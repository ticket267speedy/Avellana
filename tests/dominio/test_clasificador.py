"""Diez casos escritos a mano del clasificador de cohorte.

Criterio de aceptacion del bloque 4 (PLAN_TECNICO §12).

Las dos preguntas que el clasificador no debe mezclar:
    elegibilidad -> clinica (raro, complejo, cronico, dependiente, polimedicado)
    cohorte      -> edad    (PREVIA < 14 <= ACTIVA < 18 <= SEGUIMIENTO)
"""

from __future__ import annotations

from datetime import date, timedelta

from relevo.dominio.entidades.diagnostico import (
    CategoriaCCC,
    Contacto,
    Diagnostico,
    Dispositivo,
    Medicamento,
    TipoContacto,
)
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import VersionPasaporte
from relevo.dominio.objetos_valor.codigo_cie10 import CodigoCIE10
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.dominio.objetos_valor.ventana_transicion import Cohorte
from relevo.dominio.servicios.clasificador_cohorte import (
    ClasificadorCohorte,
    MotivoInclusion,
    contar_por_cohorte,
)

HOY = date(2026, 8, 14)
CLASIF = ClasificadorCohorte()


def nacido_hace(anios: int) -> date:
    """Fecha de nacimiento de quien cumple exactamente esos anios hoy."""
    return date(HOY.year - anios, HOY.month, HOY.day)


def dx(
    codigo: str,
    categoria: CategoriaCCC = CategoriaCCC.OTRA,
    raro: bool = False,
) -> Diagnostico:
    return Diagnostico(
        codigo=CodigoCIE10(codigo),
        descripcion=codigo,
        categoria=categoria,
        es_raro=raro,
    )


# ── 1 a 3: la version del Pasaporte que toca por edad ────────────────────────


def test_caso_1_quince_anios_le_toca_la_v1() -> None:
    """14 y 15 comparten la v1: media pagina, que tengo y que tomo."""
    paciente = Paciente(
        id="C1", fecha_nacimiento=nacido_hace(15),
        diagnosticos=[dx("G80.9", CategoriaCCC.NEUROMUSCULAR)],
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert r.es_elegible
    assert r.cohorte is Cohorte.ACTIVA
    assert r.version_pasaporte is VersionPasaporte.V1_14
    assert r.entra_al_sistema


def test_caso_2_dieciseis_anios_le_toca_la_v2() -> None:
    """Desde la v2 se pide el telefono DEL PACIENTE: a los 18 el vinculo con
    el cuidador puede haberse roto."""
    paciente = Paciente(
        id="C2", fecha_nacimiento=nacido_hace(16),
        diagnosticos=[dx("E10.9", CategoriaCCC.METABOLICA)],
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert r.version_pasaporte is VersionPasaporte.V2_16
    assert r.version_pasaporte.captura_telefono_propio


def test_caso_3_diecisiete_anios_le_toca_la_v3() -> None:
    paciente = Paciente(
        id="C3", fecha_nacimiento=nacido_hace(17),
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert r.version_pasaporte is VersionPasaporte.V3_17
    assert r.version_pasaporte.extension == "2 paginas"


# ── 4 y 5: los bordes de la ventana ──────────────────────────────────────────


def test_caso_4_doce_anios_es_elegible_pero_no_se_trabaja() -> None:
    """Queda registrado y no se trabaja: avisarle a los 12 no sirve de nada y
    satura la lista del equipo."""
    paciente = Paciente(
        id="C4", fecha_nacimiento=nacido_hace(12),
        diagnosticos=[dx("Q90.9", CategoriaCCC.CONGENITA_GENETICA)],
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert r.es_elegible
    assert r.cohorte is Cohorte.PREVIA
    assert r.version_pasaporte is None
    assert not r.entra_al_sistema


def test_caso_5_dieciocho_anios_pasa_a_seguimiento_y_sigue_en_el_sistema() -> None:
    """La cohorte que justifica el proyecto. El INSN ya no lo atiende, pero el
    ciclo sigue abierto hasta confirmar que llego al servicio de adultos: hoy
    esa confirmacion no existe y nadie sabe si el paciente llego a algun lado."""
    paciente = Paciente(
        id="C5", fecha_nacimiento=nacido_hace(18),
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert r.cohorte is Cohorte.SEGUIMIENTO
    assert r.version_pasaporte is None  # ya no se emite: se acompana
    assert r.entra_al_sistema


# ── 6 a 9: los cuatro caminos de elegibilidad ────────────────────────────────


def test_caso_6_una_fractura_no_entra() -> None:
    """Estar en la ventana no basta: un paciente agudo no necesita traspaso."""
    paciente = Paciente(
        id="C6", fecha_nacimiento=nacido_hace(16),
        diagnosticos=[dx("S52.5")],  # categoria OTRA, sin dispositivos
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert not r.es_elegible
    assert not r.entra_al_sistema
    assert r.explicacion.startswith("No cumple criterio")


def test_caso_7_enfermedad_rara_entra_aunque_la_categoria_sea_otra() -> None:
    """La lista de raras (RM 478-2026-MINSA) es una fuente independiente de
    CCC v2: un codigo puede ser raro sin caer en ninguna categoria compleja."""
    paciente = Paciente(
        id="C7", fecha_nacimiento=nacido_hace(17),
        diagnosticos=[dx("E75.2", CategoriaCCC.OTRA, raro=True)],
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert r.motivos == (MotivoInclusion.ENFERMEDAD_RARA,)


def test_caso_8_solo_el_dispositivo_ya_lo_hace_elegible() -> None:
    """Dependencia tecnologica es categoria propia en CCC v2. Un paciente con
    gastrostomia depende del sistema aunque su diagnostico no puntue."""
    paciente = Paciente(
        id="C8", fecha_nacimiento=nacido_hace(15),
        diagnosticos=[dx("R13.1")],
        dispositivos=[Dispositivo(tipo="gastrostomia")],
    )
    r = CLASIF.clasificar(paciente, HOY)

    assert r.motivos == (MotivoInclusion.DEPENDENCIA_TECNOLOGICA,)


def test_caso_9_polimedicacion_y_codigo_cronico_local_se_acumulan() -> None:
    """Los motivos se guardan todos, no solo el primero: el equipo filtra por
    motivo y 'raro' y 'complejo' no llevan al mismo servicio de adultos.

    El prefijo E10 lo agrega el medico del INSN en reglas_transicion.yaml; el
    dominio no inventa la lista.
    """
    clasificador = ClasificadorCohorte(codigos_cronicos_locales=frozenset({"E10"}))
    paciente = Paciente(
        id="C9", fecha_nacimiento=nacido_hace(17),
        diagnosticos=[dx("E10.9", CategoriaCCC.METABOLICA)],
        medicamentos=[Medicamento(nombre=f"farmaco {i}") for i in range(5)],
    )
    r = clasificador.clasificar(paciente, HOY)

    assert set(r.motivos) == {
        MotivoInclusion.CONDICION_CRONICA_COMPLEJA,
        MotivoInclusion.CRONICA_LOCAL,
        MotivoInclusion.POLIMEDICADO,
    }


# ── 10: el contacto, que casi nunca existe ───────────────────────────────────


def test_caso_10_sin_contacto_vigente_se_marca_captura() -> None:
    """La plantilla oficial del INSN (RD N° 000109-2021-DG-INSN-SB) no tiene
    campo de telefono en ninguna de sus seis paginas. El numero que hay, si lo
    hay, se anoto informalmente hace anios: por eso la verificacion caduca."""
    sin_contacto = Paciente(
        id="C10a", fecha_nacimiento=nacido_hace(17),
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
    )
    caducado = Paciente(
        id="C10b", fecha_nacimiento=nacido_hace(17),
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
        contactos=[
            Contacto(
                nombre="madre",
                tipo=TipoContacto.MADRE,
                # Verificado hace mas de un anio: ya no cuenta como vigente.
                telefono=Telefono("987654321", verificado_en=HOY - timedelta(days=400)),
            )
        ],
    )
    vigente = Paciente(
        id="C10c", fecha_nacimiento=nacido_hace(17),
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
        contactos=[
            Contacto(
                nombre="paciente",
                tipo=TipoContacto.PACIENTE,
                telefono=Telefono(
                    "987654321", verificado_en=HOY - timedelta(days=30),
                    es_del_paciente=True,
                ),
            )
        ],
    )

    assert CLASIF.clasificar(sin_contacto, HOY).requiere_captura_contacto
    assert CLASIF.clasificar(caducado, HOY).requiere_captura_contacto
    assert not CLASIF.clasificar(vigente, HOY).requiere_captura_contacto


# ── Tablero ──────────────────────────────────────────────────────────────────


def test_el_conteo_por_cohorte_solo_cuenta_elegibles() -> None:
    """El total de pacientes del hospital no es una cifra que este sistema
    deba mostrar."""
    pacientes = [
        Paciente(id="A", fecha_nacimiento=nacido_hace(15),
                 diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)]),
        Paciente(id="B", fecha_nacimiento=nacido_hace(17),
                 diagnosticos=[dx("G80.9", CategoriaCCC.NEUROMUSCULAR)]),
        Paciente(id="C", fecha_nacimiento=nacido_hace(19),
                 diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)]),
        Paciente(id="D", fecha_nacimiento=nacido_hace(16),
                 diagnosticos=[dx("S52.5")]),  # no elegible
    ]
    conteo = contar_por_cohorte(CLASIF.clasificar(p, HOY) for p in pacientes)

    assert conteo[Cohorte.ACTIVA] == 2
    assert conteo[Cohorte.SEGUIMIENTO] == 1
    assert conteo[Cohorte.PREVIA] == 0
