"""Carga el contenido de Entrenate desde `config/lecciones_entrenate.yaml`.

El dominio no toca el disco: define `Leccion` y este adaptador la puebla. Es la
misma razon por la que los plazos y los betas del indice se cargan de archivo —
el contenido educativo es material que un profesional del INSN tiene que poder
corregir sin abrir un editor de codigo.

Se detiene en vez de suponer. Si el archivo no esta, si falta una habilidad o
si una leccion se declara COMPLETA sin fuentes, el sistema no arranca. Una
leccion a medias presentada como validada es exactamente lo que la regla 4 no
permite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from relevo.dominio.entidades.leccion import Fuente, Leccion, PasoLeccion
from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.dominio.objetos_valor.habilidad import EstadoContenido, Habilidad

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
CONFIG = RAIZ_PROYECTO / "config"


def cargar_lecciones(ruta: Path | None = None) -> dict[Habilidad, Leccion]:
    """El catalogo completo, indexado por habilidad.

    Se indexa por habilidad y no por numero porque asi lo consume el
    recomendador, y porque `Leccion.__post_init__` ya garantiza que numero y
    habilidad coinciden: tener dos indices seria tener dos verdades.
    """
    ruta = ruta or CONFIG / "lecciones_entrenate.yaml"
    if not ruta.exists():
        raise ConfiguracionIncompleta(
            f"No existe {ruta}. El contenido de Entrenate se carga de archivo: "
            "sin el, la ruta de aprendizaje no tiene nada que mostrar."
        )

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or "lecciones" not in datos:
        raise ConfiguracionIncompleta(f"{ruta} no declara 'lecciones'.")

    catalogo: dict[Habilidad, Leccion] = {}
    for cruda in datos["lecciones"]:
        leccion = _construir(cruda, ruta.name)
        catalogo[leccion.habilidad] = leccion

    faltantes = [h.name for h in Habilidad if h not in catalogo]
    if faltantes:
        raise ConfiguracionIncompleta(
            f"Faltan lecciones para: {', '.join(faltantes)} en {ruta.name}. "
            "Son siete habilidades y siete lecciones: una habilidad sin "
            "leccion es una casilla que el adolescente ve y no puede abrir."
        )
    return catalogo


def _construir(cruda: dict[str, Any], archivo: str) -> Leccion:
    numero = int(cruda["numero"])
    try:
        habilidad = Habilidad(str(cruda["habilidad"]))
    except ValueError as error:
        raise ConfiguracionIncompleta(
            f"'{cruda.get('habilidad')}' no es una habilidad de Entrenate "
            f"({archivo}). Validas: {', '.join(h.value for h in Habilidad)}."
        ) from error

    pasos = cruda.get("pasos") or {}
    estado = EstadoContenido(
        str(
            cruda.get(
                "estado_contenido",
                EstadoContenido.ESQUELETO_PENDIENTE_VALIDACION.value,
            )
        )
    )

    return Leccion(
        numero=numero,
        habilidad=habilidad,
        titulo=str(cruda.get("titulo", "")),
        objetivo=str(cruda.get("objetivo", "")).strip(),
        estado_contenido=estado,
        aprender=PasoLeccion("Aprender", str(pasos.get("aprender") or "")),
        practicar=PasoLeccion("Practicar", str(pasos.get("practicar") or "")),
        desafio=PasoLeccion("Desafio", str(pasos.get("desafio") or "")),
        tarea_real=PasoLeccion(
            "Tarea de la vida real", str(pasos.get("tarea_real") or "")
        ),
        retroalimentacion=PasoLeccion(
            "Retroalimentacion", str(pasos.get("retroalimentacion") or "")
        ),
        fuentes=tuple(
            Fuente(
                afirmacion=str(f["afirmacion"]),
                norma=str(f["norma"]),
                detalle=str(f.get("detalle", "")).strip(),
            )
            for f in cruda.get("fuentes", [])
        ),
    )
