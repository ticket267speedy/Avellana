"""BLOQUEANTE — un ciclo reabierto no reabre la atencion pediatrica.

═══════════════════════════════════════════════════════════════════════════════
QUE VIGILA ESTE ARCHIVO
═══════════════════════════════════════════════════════════════════════════════

REINGRESO es un estado del CICLO DE TRANSICION, no un reingreso al INSN. Es la
confusion que mas tiempo le costo al equipo, y es del tipo que un jurado
clinico detecta en diez segundos: si la demo muestra un paciente de 18 anios y
medio "reingresando", la primera pregunta va a ser si estamos proponiendo que
el INSN atienda a un adulto.

La respuesta tiene que estar en el codigo y no en el discurso. Con el paciente
>= 18, `acciones_permitidas` devuelve solo acciones administrativas. Ninguna
accion clinica del INSN aparece, porque el INSN no atiende a mayores de 18 bajo
ninguna circunstancia (regla institucional, `CLAUDE.md`).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    MotivoReingreso,
)
from relevo.dominio.objetos_valor.reingreso import (
    ACCIONES_ADMINISTRATIVAS,
    AccionCiclo,
    Reingreso,
    acciones_permitidas,
)

HOY = date(2026, 8, 16)


def ciclo_en_reingreso(fecha_nacimiento: date | None) -> CicloTransicion:
    """Un ciclo que llego a REINGRESO por la ruta mas corta: se perdio y volvio."""
    ciclo = CicloTransicion(
        paciente_id="PAC-HUNTER",
        fecha_inicio=HOY - timedelta(days=200),
        fecha_nacimiento=fecha_nacimiento,
    )
    ciclo.avanzar(EstadoCiclo.PERDIDA_DE_SEGUIMIENTO, HOY - timedelta(days=60))
    ciclo.avanzar(
        EstadoCiclo.REINGRESO,
        HOY - timedelta(days=5),
        motivo_reingreso=MotivoReingreso.REAPARECE_TRAS_PERDIDA,
    )
    return ciclo


# ═══════════════════════════════════════════════════════════════════════════
# La regla
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_con_dieciocho_anios_y_un_dia_ninguna_accion_clinica_es_posible() -> None:
    """El caso limite exacto: 18 anios y 1 dia, ciclo reabierto."""
    # Cumplio 18 ayer.
    nacimiento = date(HOY.year - 18, HOY.month, HOY.day) - timedelta(days=1)
    ciclo = ciclo_en_reingreso(nacimiento)

    permitidas = acciones_permitidas(ciclo, HOY)

    clinicas = {a for a in permitidas if a.es_clinica}
    assert not clinicas, (
        "Con el paciente mayor de edad, el ciclo reabierto habilito acciones "
        f"clinicas del INSN: {sorted(a.name for a in clinicas)}. El INSN no "
        "atiende a mayores de 18 bajo ninguna circunstancia."
    )
    assert permitidas <= ACCIONES_ADMINISTRATIVAS


@pytest.mark.bloqueante
def test_el_reingreso_si_habilita_la_gestion_administrativa() -> None:
    """La otra mitad de la regla, que es la que le da sentido al estado.

    Si un ciclo reabierto no habilitara nada, REINGRESO seria decorativo. Lo
    que habilita es exactamente lo que la NT 018-MINSA obliga a hacer: cerrar
    la derivacion. Esa obligacion no caduca con la edad del paciente.
    """
    nacimiento = date(HOY.year - 19, 3, 4)
    ciclo = ciclo_en_reingreso(nacimiento)

    permitidas = acciones_permitidas(ciclo, HOY)

    assert AccionCiclo.REENVIAR_PASAPORTE in permitidas
    assert AccionCiclo.CONTACTAR_RECEPTOR in permitidas
    assert AccionCiclo.CONTACTAR_FAMILIA in permitidas
    assert AccionCiclo.RECLASIFICAR_CICLO in permitidas


def test_reenviar_un_pasaporte_firmado_no_es_emitir_uno_nuevo() -> None:
    """La distincion no es sutil: emitir exige que un medico del INSN revise y
    firme sobre un paciente al que la institucion ya no puede atender."""
    assert AccionCiclo.REENVIAR_PASAPORTE.es_administrativa
    assert AccionCiclo.EMITIR_PASAPORTE.es_clinica


def test_antes_de_los_dieciocho_todo_sigue_disponible() -> None:
    """El corte es duro y en fecha exacta, no una degradacion progresiva."""
    nacimiento = date(HOY.year - 17, HOY.month, HOY.day)
    ciclo = ciclo_en_reingreso(nacimiento)

    permitidas = acciones_permitidas(ciclo, HOY)
    assert AccionCiclo.PROGRAMAR_CONSULTA_INSN in permitidas
    assert AccionCiclo.EMITIR_PASAPORTE in permitidas


def test_el_dia_del_cumpleanios_ya_esta_fuera() -> None:
    """El corte es EN el cumpleanos, no al dia siguiente."""
    nacimiento = date(HOY.year - 18, HOY.month, HOY.day)
    ciclo = ciclo_en_reingreso(nacimiento)

    assert not any(a.es_clinica for a in acciones_permitidas(ciclo, HOY))


@pytest.mark.bloqueante
def test_sin_fecha_de_nacimiento_se_asume_lo_peor() -> None:
    """Una edad desconocida no es una edad valida.

    Un ciclo migrado de la base vieja puede no traer fecha de nacimiento. Si el
    sistema resolviera ese hueco por optimismo, la regla mas dura del proyecto
    se caeria justo en los datos que menos controlamos.
    """
    ciclo = ciclo_en_reingreso(None)

    assert not any(a.es_clinica for a in acciones_permitidas(ciclo, HOY))


# ═══════════════════════════════════════════════════════════════════════════
# El registro del reingreso
# ═══════════════════════════════════════════════════════════════════════════


def test_un_reingreso_no_se_reclasifica_a_un_estado_que_no_es_de_tramite() -> None:
    """Reclasificar a REINGRESO o a PERDIDA_DE_SEGUIMIENTO deja el ciclo en el
    mismo limbo del que se queria sacar."""
    with pytest.raises(ValueError):
        Reingreso(
            motivo=MotivoReingreso.CAMBIO_DE_DESTINO,
            fecha=HOY,
            reclasificado_a=EstadoCiclo.REINGRESO,
        )


def test_el_motivo_del_reingreso_queda_registrado() -> None:
    """Contarlos por motivo es lo que distingue una inasistencia de un destino
    que no funciono. Son dos problemas distintos del sistema de salud."""
    ciclo = ciclo_en_reingreso(date(HOY.year - 17, 1, 1))
    assert ciclo.reingresos[0].motivo is MotivoReingreso.REAPARECE_TRAS_PERDIDA
    assert not ciclo.reingresos[0].esta_reclasificado
