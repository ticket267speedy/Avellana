"""BLOQUEANTE — lo que declara el paciente nunca sobrescribe el Pasaporte.

═══════════════════════════════════════════════════════════════════════════════
LAS DOS REGLAS
═══════════════════════════════════════════════════════════════════════════════

1. Lo que declara el paciente NUNCA sobrescribe el dato verificado. Genera un
   caso de conciliacion asignado al equipo del INSN.
2. El sistema NUNCA decide cual version es la correcta. Solo reporta.

Las dos son consecuencia de reglas inviolables que ya existian: el medico
siempre firma (regla 4) y ninguna dosis entra si no aparece literalmente en la
fuente (regla 8). Una conciliacion que escribiera en el Pasaporte las
rompereria las dos de una vez, y lo haria en silencio — que es la unica forma
en que este sistema no puede fallar.
"""

from __future__ import annotations

import copy
from datetime import date

import pytest

from relevo.dominio.entidades.conciliacion import (
    CasoDeConciliacion,
    EstadoConciliacion,
    MedicacionDeclarada,
)
from relevo.dominio.entidades.diagnostico import Medicamento
from relevo.dominio.objetos_valor.origen_dato import OrigenDato, TipoDiscrepancia
from relevo.dominio.objetos_valor.responsable import Responsable
from relevo.dominio.servicios.conciliador import conciliar, hay_algo_que_cotejar

HOY = date(2026, 8, 16)


def pasaporte_de_mateo() -> list[Medicamento]:
    """Medicacion del caso protagonista. Sintetica (regla 1).

    Idursulfasa es el tratamiento de la mucopolisacaridosis tipo II. La dosis
    NO se inventa: va marcada como no verificada en la fuente, que es como el
    sistema representa un hueco que un medico tiene que llenar.
    """
    return [
        Medicamento(
            nombre="Idursulfasa",
            dosis=None,
            via="intravenosa",
            frecuencia="semanal",
            verificada_en_fuente=False,
        ),
        Medicamento(
            nombre="Salbutamol",
            dosis="100 mcg",
            frecuencia="cada 8 horas",
            verificada_en_fuente=True,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# La regla 1: no se sobrescribe nada
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_conciliar_no_toca_el_pasaporte() -> None:
    """Comparacion estructural antes y despues. Si algo cambiara, cambiaria en
    silencio, que es la unica forma en que este sistema no puede fallar."""
    del_pasaporte = pasaporte_de_mateo()
    antes = copy.deepcopy(del_pasaporte)

    declarados = [
        MedicacionDeclarada(nombre="Idursulfasa", dosis="30 mg", frecuencia="semanal"),
        MedicacionDeclarada(nombre="Salbutamol", dosis="200 mcg"),
        MedicacionDeclarada(nombre="Omeprazol", dosis="20 mg"),
    ]

    conciliar("PAC-HUNTER", del_pasaporte, declarados, HOY)

    assert del_pasaporte == antes, (
        "La conciliacion modifico el Pasaporte. Una dosis declarada por el "
        "paciente no puede entrar al documento que un medico firma."
    )


@pytest.mark.bloqueante
def test_una_dosis_declarada_no_llena_el_hueco_del_pasaporte() -> None:
    """El caso mas tentador: el Pasaporte tiene el hueco y el paciente sabe el
    numero. Sigue sin poder escribirse — la regla 8 no admite excepciones por
    conveniencia."""
    del_pasaporte = pasaporte_de_mateo()
    idursulfasa = del_pasaporte[0]
    assert idursulfasa.requiere_completar_manualmente

    conciliar(
        "PAC-HUNTER",
        del_pasaporte,
        [MedicacionDeclarada(nombre="Idursulfasa", dosis="0.5 mg/kg")],
        HOY,
    )

    assert del_pasaporte[0].dosis is None
    assert del_pasaporte[0].requiere_completar_manualmente
    assert "____" in del_pasaporte[0].texto_seguro()


@pytest.mark.bloqueante
def test_la_discrepancia_genera_un_caso_asignado_al_equipo_del_insn() -> None:
    """No al paciente, que ya hizo su parte, ni al receptor, que no tiene la
    historia pediatrica con la que hay que cotejar."""
    caso = conciliar(
        "PAC-HUNTER",
        pasaporte_de_mateo(),
        [MedicacionDeclarada(nombre="Salbutamol", dosis="200 mcg")],
        HOY,
    )

    assert isinstance(caso, CasoDeConciliacion)
    assert caso.responsable is Responsable.EQUIPO_INSN
    assert caso.estado is EstadoConciliacion.ABIERTO
    assert caso.esta_abierto


# ═══════════════════════════════════════════════════════════════════════════
# La regla 2: el sistema no decide
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_la_discrepancia_guarda_las_dos_versiones_sin_elegir() -> None:
    """Un campo unico "valor correcto" seria el sitio exacto donde el sistema
    tomaria la decision que no le corresponde."""
    caso = conciliar(
        "PAC-1",
        [Medicamento(nombre="Salbutamol", dosis="100 mcg", verificada_en_fuente=True)],
        [MedicacionDeclarada(nombre="Salbutamol", dosis="200 mcg")],
        HOY,
    )

    (discrepancia,) = caso.discrepancias
    assert discrepancia.tipo is TipoDiscrepancia.DOSIS_DISTINTA
    assert discrepancia.valor_pasaporte == "100 mcg"
    assert discrepancia.valor_declarado == "200 mcg"
    assert not hasattr(discrepancia, "valor_correcto")


def test_resolver_exige_nombre_y_nota() -> None:
    """Una conciliacion resuelta sin decir quien ni que decidio no se puede
    auditar, y lo que no se puede auditar aqui equivale a no haber pasado."""
    caso = conciliar("PAC-1", pasaporte_de_mateo(), [], HOY)

    with pytest.raises(ValueError):
        caso.resolver("", HOY, "se corrigio")
    with pytest.raises(ValueError):
        caso.resolver("Dra. Rios", HOY, "  ")

    caso.resolver("Dra. Rios", HOY, "Se confirmo con la madre por telefono.")
    assert caso.estado is EstadoConciliacion.RESUELTO
    assert not caso.esta_abierto


# ═══════════════════════════════════════════════════════════════════════════
# Que se detecta y que no
# ═══════════════════════════════════════════════════════════════════════════


def test_lo_que_el_paciente_toma_y_el_pasaporte_no_registra() -> None:
    """El caso mas interesante de los cuatro: suele ser medicacion anadida en
    otro establecimiento, y es exactamente lo que un receptor necesita saber."""
    caso = conciliar(
        "PAC-1",
        pasaporte_de_mateo(),
        [MedicacionDeclarada(nombre="Omeprazol", dosis="20 mg")],
        HOY,
    )
    faltas = caso.discrepancias_de(TipoDiscrepancia.FALTA_EN_PASAPORTE)
    assert [d.medicamento for d in faltas] == ["Omeprazol"]


def test_el_hueco_de_dosis_no_verificada_no_es_una_discrepancia() -> None:
    """Contarlo como diferencia enterraria las diferencias de verdad: la lista
    saldria llena de ruido y nadie la miraria."""
    caso = conciliar(
        "PAC-1",
        [Medicamento(nombre="Idursulfasa", dosis=None, verificada_en_fuente=False)],
        [MedicacionDeclarada(nombre="Idursulfasa", dosis="30 mg")],
        HOY,
    )
    assert caso.discrepancias_de(TipoDiscrepancia.DOSIS_DISTINTA) == ()
    assert caso.total_discrepancias == 0


def test_un_medicamento_que_el_paciente_dejo_de_tomar_no_se_coteja_por_dosis() -> None:
    """Dejar un tratamiento no es una discrepancia de dosis: es un cambio, y se
    reporta como ausencia en la declaracion."""
    caso = conciliar(
        "PAC-1",
        [Medicamento(nombre="Salbutamol", dosis="100 mcg", verificada_en_fuente=True)],
        [
            MedicacionDeclarada(
                nombre="Salbutamol", dosis="200 mcg", lo_sigue_tomando=False
            )
        ],
        HOY,
    )
    assert caso.discrepancias_de(TipoDiscrepancia.DOSIS_DISTINTA) == ()
    assert len(caso.discrepancias_de(TipoDiscrepancia.FALTA_EN_DECLARACION)) == 1


def test_dos_listas_que_coinciden_producen_un_caso_vacio_y_no_uno_nulo() -> None:
    """"Se cotejo y coincide" es un hecho que vale la pena registrar. Devolver
    None obligaria a distinguir entre eso y "no se cotejo"."""
    medicamentos = [
        Medicamento(nombre="Salbutamol", dosis="100 mcg", verificada_en_fuente=True)
    ]
    caso = conciliar(
        "PAC-1",
        medicamentos,
        [MedicacionDeclarada(nombre="salbutamol", dosis="100  mcg")],
        HOY,
    )
    assert caso.total_discrepancias == 0
    assert not hay_algo_que_cotejar(caso)


def test_lo_declarado_por_el_paciente_se_marca_con_su_origen() -> None:
    """`OrigenDato` es la capa de presentacion de `EstadoCampo`, no su
    reemplazo: el dominio sigue en VERDE/AMBAR/ROJO y la interfaz traduce."""
    declarado = MedicacionDeclarada(nombre="Omeprazol", dosis="20 mg")
    assert declarado.origen is OrigenDato.INFORMADO_POR_PACIENTE

    from relevo.dominio.objetos_valor.campo_extraido import EstadoCampo

    assert OrigenDato.INFORMADO_POR_PACIENTE.estado_campo is EstadoCampo.AMBAR
    assert OrigenDato.VERIFICADO_INSN.estado_campo is EstadoCampo.VERDE
    assert OrigenDato.PENDIENTE_DE_COTEJO.estado_campo is EstadoCampo.ROJO
