"""El YAML y la copia provisional de los tests no pueden separarse.

Este test cierra el TODO que dejo la revision del nucleo. `conftest.py` tiene
una copia en codigo de `config/*.yaml` para que el dominio se pruebe sin leer
archivos; si las dos versiones divergen, los cinco casos calculados a mano
estarian validando una politica clinica que ya no es la que corre en produccion.

El YAML manda. Si este test falla, el que esta mal es `conftest.py`.
"""

from __future__ import annotations

import pytest

from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.infraestructura.configuracion.cargador_yaml import (
    cargar_parametros_iut,
    cargar_politica_plazos,
)

from tests.dominio.conftest import (
    parametros_iut_provisionales,
    politica_plazos_provisional,
)


def test_los_parametros_del_yaml_son_los_de_los_tests() -> None:
    del_archivo = cargar_parametros_iut()
    de_los_tests = parametros_iut_provisionales()

    assert del_archivo.beta_0 == de_los_tests.beta_0
    assert del_archivo.betas == de_los_tests.betas
    assert del_archivo.horizonte_meses == de_los_tests.horizonte_meses
    assert del_archivo.categorias_techo == de_los_tests.categorias_techo
    assert del_archivo.severidad_maxima_posible == de_los_tests.severidad_maxima_posible
    assert del_archivo.peso_maximo_dispositivos == de_los_tests.peso_maximo_dispositivos
    assert del_archivo.traq_imputacion == de_los_tests.traq_imputacion
    assert del_archivo.intervalo_control_dias == de_los_tests.intervalo_control_dias
    assert del_archivo.lima_metropolitana == de_los_tests.lima_metropolitana
    assert del_archivo.severidad_por_categoria == de_los_tests.severidad_por_categoria
    assert del_archivo.peso_dispositivos == de_los_tests.peso_dispositivos
    assert del_archivo.riesgo_seguro == de_los_tests.riesgo_seguro
    assert del_archivo.riesgo_seguro_verificado == de_los_tests.riesgo_seguro_verificado
    assert del_archivo.umbral_rojo == de_los_tests.umbral_rojo
    assert del_archivo.umbral_ambar == de_los_tests.umbral_ambar
    assert del_archivo.confianza_minima == de_los_tests.confianza_minima


def test_los_plazos_del_yaml_son_los_de_los_tests() -> None:
    del_archivo = cargar_politica_plazos()
    de_los_tests = politica_plazos_provisional()

    assert del_archivo.dias_por_estado == de_los_tests.dias_por_estado
    assert del_archivo.fraccion_preaviso == de_los_tests.fraccion_preaviso
    assert del_archivo.minimo_dias_preaviso == de_los_tests.minimo_dias_preaviso


def test_una_clave_ausente_detiene_la_carga(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Nada se completa con un valor razonable: un valor razonable inventado es
    justo lo que este proyecto no puede permitirse."""
    incompleto = tmp_path / "reglas.yaml"
    incompleto.write_text("iut:\n  beta_0: -4.0\n", encoding="utf-8")

    with pytest.raises(ConfiguracionIncompleta) as error:
        cargar_parametros_iut(incompleto)
    assert "iut.betas" in str(error.value)
