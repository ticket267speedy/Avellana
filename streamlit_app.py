"""Launcher usado por Streamlit Cloud para arrancar la app principal del proyecto.

No se usa __init__.py como punto de entrada: Streamlit Cloud busca un archivo
`streamlit_app.py` en la raiz del repositorio.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

APP_FILE = SRC / "relevo" / "interfaz" / "web" / "app.py"
if not APP_FILE.exists():
    raise FileNotFoundError(f"No se encontró la app principal en: {APP_FILE}")

# Ejecuta el archivo de la aplicación principal como si fuera el script de entrada.
runpy.run_path(str(APP_FILE), run_name="__main__")
