"""Descarga las fuentes manuscritas del corpus. Se corre una vez.

Todas son de Google Fonts con licencia OFL o Apache: libres para cualquier uso,
incluido comercial. No se versionan en el repositorio — se descargan.

    python -m relevo.interfaz.cli.descargar_fuentes

Si la red del evento bloquea GitHub, cualquiera del equipo las descarga una vez
y las comparte por USB: son ~2 MB en total.
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

BASE = "https://raw.githubusercontent.com/google/fonts/main/"

# Catalogo verificado: las 17 tienen juego latino completo con tildes y enie.
# Se comprobo una por una con `ImageFont.getmask` sobre "aeiouAEIOUnN" acentuado.
FUENTES: dict[str, str] = {
    # ── manuscritas ──────────────────────────────────────────────────────────
    "IndieFlower": "ofl/indieflower/IndieFlower-Regular.ttf",
    "PatrickHand": "ofl/patrickhand/PatrickHand-Regular.ttf",
    "ArchitectsDaughter": "ofl/architectsdaughter/ArchitectsDaughter-Regular.ttf",
    "CoveredByYourGrace": "ofl/coveredbyyourgrace/CoveredByYourGrace.ttf",
    "BadScript": "ofl/badscript/BadScript-Regular.ttf",
    "Zeyada": "ofl/zeyada/Zeyada.ttf",
    "DawningofaNewDay": "ofl/dawningofanewday/DawningofaNewDay.ttf",
    "NothingYouCouldDo": "ofl/nothingyoucoulddo/NothingYouCouldDo.ttf",
    "CaveatBrush": "ofl/caveatbrush/CaveatBrush-Regular.ttf",
    "SwankyandMooMoo": "ofl/swankyandmoomoo/SwankyandMooMoo.ttf",
    "Kalam": "ofl/kalam/Kalam-Regular.ttf",
    "ShadowsIntoLight": "apache/shadowsintolight/ShadowsIntoLight-Regular.ttf",
    "HomemadeApple": "apache/homemadeapple/HomemadeApple-Regular.ttf",
    "RockSalt": "apache/rocksalt/RockSalt-Regular.ttf",
    "Schoolbell": "apache/schoolbell/Schoolbell-Regular.ttf",
    # ── de maquina, para el caso tipeado ─────────────────────────────────────
    "CourierPrime": "ofl/courierprime/CourierPrime-Regular.ttf",
    "CutiveMono": "ofl/cutivemono/CutiveMono-Regular.ttf",
    "SpecialElite": "apache/specialelite/SpecialElite-Regular.ttf",
}

DE_MAQUINA = frozenset({"CourierPrime", "CutiveMono", "SpecialElite"})


def carpeta_fuentes() -> Path:
    """assets/fuentes/ en la raiz del proyecto."""
    return Path(__file__).resolve().parents[4] / "assets" / "fuentes"


def manuscritas(carpeta: Path | None = None) -> list[Path]:
    carpeta = carpeta or carpeta_fuentes()
    return sorted(f for f in carpeta.glob("*.ttf") if f.stem not in DE_MAQUINA)


def de_maquina(carpeta: Path | None = None) -> list[Path]:
    carpeta = carpeta or carpeta_fuentes()
    return sorted(f for f in carpeta.glob("*.ttf") if f.stem in DE_MAQUINA)


def descargar(destino: Path | None = None) -> int:
    destino = destino or carpeta_fuentes()
    destino.mkdir(parents=True, exist_ok=True)
    ok = 0
    for nombre, ruta in FUENTES.items():
        salida = destino / f"{nombre}.ttf"
        if salida.exists():
            ok += 1
            continue
        try:
            r = requests.get(
                BASE + ruta, timeout=30, headers={"User-Agent": "relevo/1.0"}
            )
            if r.status_code == 200 and len(r.content) > 5_000:
                salida.write_bytes(r.content)
                print(f"  ok   {nombre:22s} {len(r.content):>8,} bytes")
                ok += 1
            else:
                print(f"  FALLO {nombre:22s} HTTP {r.status_code}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — script de utilidad
            print(f"  FALLO {nombre:22s} {type(exc).__name__}", file=sys.stderr)
    print(f"\n{ok}/{len(FUENTES)} fuentes disponibles en {destino}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if descargar() >= 8 else 1)
