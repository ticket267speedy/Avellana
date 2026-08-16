"""Falla si algun archivo del frontend se pasa de tamano.

═══════════════════════════════════════════════════════════════════════════════
POR QUE EXISTE ESTE SCRIPT
═══════════════════════════════════════════════════════════════════════════════

El segundo MVP del equipo eran tres archivos de ~2000 lineas sin capas. No se
pudo integrar: el coste de desenredarlo superaba el de reescribirlo.

Este limite es la respuesta directa y verificable a eso. Doscientas lineas no
es un numero magico — es el punto en el que un archivo deja de caber en la
cabeza de una persona, y a partir del cual la gente empieza a anadir cosas
donde caben en vez de donde van.

Se corre en la suite (`tests/interfaz/test_tamano_archivos_js.py`) y tambien a
mano:

    python scripts/verificar_tamano_archivos.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "src" / "relevo" / "interfaz" / "web"

LIMITE_JS = 200
LIMITE_CSS = 500
"""El CSS admite mas porque una regla ocupa tres lineas y no tiene ramas: 200
lineas de CSS son una pantalla, 200 de JS son una decision de diseno."""


def contar(archivo: Path) -> int:
    return len(archivo.read_text(encoding="utf-8").splitlines())


def revisar() -> list[str]:
    """Los archivos que se pasan, con su tamano. Vacio si todo esta bien."""
    excesos: list[str] = []

    for archivo in sorted(WEB.rglob("*.js")):
        lineas = contar(archivo)
        if lineas > LIMITE_JS:
            excesos.append(
                f"{archivo.relative_to(RAIZ)}: {lineas} lineas (limite {LIMITE_JS})"
            )

    for archivo in sorted(WEB.rglob("*.css")):
        lineas = contar(archivo)
        if lineas > LIMITE_CSS:
            excesos.append(
                f"{archivo.relative_to(RAIZ)}: {lineas} lineas (limite {LIMITE_CSS})"
            )

    return excesos


def main() -> int:
    if not WEB.exists():
        print(f"No existe {WEB}: nada que revisar.")
        return 0

    excesos = revisar()
    if excesos:
        print("Archivos del frontend por encima del limite:")
        for linea in excesos:
            print(f"  {linea}")
        print(
            "\nUn archivo que no cabe en la cabeza de una persona es donde la "
            "gente empieza a anadir cosas donde caben en vez de donde van. "
            "Partirlo por responsabilidad, no por tamano."
        )
        return 1

    total_js = sum(1 for _ in WEB.rglob("*.js"))
    print(f"{total_js} archivos .js, ninguno pasa de {LIMITE_JS} lineas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
