"""Carga la politica clinica desde `config/*.yaml`.

Este adaptador existe porque el dominio no toca el disco. Es tambien la unica
via legitima para construir `ParametrosIUT` y `PoliticaPlazos` en produccion:
desde la revision del nucleo, esas clases no tienen valores por defecto, de modo
que si este cargador no corre, el sistema no arranca. Es deliberado — antes
`CalculadoraIUT()` producia numeros con aspecto legitimo calculados con pesos
que ningun medico aprobo.

Todo lo que falte se reporta como `ConfiguracionIncompleta` con el nombre de la
clave y el archivo. Nada se completa con un valor razonable: un valor razonable
inventado es exactamente lo que este proyecto no puede permitirse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from relevo.dominio.entidades.ciclo_transicion import EstadoCiclo
from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.dominio.servicios.calculadora_iut import ParametrosIUT
from relevo.dominio.servicios.maquina_ciclo import PoliticaPlazos

# La raiz del repositorio, cuatro niveles por encima de este archivo:
# src/relevo/infraestructura/configuracion/cargador_yaml.py
RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
CONFIG = RAIZ_PROYECTO / "config"


def _leer(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        raise ConfiguracionIncompleta(
            f"No existe {ruta}. La politica clinica se carga de archivo: "
            "sin el, el sistema no arranca."
        )
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ConfiguracionIncompleta(f"{ruta} no contiene un mapa YAML.")
    return datos


def _exigir(datos: dict[str, Any], clave: str, archivo: str) -> Any:
    """Lee una clave o se detiene. Las claves anidadas van con puntos."""
    actual: Any = datos
    for parte in clave.split("."):
        if not isinstance(actual, dict) or parte not in actual:
            raise ConfiguracionIncompleta(
                f"Falta '{clave}' en {archivo}. Nadie debe inventar este valor."
            )
        actual = actual[parte]
    if actual is None:
        raise ConfiguracionIncompleta(
            f"'{clave}' esta vacio en {archivo}. Un valor nulo no es un valor."
        )
    return actual


def cargar_parametros_iut(ruta: Path | None = None) -> ParametrosIUT:
    """Construye `ParametrosIUT` desde `config/reglas_transicion.yaml`."""
    ruta = ruta or CONFIG / "reglas_transicion.yaml"
    datos = _leer(ruta)
    nombre = ruta.name

    betas_yaml = _exigir(datos, "iut.betas", nombre)
    riesgo_yaml = _exigir(datos, "riesgo_seguro", nombre)

    # El YAML guarda valor, verificado y fuente por regimen; el dominio solo
    # necesita los dos primeros. La fuente se queda en el archivo, que es donde
    # sirve: es lo que se lee cuando alguien pregunta de donde salio el numero.
    riesgo: dict[str, float] = {}
    verificado: dict[str, bool] = {}
    for regimen, detalle in riesgo_yaml.items():
        if not isinstance(detalle, dict) or "valor" not in detalle:
            raise ConfiguracionIncompleta(
                f"riesgo_seguro.{regimen} necesita al menos 'valor' en {nombre}."
            )
        riesgo[str(regimen)] = float(detalle["valor"])
        verificado[str(regimen)] = bool(detalle.get("verificado", False))

    return ParametrosIUT(
        beta_0=float(_exigir(datos, "iut.beta_0", nombre)),
        betas={str(k): float(v) for k, v in betas_yaml.items()},
        horizonte_meses=int(_exigir(datos, "iut.normalizacion.x1_horizonte_meses", nombre)),
        categorias_techo=int(
            _exigir(datos, "iut.normalizacion.x2_categorias_techo", nombre)
        ),
        severidad_maxima_posible=float(
            _exigir(datos, "iut.normalizacion.x3_severidad_maxima", nombre)
        ),
        peso_maximo_dispositivos=float(
            _exigir(datos, "iut.normalizacion.x4_peso_maximo", nombre)
        ),
        traq_minimo=float(_exigir(datos, "iut.normalizacion.x5_traq_minimo", nombre)),
        traq_maximo=float(_exigir(datos, "iut.normalizacion.x5_traq_maximo", nombre)),
        traq_imputacion=float(
            _exigir(datos, "iut.normalizacion.x5_imputacion_sin_dato", nombre)
        ),
        intervalo_control_dias=int(
            _exigir(datos, "iut.normalizacion.x6_intervalo_control_dias", nombre)
        ),
        lima_metropolitana=frozenset(
            str(z).strip().lower()
            for z in _exigir(datos, "iut.normalizacion.x7_lima_metropolitana", nombre)
        ),
        severidad_por_categoria={
            str(k): int(v)
            for k, v in _exigir(datos, "severidad_por_categoria", nombre).items()
        },
        peso_dispositivos={
            str(k): int(v) for k, v in _exigir(datos, "peso_dispositivos", nombre).items()
        },
        riesgo_seguro=riesgo,
        riesgo_seguro_verificado=verificado,
        umbral_rojo=float(_exigir(datos, "semaforo.umbral_rojo", nombre)),
        umbral_ambar=float(_exigir(datos, "semaforo.umbral_ambar", nombre)),
        confianza_minima=float(_exigir(datos, "semaforo.confianza_minima", nombre)),
    )


def cargar_capacidad_mensual(ruta: Path | None = None) -> int | None:
    """La capacidad del equipo de transicion, si alguien la declaro.

    None significa que no se sabe, y entonces el umbral rojo se queda en el
    valor fijo del YAML. TODO: confirmar con mentor.
    """
    ruta = ruta or CONFIG / "reglas_transicion.yaml"
    datos = _leer(ruta)
    valor = datos.get("semaforo", {}).get("capacidad_mensual_equipo")
    return None if valor is None else int(valor)


def cargar_politica_plazos(ruta: Path | None = None) -> PoliticaPlazos:
    """Construye `PoliticaPlazos` desde `config/plazos_ciclo.yaml`."""
    ruta = ruta or CONFIG / "plazos_ciclo.yaml"
    datos = _leer(ruta)
    nombre = ruta.name

    dias: dict[EstadoCiclo, int] = {}
    for transicion in _exigir(datos, "transiciones", nombre):
        desde = str(transicion["desde"])
        try:
            estado = EstadoCiclo[desde]
        except KeyError as error:
            raise ConfiguracionIncompleta(
                f"'{desde}' no es un estado del ciclo ({nombre}). "
                f"Estados validos: {', '.join(e.name for e in EstadoCiclo)}."
            ) from error
        dias[estado] = int(transicion["plazo_dias"])

    return PoliticaPlazos(
        dias_por_estado=dias,
        fraccion_preaviso=float(_exigir(datos, "preaviso.fraccion_restante", nombre)),
        minimo_dias_preaviso=int(_exigir(datos, "preaviso.minimo_dias", nombre)),
    )
