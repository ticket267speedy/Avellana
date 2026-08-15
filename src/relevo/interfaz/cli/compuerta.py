"""Arranca la compuerta que decide si la pagina web puede usar esta LLM.

    python -m relevo.interfaz.cli.compuerta

Luego se apunta el tunel a la compuerta en vez de a Ollama:

    cloudflared tunnel --url http://localhost:8787

Ver `docs/DESPLIEGUE.md` seccion 4.
"""

from __future__ import annotations

import argparse

from relevo.infraestructura.llm.compuerta import (
    OLLAMA_POR_DEFECTO,
    PUERTO_POR_DEFECTO,
    servir,
)


def main() -> None:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--puerto", type=int, default=PUERTO_POR_DEFECTO)
    analizador.add_argument("--ollama", default=OLLAMA_POR_DEFECTO)
    analizador.add_argument(
        "--cerrada",
        action="store_true",
        help="arrancar con la LLM apagada para la pagina web",
    )
    args = analizador.parse_args()
    servir(puerto=args.puerto, ollama=args.ollama, abierta=not args.cerrada)


if __name__ == "__main__":
    main()
