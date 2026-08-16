"""BLOQUEANTE — ningun .js pasa de 200 lineas, y fetch() solo vive en api.js.

═══════════════════════════════════════════════════════════════════════════════
QUE SALIO MAL Y QUE VIGILA ESTO
═══════════════════════════════════════════════════════════════════════════════

El segundo MVP del equipo eran tres archivos de ~2000 lineas sin capas. No se
pudo integrar: el coste de desenredarlo superaba el de reescribirlo.

El frontend nuevo no tiene framework ni paso de compilacion, pero SI tiene
capas, y estas dos reglas son lo que las mantiene:

  1. Ningun archivo supera las 200 lineas.
  2. `fetch()` aparece en un solo sitio.

Las dos son verificables por script, que es la diferencia entre una regla y una
buena intencion.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
WEB = RAIZ / "src" / "relevo" / "interfaz" / "web"
JS = WEB / "estatico" / "js"
LIMITE = 200


def archivos_js() -> list[Path]:
    return sorted(JS.rglob("*.js"))


def test_hay_frontend_que_verificar() -> None:
    """Un test que pasa porque no encontro archivos no verifica nada."""
    assert len(archivos_js()) >= 8, "el frontend deberia tener al menos 8 modulos"


@pytest.mark.bloqueante
def test_ningun_archivo_js_supera_las_200_lineas() -> None:
    excesos = [
        f"{a.relative_to(RAIZ)}: {len(a.read_text(encoding='utf-8').splitlines())}"
        for a in archivos_js()
        if len(a.read_text(encoding="utf-8").splitlines()) > LIMITE
    ]

    assert not excesos, (
        f"Archivos por encima de {LIMITE} lineas:\n  " + "\n  ".join(excesos)
        + "\n\nPartirlos por responsabilidad, no por tamano. Un archivo que no "
        "cabe en la cabeza de una persona es donde la gente empieza a anadir "
        "cosas donde caben en vez de donde van."
    )


@pytest.mark.bloqueante
def test_fetch_solo_aparece_en_api_js() -> None:
    """Cuando cada vista hace su propia llamada, cambiar una cabecera —o anadir
    la de sesion cuando exista autenticacion— obliga a tocar diez archivos, y
    siempre queda uno sin tocar."""
    patron = re.compile(r"\bfetch\s*\(")
    infractores = [
        str(a.relative_to(RAIZ))
        for a in archivos_js()
        if a.name != "api.js" and patron.search(a.read_text(encoding="utf-8"))
    ]

    assert not infractores, (
        "fetch() fuera de api.js:\n  " + "\n  ".join(infractores)
        + "\n\nTodas las llamadas pasan por api.js, que es donde viven las "
        "cabeceras y el manejo de errores."
    )


def test_api_js_si_usa_fetch() -> None:
    """La otra mitad: si api.js dejara de usar fetch, la regla de arriba
    pasaria trivialmente y nadie se enteraria de que el frontend no habla con
    nadie."""
    api = (JS / "api.js").read_text(encoding="utf-8")
    assert "fetch(" in api


@pytest.mark.bloqueante
def test_el_script_de_verificacion_esta_de_acuerdo() -> None:
    """El mismo limite comprobado por las dos vias.

    El script existe para poder correrlo a mano y en un build; el test, para
    que nadie lo olvide. Si los dos discreparan, uno de los dos estaria
    mintiendo.
    """
    import sys

    sys.path.insert(0, str(RAIZ / "scripts"))
    from verificar_tamano_archivos import LIMITE_JS, revisar

    assert LIMITE_JS == LIMITE
    assert revisar() == []


# ═══════════════════════════════════════════════════════════════════════════
# Las capas del frontend
# ═══════════════════════════════════════════════════════════════════════════


def test_las_vistas_no_se_importan_entre_si_salvo_por_una_excepcion() -> None:
    """Una vista que importa a otra es el principio del archivo de 2000 lineas.

    La unica excepcion tolerada es `leccion.js`, que reutiliza `marcar()` de
    `entrenate.js`: son la misma pantalla en dos niveles de detalle, y duplicar
    esa funcion habria dejado dos sitios donde arreglar el mismo fallo.
    """
    vistas = sorted((JS / "vistas").glob("*.js"))
    assert vistas

    infracciones: list[str] = []
    for archivo in vistas:
        texto = archivo.read_text(encoding="utf-8")
        for otra in vistas:
            if otra.name == archivo.name:
                continue
            if f"./{otra.stem}.js" in texto:
                infracciones.append(f"{archivo.name} importa {otra.name}")

    assert infracciones == ["leccion.js importa entrenate.js"], infracciones


def test_cada_vista_exporta_render() -> None:
    """El contrato del router: una vista es algo que sabe pintarse."""
    for archivo in sorted((JS / "vistas").glob("*.js")):
        texto = archivo.read_text(encoding="utf-8")
        assert "export async function render" in texto, (
            f"{archivo.name} no exporta render()"
        )
