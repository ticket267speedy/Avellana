"""La maquina del ciclo, simulando el paso del tiempo por cada plazo.

Criterio de aceptacion del bloque 5 (PLAN_TECNICO §12), actualizado a los nueve
estados de la fusion.

Los plazos vienen de `config/plazos_ciclo.yaml`. El unico calibrado con datos
es el de 120 dias entre aceptacion y cita: la mediana observada es 80-85 dias
(DIRIS Lima Norte, 19 951 referencias), de modo que un umbral de 90 marcaria
como vencida la mitad de los casos que van bien. Los demas estan marcados como
PROVISIONAL, aqui y en el YAML.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    FuenteConfirmacion,
    MotivoReingreso,
)
from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.objetos_valor.estado_ciclo import (
    ESTADOS_LEGADO,
    TRANSICIONES_PERMITIDAS,
    estado_desde_persistido,
)
from relevo.dominio.objetos_valor.responsable import Responsable, responsable_de
from relevo.dominio.servicios.maquina_ciclo import (
    TABLA_CICLO,
    MaquinaCiclo,
    PoliticaPlazos,
    SituacionPlazo,
)

INICIO = date(2026, 8, 14)


def ciclo_nuevo(paciente_id: str = "P-1") -> CicloTransicion:
    return CicloTransicion(paciente_id=paciente_id, fecha_inicio=INICIO)


def hasta_aceptacion(ciclo: CicloTransicion) -> date:
    """Lleva un ciclo recien abierto hasta ACEPTADO_CON_SERVICIO.

    Devuelve la fecha de aceptacion, que es desde donde corre el plazo de 120
    dias — el unico numero de la tabla que no es provisional.
    """
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ENVIADA, INICIO + timedelta(days=3))
    ciclo.avanzar(EstadoCiclo.RECEPCION_CONFIRMADA, INICIO + timedelta(days=6))
    ciclo.avanzar(EstadoCiclo.EN_EVALUACION, INICIO + timedelta(days=10))
    aceptada = INICIO + timedelta(days=20)
    ciclo.avanzar(EstadoCiclo.ACEPTADO_CON_SERVICIO, aceptada)
    return aceptada


# ═══════════════════════════════════════════════════════════════════════════
# El grafo: explicito, sin callejones sin salida
# ═══════════════════════════════════════════════════════════════════════════


def test_el_ciclo_nace_en_preparacion() -> None:
    ciclo = ciclo_nuevo()
    assert ciclo.estado is EstadoCiclo.PREPARACION
    assert len(ciclo.historial) == 1
    assert ciclo.siguiente_estado is EstadoCiclo.REFERENCIA_ENVIADA
    assert ciclo.responsable is Responsable.EQUIPO_INSN


@pytest.mark.bloqueante
def test_desde_todo_estado_se_alcanza_la_primera_atencion() -> None:
    """Recorre el grafo entero. Un estado desde el que no se llega al final es
    un expediente enterrado: el paciente existe, el ciclo existe, y no hay
    camino que lo lleve a ser atendido.

    Incluye PERDIDA_DE_SEGUIMIENTO a proposito. Que se pueda salir de la
    perdida es lo que distingue este modelo de uno que solo sabe contar bajas.
    """
    meta = EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA

    for origen in EstadoCiclo:
        vistos: set[EstadoCiclo] = set()
        pendientes = [origen]
        alcanzado = False
        while pendientes:
            actual = pendientes.pop()
            for destino in TRANSICIONES_PERMITIDAS[actual]:
                if destino is meta:
                    alcanzado = True
                if destino not in vistos:
                    vistos.add(destino)
                    pendientes.append(destino)
        assert alcanzado, (
            f"Desde {origen.name} no se puede alcanzar {meta.name}: el grafo "
            "tiene un callejon sin salida."
        )


def test_una_transicion_fuera_del_grafo_es_error() -> None:
    """Un salto significa que alguien no registro un paso, y perder ese
    registro es perder el dato que el piloto viene a medir."""
    ciclo = ciclo_nuevo()
    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=5))


def test_retroceder_en_el_tiempo_es_error() -> None:
    ciclo = ciclo_nuevo()
    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(EstadoCiclo.REFERENCIA_ENVIADA, INICIO - timedelta(days=1))


def test_desde_cualquier_estado_de_tramite_se_puede_caer_a_la_perdida() -> None:
    """Un paciente se pierde cuando le da la gana, no cuando al proceso le
    conviene."""
    for estado in TRANSICIONES_PERMITIDAS:
        if not estado.es_de_tramite or estado.es_final:
            continue
        assert EstadoCiclo.PERDIDA_DE_SEGUIMIENTO in TRANSICIONES_PERMITIDAS[estado], (
            f"Desde {estado.name} no se puede registrar una perdida de "
            "seguimiento, y ese es el desenlace que el proyecto existe para "
            "poder contar."
        )


def test_la_recepcion_y_la_evaluacion_son_estados_distintos() -> None:
    """Ahi exactamente vive el 0.55 % de contrarreferencia del estudio de DIRIS
    Lima Norte. Un solo estado hace indistinguible un expediente que nadie
    abrio de uno que se esta evaluando."""
    assert EstadoCiclo.RECEPCION_CONFIRMADA is not EstadoCiclo.EN_EVALUACION
    assert TRANSICIONES_PERMITIDAS[EstadoCiclo.RECEPCION_CONFIRMADA] >= frozenset(
        {EstadoCiclo.EN_EVALUACION}
    )


# ═══════════════════════════════════════════════════════════════════════════
# Reingreso y confirmacion: los dos avances que exigen decir por que
# ═══════════════════════════════════════════════════════════════════════════


def test_confirmar_una_atencion_exige_decir_como_se_supo() -> None:
    """La proporcion entre via formal, receptor y familia es un hallazgo del
    piloto: el estudio documenta 110 contrarreferencias sobre 19 951 (0.55 %)."""
    ciclo = ciclo_nuevo()
    hasta_aceptacion(ciclo)
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=90))

    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(
            EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA, INICIO + timedelta(days=100)
        )

    ciclo.avanzar(
        EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
        INICIO + timedelta(days=100),
        fuente_confirmacion=FuenteConfirmacion.CONFIRMACION_RECEPTOR,
    )
    assert ciclo.esta_confirmado
    assert ciclo.esta_cerrado
    assert ciclo.tiene_destino_asegurado
    assert ciclo.responsable is Responsable.NADIE
    assert ciclo.fuente_de_confirmacion is FuenteConfirmacion.CONFIRMACION_RECEPTOR


def test_reabrir_un_ciclo_exige_decir_por_que() -> None:
    """Un reingreso sin motivo no se puede contar, y contarlos por motivo es lo
    que distingue una inasistencia de un destino que no funciono."""
    ciclo = ciclo_nuevo()
    hasta_aceptacion(ciclo)
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=90))

    with pytest.raises(TransicionInvalida):
        ciclo.avanzar(EstadoCiclo.REINGRESO, INICIO + timedelta(days=110))

    ciclo.avanzar(
        EstadoCiclo.REINGRESO,
        INICIO + timedelta(days=110),
        motivo_reingreso=MotivoReingreso.NO_ASISTIO_A_PRIMERA_CITA,
    )
    assert ciclo.estado is EstadoCiclo.REINGRESO
    assert len(ciclo.reingresos_sin_reclasificar) == 1


def test_el_reingreso_es_transitorio_y_se_reclasifica() -> None:
    """Un ciclo no puede quedarse en REINGRESO: seria el cajon donde los casos
    dificiles van a morir sin que nadie lo note."""
    ciclo = ciclo_nuevo()
    hasta_aceptacion(ciclo)
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=90))
    ciclo.avanzar(
        EstadoCiclo.REINGRESO,
        INICIO + timedelta(days=110),
        motivo_reingreso=MotivoReingreso.NO_ASISTIO_A_PRIMERA_CITA,
    )

    ciclo.reclasificar(EstadoCiclo.ACEPTADO_CON_SERVICIO, INICIO + timedelta(days=113))

    assert ciclo.estado is EstadoCiclo.ACEPTADO_CON_SERVICIO
    assert ciclo.reingresos_sin_reclasificar == ()
    assert ciclo.reingresos[0].reclasificado_a is EstadoCiclo.ACEPTADO_CON_SERVICIO


def test_la_primera_atencion_es_terminal_pero_no_inmutable() -> None:
    """"Lo atendieron una vez y ahi se acabo" es un desenlace frecuente y hay
    que poder nombrarlo: en el papel figura como exito."""
    ciclo = ciclo_nuevo()
    hasta_aceptacion(ciclo)
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=90))
    ciclo.avanzar(
        EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
        INICIO + timedelta(days=95),
        fuente_confirmacion=FuenteConfirmacion.CONTRARREFERENCIA,
    )

    ciclo.avanzar(
        EstadoCiclo.REINGRESO,
        INICIO + timedelta(days=400),
        motivo_reingreso=MotivoReingreso.ATENDIDO_SIN_CONTINUIDAD,
    )
    assert ciclo.estado is EstadoCiclo.REINGRESO


# ═══════════════════════════════════════════════════════════════════════════
# ¿Quien tiene el turno ahora?
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("estado", "esperado"),
    [
        (EstadoCiclo.PREPARACION, Responsable.EQUIPO_INSN),
        (EstadoCiclo.REFERENCIA_ENVIADA, Responsable.HOSPITAL_RECEPTOR),
        (EstadoCiclo.RECEPCION_CONFIRMADA, Responsable.HOSPITAL_RECEPTOR),
        (EstadoCiclo.EN_EVALUACION, Responsable.HOSPITAL_RECEPTOR),
        (EstadoCiclo.ACEPTADO_CON_SERVICIO, Responsable.HOSPITAL_RECEPTOR),
        (EstadoCiclo.CITA_PROGRAMADA, Responsable.PACIENTE),
        (EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA, Responsable.NADIE),
        (EstadoCiclo.PERDIDA_DE_SEGUIMIENTO, Responsable.EQUIPO_INSN),
        (EstadoCiclo.REINGRESO, Responsable.EQUIPO_INSN),
    ],
)
def test_todo_estado_tiene_dueno(estado: EstadoCiclo, esperado: Responsable) -> None:
    """El INSN lo pidio dos veces: en el entregable 1 y en su Insight 5. Un
    estado sin responsable es un expediente parado que nadie reclama."""
    assert responsable_de(estado) is esperado


def test_la_tabla_del_ciclo_documenta_la_fuente_de_cada_plazo() -> None:
    """Regla 7 del proyecto. Un umbral sin fuente es un umbral inventado."""
    for estado, entrada in TABLA_CICLO.items():
        assert entrada.fuente.strip(), f"{estado.name} no declara fuente"
    # El de 120 dias es el unico calibrado con datos; el resto va marcado.
    assert not TABLA_CICLO[EstadoCiclo.ACEPTADO_CON_SERVICIO].provisional
    assert TABLA_CICLO[EstadoCiclo.PREPARACION].provisional


# ═══════════════════════════════════════════════════════════════════════════
# Migracion de los seis estados originales
# ═══════════════════════════════════════════════════════════════════════════


def test_todo_estado_viejo_persistido_tiene_destino() -> None:
    """No se borra nada para simplificar la migracion: borrar filas es perder
    el historico que el piloto viene a medir."""
    viejos = (
        "PASAPORTE_EMITIDO",
        "REFERENCIA_REGISTRADA",
        "REFERENCIA_ACEPTADA",
        "CITA_PROGRAMADA",
        "CITA_CUMPLIDA",
        "CONTRARREFERENCIA",
    )
    for nombre in viejos:
        assert nombre in ESTADOS_LEGADO, f"{nombre} se quedaria sin traduccion"
        assert isinstance(estado_desde_persistido(nombre), EstadoCiclo)

    # El enum viejo se serializaba tambien por su valor entero.
    for entero in "123456":
        assert isinstance(estado_desde_persistido(entero), EstadoCiclo)


def test_un_estado_nuevo_no_pasa_por_la_tabla_de_legado() -> None:
    """CITA_PROGRAMADA existe en los dos modelos con el mismo significado, pero
    el resto no: leer un valor nuevo por la ruta de migracion seria traducirlo
    dos veces."""
    for estado in EstadoCiclo:
        assert estado_desde_persistido(estado.value) is estado


def test_un_estado_desconocido_se_detiene_en_vez_de_adivinar() -> None:
    with pytest.raises(ValueError):
        estado_desde_persistido("ESTADO_QUE_NUNCA_EXISTIO")


# ═══════════════════════════════════════════════════════════════════════════
# Los plazos, dia por dia
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("estado", "plazo_esperado"),
    [
        (EstadoCiclo.PREPARACION, 30),
        (EstadoCiclo.REFERENCIA_ENVIADA, 7),
        (EstadoCiclo.RECEPCION_CONFIRMADA, 15),
        (EstadoCiclo.EN_EVALUACION, 30),
        (EstadoCiclo.ACEPTADO_CON_SERVICIO, 120),
        (EstadoCiclo.CITA_PROGRAMADA, 7),
        (EstadoCiclo.PERDIDA_DE_SEGUIMIENTO, 15),
        (EstadoCiclo.REINGRESO, 7),
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
    aceptada = hasta_aceptacion(ciclo)

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
    """Plazo de PREPARACION: 30 dias. El dia 30 se cumple, el 31 se incumple."""
    ciclo = ciclo_nuevo()
    assert maquina.evaluar(ciclo, INICIO + timedelta(days=30)).situacion is (
        SituacionPlazo.POR_VENCER
    )
    assert maquina.evaluar(ciclo, INICIO + timedelta(days=31)).situacion is (
        SituacionPlazo.VENCIDO
    )


def test_el_preaviso_nunca_baja_del_minimo(politica: PoliticaPlazos) -> None:
    """El 25 % de 7 dias son 1.75 dias, y avisar dia y medio antes no le da
    tiempo a nadie. El minimo de 3 dias del YAML manda."""
    assert politica.dias_de_preaviso(EstadoCiclo.REFERENCIA_ENVIADA) == 3
    assert politica.dias_de_preaviso(EstadoCiclo.ACEPTADO_CON_SERVICIO) == 30


def test_la_cita_se_cuenta_desde_su_fecha_y_no_desde_su_programacion(
    maquina: MaquinaCiclo,
) -> None:
    """Una cita programada a tres meses no esta vencida a los siete dias de
    haberse programado."""
    ciclo = ciclo_nuevo()
    hasta_aceptacion(ciclo)
    programacion = INICIO + timedelta(days=30)
    fecha_cita = INICIO + timedelta(days=120)
    ciclo.fecha_cita = fecha_cita
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, programacion)

    # 60 dias despues de programarla, pero la cita aun no ha ocurrido.
    evaluacion = maquina.evaluar(ciclo, programacion + timedelta(days=60))
    assert evaluacion.situacion is SituacionPlazo.EN_PLAZO
    assert evaluacion.dias_transcurridos < 0

    # 8 dias despues de la cita, sin confirmacion: es inasistencia.
    assert maquina.evaluar(ciclo, fecha_cita + timedelta(days=8)).situacion is (
        SituacionPlazo.VENCIDO
    )


def test_el_ciclo_cerrado_no_tiene_plazo_que_vigilar(maquina: MaquinaCiclo) -> None:
    ciclo = ciclo_nuevo()
    hasta_aceptacion(ciclo)
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, INICIO + timedelta(days=90))
    ciclo.avanzar(
        EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
        INICIO + timedelta(days=95),
        fuente_confirmacion=FuenteConfirmacion.CONTRARREFERENCIA,
    )

    evaluacion = maquina.evaluar(ciclo, INICIO + timedelta(days=900))
    assert evaluacion.situacion is SituacionPlazo.CERRADO
    assert evaluacion.plazo_dias is None
    assert not evaluacion.requiere_accion


# ═══════════════════════════════════════════════════════════════════════════
# La lista que va al correo del equipo
# ═══════════════════════════════════════════════════════════════════════════


def test_primero_lo_vencido_y_dentro_de_eso_lo_mas_parado(
    maquina: MaquinaCiclo,
) -> None:
    hoy = date(2026, 10, 20)
    # Plazo del estado PREPARACION: 30 dias.
    ciclos = [
        CicloTransicion(paciente_id="EN-PLAZO", fecha_inicio=hoy - timedelta(days=1)),
        CicloTransicion(
            paciente_id="VENCIDO-10", fecha_inicio=hoy - timedelta(days=40)
        ),
        CicloTransicion(
            paciente_id="VENCIDO-60", fecha_inicio=hoy - timedelta(days=90)
        ),
    ]

    orden = maquina.evaluar_todos(ciclos, hoy)
    assert [e.paciente_id for e in orden] == ["VENCIDO-60", "VENCIDO-10", "EN-PLAZO"]


def test_si_no_hay_nada_que_atender_la_lista_sale_vacia(maquina: MaquinaCiclo) -> None:
    """Un aviso que llega siempre deja de leerse (PLAN_TECNICO §10). Sin nada
    en la lista, no se manda correo."""
    ciclo = ciclo_nuevo()
    assert maquina.requieren_accion([ciclo], INICIO + timedelta(days=1)) == []


def test_el_mensaje_del_aviso_dice_de_quien_es_el_turno(maquina: MaquinaCiclo) -> None:
    """Puede terminar en una pantalla de bloqueo: dice que atender y a quien le
    toca, nunca que tiene el paciente.

    "PAC vencido" obliga a abrir el expediente para saber si te toca;
    "PAC vencido — turno del hospital receptor" se resuelve leyendo el correo.
    """
    ciclo = ciclo_nuevo()
    mensaje = maquina.evaluar(ciclo, INICIO + timedelta(days=45)).mensaje()
    assert mensaje == (
        "P-1: En preparación vencido hace 15 días — turno de "
        "Equipo de transición del INSN"
    )
