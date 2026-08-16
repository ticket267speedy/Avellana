"""BLOQUEANTE — ningun dato clinico se guarda en el navegador.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTO NO ES UNA PREFERENCIA
═══════════════════════════════════════════════════════════════════════════════

La **Ley 29733** clasifica los datos de salud como **datos sensibles**
(art. 2.5). Guardarlos en `localStorage` —sin cifrado, sin control de acceso y
sin registro de quien los toco— no es una implementacion incompleta: **es una
que no se puede desplegar.**

Y hay un motivo practico igual de fuerte: un portatil compartido en un
consultorio conserva ese `localStorage` para el siguiente que se siente delante.

Todo el estado del cliente vive en memoria (`estado.js`) y se pierde al
recargar. Esa perdida es deliberada, y es la unica politica de retencion que
este proyecto puede prometer hoy sin mentir.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
WEB = RAIZ / "src" / "relevo" / "interfaz" / "web"

# Todo lo que persiste algo en el navegador.
ALMACENES = (
    "localStorage",
    "sessionStorage",
    "indexedDB",
    "openDatabase",
    # Escribir una cookie desde el cliente es la misma fuga con otro nombre.
    "document.cookie",
)


def archivos_del_frontend() -> list[Path]:
    return sorted([*WEB.rglob("*.js"), *WEB.rglob("*.html")])


def test_hay_frontend_que_verificar() -> None:
    assert len(archivos_del_frontend()) >= 8


@pytest.mark.bloqueante
def test_no_se_usa_ningun_almacenamiento_del_navegador() -> None:
    infracciones: list[str] = []

    for archivo in archivos_del_frontend():
        texto = archivo.read_text(encoding="utf-8")
        for linea_numero, linea in enumerate(texto.splitlines(), start=1):
            # Los comentarios que EXPLICAN por que no se usa son legitimos y
            # valiosos: son donde vive el motivo. Se saltan.
            desnuda = linea.strip()
            if desnuda.startswith("//") or desnuda.startswith("*"):
                continue
            for almacen in ALMACENES:
                if almacen in linea:
                    infracciones.append(
                        f"{archivo.relative_to(RAIZ)}:{linea_numero} · {almacen}"
                    )

    assert not infracciones, (
        "El frontend guarda datos en el navegador:\n  " + "\n  ".join(infracciones)
        + "\n\nLa Ley 29733 clasifica los datos de salud como datos sensibles. "
        "Guardarlos sin cifrado, sin control de acceso y sin registro de quien "
        "los toco no es una implementacion incompleta: es una que no se puede "
        "desplegar."
    )


@pytest.mark.bloqueante
def test_el_estado_del_cliente_vive_en_memoria() -> None:
    """La contraparte: tiene que existir el sitio donde SI se guarda.

    Sin esto, el test de arriba pasaria igual en un frontend que no guarda nada
    porque no funciona.
    """
    estado = (WEB / "estatico" / "js" / "estado.js").read_text(encoding="utf-8")

    assert "const estado = {" in estado
    assert "new Map()" in estado, "la cache del cliente deberia ser un Map en memoria"
    # Y el motivo tiene que estar escrito ahi, no solo en este test: quien abra
    # el archivo para anadir persistencia tiene que leerlo antes.
    assert "29733" in estado


@pytest.mark.bloqueante
def test_cambiar_de_rol_vacia_la_cache() -> None:
    """Si la cache sobreviviera a un cambio de rol, una vista podria pintar con
    datos que el rol nuevo no tiene derecho a ver — que es exactamente la fuga
    que el aislamiento por establecimiento viene a impedir."""
    estado = (WEB / "estatico" / "js" / "estado.js").read_text(encoding="utf-8")

    funcion = re.search(r"export function fijarRol\(.*?\n}", estado, re.DOTALL)
    assert funcion, "no se encontro fijarRol()"
    assert "cache.clear()" in funcion.group(0)


def test_el_html_no_incrusta_datos_de_paciente() -> None:
    """El unico HTML es un contenedor vacio. Si el servidor renderizara datos
    dentro, quedarian en el historial del navegador y en la cache del disco."""
    indice = (WEB / "index.html").read_text(encoding="utf-8")

    for sospechoso in ("DEMO-0001", "diagnostico", "CIE", "dosis"):
        assert sospechoso not in indice, (
            f"index.html contiene '{sospechoso}': el HTML es un contenedor, "
            "los datos llegan por la API y viven en memoria."
        )
