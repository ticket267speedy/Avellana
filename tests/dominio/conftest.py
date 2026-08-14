"""Politica clinica provisional, para los tests del dominio.

Esto vivia en `dominio/servicios/` como `ParametrosIUT.provisionales()` y
`PoliticaPlazos.provisionales()`. Estaba mal ubicado: eran valores marcados
como PROVISIONALES y sin aprobar por ningun medico, disponibles como valor por
defecto de codigo de produccion. Cualquiera podia escribir `CalculadoraIUT()` y
obtener numeros con aspecto legitimo calculados con pesos que nadie valido.

Aqui son lo que en realidad son: material de prueba. La politica clinica de
produccion se carga de `config/*.yaml` y de ningun otro lado.

TODO (bloque 7, cargador YAML): un test de infraestructura debe comparar estos
valores contra los archivos de `config/` y fallar si se separan. Mientras no
exista el cargador, la copia se mantiene a mano y la fuente de verdad es el
YAML — si los dos discrepan, el que esta mal es este archivo.
"""

from __future__ import annotations

import pytest

from relevo.dominio.entidades.ciclo_transicion import EstadoCiclo
from relevo.dominio.entidades.diagnostico import TipoSeguro
from relevo.dominio.servicios.calculadora_iut import (
    X1_URGENCIA_TEMPORAL,
    X2_COMPLEJIDAD,
    X3_SEVERIDAD,
    X4_DEPENDENCIA_TECNOLOGICA,
    X5_BRECHA_PREPARACION,
    X6_RIESGO_PERDIDA,
    X7_BARRERA_ACCESO,
    X8_CONTINUIDAD_SEGURO,
    CalculadoraIUT,
    ParametrosIUT,
)
from relevo.dominio.servicios.maquina_ciclo import MaquinaCiclo, PoliticaPlazos


def parametros_iut_provisionales() -> ParametrosIUT:
    """Copia de `config/reglas_transicion.yaml` v0.1.0-provisional."""
    return ParametrosIUT(
        beta_0=-4.0,
        betas={
            # Suman exactamente 10.0: con beta_0 = -4.0 el rango de z es
            # [-4.0, +6.0]. Numeros redondos para poder verificar la
            # aritmetica en papel.
            X1_URGENCIA_TEMPORAL: 3.0,  # domina: el corte a los 18 es duro
            X2_COMPLEJIDAD: 1.2,
            X3_SEVERIDAD: 1.5,
            X4_DEPENDENCIA_TECNOLOGICA: 1.0,
            X5_BRECHA_PREPARACION: 1.0,
            X6_RIESGO_PERDIDA: 0.8,
            X7_BARRERA_ACCESO: 0.6,
            X8_CONTINUIDAD_SEGURO: 0.9,
        },
        horizonte_meses=48,
        # x2 cuenta sistemas comprometidos, no diagnosticos; x3 mide la
        # gravedad del peor, no la suma. Son dos preguntas distintas a
        # proposito: antes las dos crecian con el numero de codigos y el
        # desglose presentaba la misma senal como dos razones.
        categorias_techo=5,
        severidad_maxima_posible=3.0,
        peso_maximo_dispositivos=6.0,
        traq_minimo=1.0,
        traq_maximo=5.0,
        traq_imputacion=0.5,
        intervalo_control_dias=180,
        lima_metropolitana=frozenset({"lima", "lima metropolitana", "callao"}),
        severidad_por_categoria={
            "neuromuscular": 2,
            "cardiovascular": 3,
            "respiratoria": 3,
            "renal": 3,
            "gastrointestinal": 2,
            "hematologica_inmunologica": 2,
            "metabolica": 2,
            "congenita_genetica": 2,
            "malignidad": 3,
            "neonatal": 1,
            "dependencia_tecnologica": 3,
            "trasplante": 3,
            "otra": 1,
        },
        peso_dispositivos={
            "traqueostomia": 3,
            "ventilacion_mecanica": 3,
            "ventilacion_no_invasiva": 2,
            "dialisis_peritoneal": 3,
            "hemodialisis": 3,
            "gastrostomia": 2,
            "yeyunostomia": 2,
            "cateter_venoso_central": 2,
            "derivacion_ventriculoperitoneal": 2,
            "marcapasos": 2,
            "colostomia": 1,
            "sonda_vesical": 1,
            "oxigeno_domiciliario": 1,
            "bomba_insulina": 1,
            "audifono": 0,
            "protesis": 0,
        },
        riesgo_seguro={
            # VERIFICADO (Ley 26790): en EsSalud se deja de ser derechohabiente
            # a los 18 salvo incapacidad total acreditada.
            TipoSeguro.ESSALUD.value: 1.0,
            # NO VERIFICADO — TODO: Servicio Social INSN.
            TipoSeguro.SIS.value: 0.5,
            TipoSeguro.PRIVADO.value: 0.3,
            # Sin seguro no hay continuidad que preservar: riesgo maximo.
            TipoSeguro.NINGUNO.value: 1.0,
        },
        riesgo_seguro_verificado={
            TipoSeguro.ESSALUD.value: True,
            TipoSeguro.SIS.value: False,
            TipoSeguro.PRIVADO.value: False,
            TipoSeguro.NINGUNO.value: True,
        },
        umbral_rojo=0.80,
        umbral_ambar=0.50,
        confianza_minima=0.70,
    )


def politica_plazos_provisional() -> PoliticaPlazos:
    """Copia de `config/plazos_ciclo.yaml` v0.1.0."""
    return PoliticaPlazos(
        dias_por_estado={
            # Tramite puramente administrativo (NT 018-MINSA/DGSP-V.01).
            EstadoCiclo.PASAPORTE_EMITIDO: 7,
            # Solo el 23.14 % se acepta en 24 h; el 13.6 % vuelve por
            # informacion incompleta (DIRIS Lima Norte).
            EstadoCiclo.REFERENCIA_REGISTRADA: 30,
            # Mediana observada aceptacion -> cita: 80 a 85 dias.
            EstadoCiclo.REFERENCIA_ACEPTADA: 120,
            # Contado desde la fecha de la cita, no desde su programacion.
            EstadoCiclo.CITA_PROGRAMADA: 30,
            # Plazo nominal. En la practica casi nunca se cumple: la
            # contrarreferencia llega en el 0.55 % de los casos.
            EstadoCiclo.CITA_CUMPLIDA: 30,
        },
        fraccion_preaviso=0.25,
        minimo_dias_preaviso=3,
    )


@pytest.fixture
def parametros() -> ParametrosIUT:
    return parametros_iut_provisionales()


@pytest.fixture
def calculadora(parametros: ParametrosIUT) -> CalculadoraIUT:
    return CalculadoraIUT(parametros=parametros)


@pytest.fixture
def politica() -> PoliticaPlazos:
    return politica_plazos_provisional()


@pytest.fixture
def maquina(politica: PoliticaPlazos) -> MaquinaCiclo:
    return MaquinaCiclo(politica=politica)
