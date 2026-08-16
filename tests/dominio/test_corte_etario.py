"""El corte etario: la metrica estrella de fracaso.

Lo que este archivo fija, y que hay que poder decir sin dudar delante de un
jurado: **cumplir 18 anios no es el fracaso.** La primera cita en el hospital
de adultos ocurre, por definicion, despues de los 18. El fracaso es cumplir 18
sin destino asegurado.

Si estos tests se relajaran, el radar empezaria a contar como fracasos los
casos que van bien, y el numero que va arriba de todo dejaria de significar
nada.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.dominio.servicios.corte_etario import (
    DIAS_HORIZONTE_RIESGO,
    dias_para_corte,
    en_riesgo_de_corte,
    evaluar_corte_etario,
    fracasos,
    medir_corte_etario,
)

HOY = date(2026, 8, 16)


def nacido_hace(anios: int, dias: int = 0) -> date:
    return date(HOY.year - anios, HOY.month, HOY.day) - timedelta(days=dias)


def ciclo(
    fecha_nacimiento: date,
    estado: EstadoCiclo = EstadoCiclo.PREPARACION,
    dias_en_estado: int = 0,
) -> CicloTransicion:
    """Un ciclo puesto directamente en el estado que interesa.

    Se construye el historial a mano en vez de recorrer el grafo porque lo que
    se prueba aqui es el corte etario, no las transiciones. Recorrerlas haria
    que un cambio en el grafo rompiera tests que no hablan del grafo.
    """
    from relevo.dominio.entidades.ciclo_transicion import EventoCiclo

    fecha = HOY - timedelta(days=dias_en_estado)
    c = CicloTransicion(
        paciente_id="PAC-1",
        fecha_inicio=fecha - timedelta(days=1),
        fecha_nacimiento=fecha_nacimiento,
    )
    c.historial.append(
        EventoCiclo(
            estado=estado,
            fecha=fecha,
            fuente_confirmacion=(
                FuenteConfirmacion.CONFIRMACION_RECEPTOR
                if estado is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA
                else None
            ),
        )
    )
    return c


# ═══════════════════════════════════════════════════════════════════════════
# Que es fracaso y que no
# ═══════════════════════════════════════════════════════════════════════════


def test_cumplir_dieciocho_con_destino_asegurado_no_es_fracaso() -> None:
    """La primera cita en el hospital de adultos ocurre despues de los 18. Un
    ciclo que sigue avanzando con el paciente ya mayor de edad esta funcionando
    como debe."""
    for estado in (
        EstadoCiclo.ACEPTADO_CON_SERVICIO,
        EstadoCiclo.CITA_PROGRAMADA,
        EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
    ):
        assert evaluar_corte_etario(ciclo(nacido_hace(18, 30), estado), HOY) is None


@pytest.mark.parametrize(
    "estado",
    [
        EstadoCiclo.PREPARACION,
        EstadoCiclo.REFERENCIA_ENVIADA,
        EstadoCiclo.RECEPCION_CONFIRMADA,
        EstadoCiclo.EN_EVALUACION,
        EstadoCiclo.PERDIDA_DE_SEGUIMIENTO,
    ],
)
def test_cumplir_dieciocho_sin_destino_asegurado_si_es_fracaso(
    estado: EstadoCiclo,
) -> None:
    evento = evaluar_corte_etario(ciclo(nacido_hace(18, 30), estado), HOY)
    assert evento is not None
    assert evento.estado_al_cumplir is estado
    assert evento.id_paciente == "PAC-1"


def test_un_menor_de_dieciocho_nunca_es_fracaso_todavia() -> None:
    """Aunque este en PREPARACION: todavia hay tiempo. Contarlo como fracaso
    seria contar un dano que no ocurrio."""
    assert evaluar_corte_etario(ciclo(nacido_hace(17), EstadoCiclo.PREPARACION), HOY) is None


def test_los_dias_parado_se_cuentan_al_cumplir_dieciocho_no_hoy() -> None:
    """Un paciente que cumplio 18 en PREPARACION habiendo entrado ayer es un
    caso detectado tarde; uno que llevaba 200 dias ahi es un expediente que el
    sistema vio y nadie movio. Solo la segunda la puede corregir Relevo."""
    # Cumplio 18 hace 30 dias; entro al estado hace 100.
    evento = evaluar_corte_etario(
        ciclo(nacido_hace(18, 30), EstadoCiclo.PREPARACION, dias_en_estado=100), HOY
    )
    assert evento is not None
    assert evento.dias_en_ese_estado == 70  # 100 - 30


def test_si_entro_al_estado_despues_del_cumpleanios_el_conteo_es_cero() -> None:
    """No un numero negativo, que en un tablero se lee como un error."""
    evento = evaluar_corte_etario(
        ciclo(nacido_hace(18, 30), EstadoCiclo.PREPARACION, dias_en_estado=5), HOY
    )
    assert evento is not None
    assert evento.dias_en_ese_estado == 0


def test_sin_fecha_de_nacimiento_se_detiene_en_vez_de_imputar() -> None:
    """Una metrica de fracaso calculada sobre una edad supuesta es peor que no
    tener metrica: da un numero con aspecto de dato."""
    c = CicloTransicion(paciente_id="SIN-FECHA", fecha_inicio=HOY)
    with pytest.raises(ConfiguracionIncompleta):
        evaluar_corte_etario(c, HOY)


# ═══════════════════════════════════════════════════════════════════════════
# La alerta temprana
# ═══════════════════════════════════════════════════════════════════════════


def test_dias_para_corte_cuenta_hasta_el_cumpleanios_dieciocho() -> None:
    assert dias_para_corte(nacido_hace(18, 0), HOY) == 0
    assert dias_para_corte(nacido_hace(17), HOY) == 365
    assert dias_para_corte(nacido_hace(18, 10), HOY) == -10


def test_esta_en_riesgo_si_cumple_dentro_del_horizonte_y_no_tiene_destino() -> None:
    c = ciclo(nacido_hace(17, 365 - 30), EstadoCiclo.EN_EVALUACION)
    assert 0 <= dias_para_corte(nacido_hace(17, 365 - 30), HOY) < DIAS_HORIZONTE_RIESGO
    assert en_riesgo_de_corte(c, HOY)


def test_no_esta_en_riesgo_si_ya_tiene_destino_asegurado() -> None:
    c = ciclo(nacido_hace(17, 365 - 30), EstadoCiclo.ACEPTADO_CON_SERVICIO)
    assert not en_riesgo_de_corte(c, HOY)


def test_el_que_ya_cumplio_no_cuenta_como_riesgo_sino_como_dano() -> None:
    """Mezclarlos daria un numero que baja cuando la situacion empeora."""
    c = ciclo(nacido_hace(18, 10), EstadoCiclo.PREPARACION)
    assert not en_riesgo_de_corte(c, HOY)
    assert evaluar_corte_etario(c, HOY) is not None


# ═══════════════════════════════════════════════════════════════════════════
# La metrica agregada — la que va arriba de todo en el radar
# ═══════════════════════════════════════════════════════════════════════════


def test_la_metrica_separa_riesgo_de_dano_consumado() -> None:
    cohorte = [
        # Dos en riesgo: cumplen pronto y no tienen destino.
        ciclo(nacido_hace(17, 365 - 20), EstadoCiclo.PREPARACION),
        ciclo(nacido_hace(17, 365 - 80), EstadoCiclo.EN_EVALUACION),
        # Uno que cumple pronto pero ya esta a salvo.
        ciclo(nacido_hace(17, 365 - 20), EstadoCiclo.ACEPTADO_CON_SERVICIO),
        # Dos danos consumados.
        ciclo(nacido_hace(18, 5), EstadoCiclo.REFERENCIA_ENVIADA),
        ciclo(nacido_hace(19), EstadoCiclo.PERDIDA_DE_SEGUIMIENTO),
        # Uno mayor de edad que si llego: no es fracaso.
        ciclo(nacido_hace(19), EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA),
        # Uno lejos del corte.
        ciclo(nacido_hace(15), EstadoCiclo.PREPARACION),
    ]

    metrica = medir_corte_etario(cohorte, HOY)

    assert metrica.en_riesgo_90_dias == 2
    assert metrica.ya_cumplieron_sin_destino == 2
    assert metrica.total_cohorte == 7
    assert metrica.hay_algo_que_hacer


def test_la_metrica_de_una_cohorte_vacia_no_divide_entre_cero() -> None:
    metrica = medir_corte_etario([], HOY)
    assert metrica.proporcion_sin_destino == 0.0
    assert not metrica.hay_algo_que_hacer


def test_los_fracasos_se_listan_del_mas_reciente_al_mas_viejo() -> None:
    """Un numero agregado no permite hacer nada: para llamar a alguien hace
    falta saber a quien."""
    cohorte = [
        ciclo(nacido_hace(20), EstadoCiclo.PREPARACION),
        ciclo(nacido_hace(18, 3), EstadoCiclo.PREPARACION),
        ciclo(nacido_hace(19), EstadoCiclo.PREPARACION),
    ]
    lista = fracasos(cohorte, HOY)
    assert len(lista) == 3
    assert lista[0].fecha_cumpleanios > lista[-1].fecha_cumpleanios
