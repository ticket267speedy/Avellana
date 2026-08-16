"""Un sistema completo sobre una base temporal, para los tests de la API.

Base temporal y no la del proyecto: un test que escriba en `data/relevo.db`
destruiria la cohorte que el equipo tiene preparada para ensayar el pitch.

El contenedor se sustituye con `dependency_overrides`, que es exactamente para
lo que la API lo pide por inyeccion en vez de importarlo como global.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from relevo.interfaz.api.dependencias import obtener_contenedor
from relevo.interfaz.api.principal import app
from relevo.interfaz.arranque import Contenedor, construir

HOY = date(2026, 8, 16)
RECEPTOR = "HOSPITAL NACIONAL  DOS DE MAYO"


@pytest.fixture(scope="session")
def contenedor_demo(tmp_path_factory: pytest.TempPathFactory) -> Contenedor:
    """Sembrado una sola vez por sesion: la siembra es determinista y lenta."""
    ruta: Path = tmp_path_factory.mktemp("relevo") / "prueba.db"
    contenedor = construir(persistente=True, ruta_bd=ruta)
    contenedor.sembrar_demo(
        n_pacientes=42,
        semilla_aleatoria=20260816,
        hoy=HOY,
        ciclos_abiertos=18,
        reparto_estados={},
        vencidos_forzados=3,
    )
    return contenedor


@pytest.fixture
def cliente(contenedor_demo: Contenedor) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_contenedor] = lambda: contenedor_demo
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def insn() -> dict[str, str]:
    return {"X-Relevo-Rol": "profesional_insn"}


@pytest.fixture
def receptor() -> dict[str, str]:
    return {
        "X-Relevo-Rol": "profesional_receptor",
        "X-Relevo-Establecimiento": RECEPTOR,
    }


@pytest.fixture
def paciente() -> dict[str, str]:
    return {"X-Relevo-Rol": "paciente"}


@pytest.fixture
def administrador() -> dict[str, str]:
    return {"X-Relevo-Rol": "administrador"}
