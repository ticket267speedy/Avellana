"""La maquina del ciclo, simulando el paso del tiempo por cada plazo.

Criterio de aceptacion del bloque 5 (PLAN_TECNICO §12).

Los plazos vienen de `config/plazos_ciclo.yaml`, calibrados con el estudio de
DIRIS Lima Norte (19 951 referencias). El numero que mas importa es el de 120
dias entre aceptacion y cita: la mediana observada es 80-85 dias, de modo que
un umbral de 90 marcaria como vencida la mitad de los casos que van bien.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.servicios.maquina_ciclo import (
    MaquinaCiclo,
    PoliticaPlazos,
    SituacionPlazo,
)

INICIO = date(2026, 8, 14)


def ciclo_nuevo(paciente_id: str = "P-1") -> CicloTransicion:
    return CicloTransicion(paciente_id=paciente_id, fecha_inicio=INICIO)


# ═══════════════════════════════════════════════════════════════════════════
# La maquina es lineal: sin saltos, sin retrocesos, sin repeticiones
# ═══════════════════════════════════════════════════════════════════════════


def test_el_ciclo_nace_con_el_pasaporte_emitido() -> None:
    ciclo = ciclo_nuevo()
    assert ciclo.estado is EstadoCiclo.PASAPORTE_EMITIDO
    assert len(ciclo.historial) == 1
    assert ciclo.siguiente_estado is EstadoCiclo.REFERENCIA_REGISTRADA


def test_saltarse_un_estado_es_error() -> None:
    """Un salto significa que alguien no registro un paso, y perder ese
    registro es perder el dato que el piloto viene a medir."""
    ciclo = ciclo_nuevo()
    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=5))


def test_retroceder_en_el_tiempo_es_error() -> None:
    ciclo = ciclo_nuevo()
    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, INICIO - timedelta(days=1))


def test_confirmar_una_cita_exige_decir_como_se_supo() -> None:
    """La proporcion entre via formal y confirmacion de la familia es un
    hallazgo del piloto, no un detalle de implementacion: el estudio documenta
    110 contrarreferencias sobre 19 951 referencias (0.55 %)."""
    ciclo = ciclo_nuevo()
    ciclo.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, INICIO + timedelta(days=3))
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ACEPTADA, INICIO + timedelta(days=20))
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=90))

    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(EstadoCiclo.CITA_CUMPLIDA, INICIO + timedelta(days=100))

    ciclo.avanzar(
        EstadoCiclo.CITA_CUMPLIDA,
        INICIO + timedelta(days=100),
        fuente_confirmacion=FuenteConfirmacion.CONFIRMACION_FAMILIA,
    )
    assert ciclo.esta_confirmado
    assert not ciclo.esta_cerrado  # confirmado por la familia, sin papel formal
    assert ciclo.fuente_de_confirmacion is FuenteConfirmacion.CONFIRMACION_FAMILIA


# ═══════════════════════════════════════════════════════════════════════════
# Los cinco plazos, dia por dia
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("estado", "plazo_esperado"),
    [
        (EstadoCiclo.PASAPORTE_EMITIDO, 7),
        (EstadoCiclo.REFERENCIA_REGISTRADA, 30),
        (EstadoCiclo.REFERENCIA_ACEPTADA, 120),
        (EstadoCiclo.CITA_PROGRAMADA, 30),
        (EstadoCiclo.CITA_CUMPLIDA, 30),
    ],
)
def test_los_plazos_son_los_del_yaml(
    estado: EstadoCiclo, plazo_esperado: int, politica: PoliticaPlazos
) -> None:
    assert politica.plazo_de(estado) == plazo_esperado


def test_el_plazo_de_120_dias_no_dispara_en_la_mediana_observada(
    maquina: MaquinaCiclo,
) -> None:
    """El caso que justifica el numero: a los 85 dias, que es la cola alta de
    la mediana observada, el ciclo todavia esta EN PLAZO. Con un umbral de 90
    ya estaria avisando, y avisar cuando no pasa nada mata el sistema: el
    equipo deja de leer los correos."""
    ciclo = ciclo_nuevo()
    ciclo.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, INICIO + timedelta(days=3))
    aceptada = INICIO + timedelta(days=20)
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ACEPTADA, aceptada)

    assert maquina.evaluar(ciclo, aceptada + timedelta(days=85)).situacion is (
        SituacionPlazo.EN_PLAZO
    )
    # El preaviso cae al dia 90 (120 - 25 %), justo donde todavia se puede
    # hacer algo.
    assert maquina.evaluar(ciclo, aceptada + timedelta(days=90)).situacion is (
        SituacionPlazo.POR_VENCER
    )
    assert maquina.evaluar(ciclo, aceptada + timedelta(days=121)).situacion is (
        SituacionPlazo.VENCIDO
    )


def test_el_dia_exacto_del_vencimiento_todavia_no_esta_vencido(
    maquina: MaquinaCiclo,
) -> None:
    """Plazo de 7 dias: el dia 7 se cumple el plazo, el 8 se incumple."""
    ciclo = ciclo_nuevo()
    assert maquina.evaluar(ciclo, INICIO + timedelta(days=7)).situacion is (
        SituacionPlazo.POR_VENCER
    )
    assert maquina.evaluar(ciclo, INICIO + timedelta(days=8)).situacion is (
        SituacionPlazo.VENCIDO
    )


def test_el_preaviso_nunca_baja_del_minimo(politica: PoliticaPlazos) -> None:
    """El 25 % de 7 dias son 1.75 dias, y avisar dia y medio antes no le da
    tiempo a nadie. El minimo de 3 dias del YAML manda."""
    assert politica.dias_de_preaviso(EstadoCiclo.PASAPORTE_EMITIDO) == 3
    assert politica.dias_de_preaviso(EstadoCiclo.REFERENCIA_ACEPTADA) == 30


def test_la_cita_se_cuenta_desde_su_fecha_y_no_desde_su_programacion(
    maquina: MaquinaCiclo,
) -> None:
    """Una cita programada a tres meses no esta vencida a los treinta dias de
    haberse programado. El plazo 4 -> 5 corre desde la fecha de la cita."""
    ciclo = ciclo_nuevo()
    ciclo.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, INICIO + timedelta(days=3))
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ACEPTADA, INICIO + timedelta(days=20))
    programacion = INICIO + timedelta(days=30)
    fecha_cita = INICIO + timedelta(days=120)
    ciclo.fecha_cita = fecha_cita
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, programacion)

    # 60 dias despues de programarla, pero la cita aun no ha ocurrido.
    evaluacion = maquina.evaluar(ciclo, programacion + timedelta(days=60))
    assert evaluacion.situacion is SituacionPlazo.EN_PLAZO
    assert evaluacion.dias_transcurridos < 0

    # 31 dias despues de la cita, sin confirmacion: es inasistencia.
    assert maquina.evaluar(ciclo, fecha_cita + timedelta(days=31)).situacion is (
        SituacionPlazo.VENCIDO
    )


def test_el_ciclo_cerrado_no_tiene_plazo_que_vigilar(maquina: MaquinaCiclo) -> None:
    ciclo = ciclo_nuevo()
    ciclo.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, INICIO + timedelta(days=3))
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ACEPTADA, INICIO + timedelta(days=20))
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=90))
    ciclo.avanzar(
        EstadoCiclo.CITA_CUMPLIDA,
        INICIO + timedelta(days=95),
        fuente_confirmacion=FuenteConfirmacion.CONTRARREFERENCIA,
    )
    ciclo.avanzar(EstadoCiclo.CONTRARREFERENCIA, INICIO + timedelta(days=110))

    evaluacion = maquina.evaluar(ciclo, INICIO + timedelta(days=900))
    assert evaluacion.situacion is SituacionPlazo.CERRADO
    assert evaluacion.plazo_dias is None
    assert not evaluacion.requiere_accion

    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(EstadoCiclo.CONTRARREFERENCIA, INICIO + timedelta(days=120))


# ═══════════════════════════════════════════════════════════════════════════
# La lista que va al correo del equipo
# ═══════════════════════════════════════════════════════════════════════════


def test_primero_lo_vencido_y_dentro_de_eso_lo_mas_parado(
    maquina: MaquinaCiclo,
) -> None:
    hoy = date(2026, 10, 20)
    # Plazo del estado PASAPORTE_EMITIDO: 7 dias.
    ciclos = [
        CicloTransicion(paciente_id="EN-PLAZO", fecha_inicio=hoy - timedelta(days=1)),
        CicloTransicion(
            paciente_id="VENCIDO-10", fecha_inicio=hoy - timedelta(days=17)
        ),
        CicloTransicion(
            paciente_id="VENCIDO-60", fecha_inicio=hoy - timedelta(days=67)
        ),
    ]

    orden = maquina.evaluar_todos(ciclos, hoy)
    assert [e.paciente_id for e in orden] == ["VENCIDO-60", "VENCIDO-10", "EN-PLAZO"]


def test_si_no_hay_nada_que_atender_la_lista_sale_vacia(maquina: MaquinaCiclo) -> None:
    """Un aviso que llega siempre deja de leerse (PLAN_TECNICO §10). Sin nada
    en la lista, no se manda correo."""
    ciclo = ciclo_nuevo()
    assert maquina.requieren_accion([ciclo], INICIO + timedelta(days=1)) == []


def test_el_mensaje_del_aviso_no_lleva_datos_clinicos(maquina: MaquinaCiclo) -> None:
    """Puede terminar en una pantalla de bloqueo. Dice que atender y donde,
    nunca que tiene el paciente."""
    ciclo = ciclo_nuevo()
    mensaje = maquina.evaluar(ciclo, INICIO + timedelta(days=20)).mensaje()
    assert mensaje == "P-1: Pasaporte emitido vencido hace 13 dias"
