"""La regla de dependencia, verificada automaticamente.

PLAN_TECNICO §3.2:

        interfaz  ──────┐
                        ├──►  aplicacion  ──►  dominio
   infraestructura ─────┘                        ▲
                                                 │
                        (define los puertos que ambos implementan)

Por que este test es bloqueante y no una buena practica: la promesa central
del pitch es *"el nucleo no cambia; solo se cambia el adaptador de entrada
segun el sistema del hospital"*. Si el dominio importara SQLAlchemy o
`requests`, esa frase seria falsa y el jurado tendria razon en no creernos.

Este archivo es lo que convierte la afirmacion en algo demostrable en treinta
segundos delante de quien pregunte. Es una regla que se rompe sola si nadie la
vigila: basta un `import yaml` puesto con prisa a las tres de la manana.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
DOMINIO = RAIZ / "src" / "relevo" / "dominio"
APLICACION = RAIZ / "src" / "relevo" / "aplicacion"

# Modulos de la libreria estandar de esta version de Python. El dominio puede
# usarlos todos: `dataclasses`, `datetime`, `enum`, `math`, `re`, `abc`.
ESTANDAR = set(sys.stdlib_module_names)


def modulos_de(carpeta: Path) -> list[Path]:
    return sorted(p for p in carpeta.rglob("*.py") if p.name != "__init__.py")


def imports_de(archivo: Path) -> set[str]:
    """Los paquetes de primer nivel que importa un archivo.

    'from relevo.dominio.entidades.paciente import Paciente' -> 'relevo.dominio'
    'import yaml'                                            -> 'yaml'
    """
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    paquetes: set[str] = set()

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                paquetes.add(_raiz(alias.name))
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level > 0:
                # Import relativo: por definicion queda dentro del paquete.
                continue
            if nodo.module:
                paquetes.add(_raiz(nodo.module))
    return paquetes


def _raiz(nombre: str) -> str:
    """'relevo.dominio.entidades.paciente' -> 'relevo.dominio'; 'yaml' -> 'yaml'."""
    partes = nombre.split(".")
    if partes[0] == "relevo" and len(partes) > 1:
        return f"relevo.{partes[1]}"
    return partes[0]


# ═══════════════════════════════════════════════════════════════════════════
# La regla
# ═══════════════════════════════════════════════════════════════════════════


def test_hay_dominio_que_verificar() -> None:
    """Un test que pasa porque no encontro archivos no verifica nada."""
    assert len(modulos_de(DOMINIO)) >= 8


@pytest.mark.bloqueante
def test_el_dominio_no_depende_de_nada_externo() -> None:
    """Ni SQLAlchemy, ni FastAPI, ni requests, ni pydantic, ni yaml.

    Solo libreria estandar y el propio dominio. Si este test falla, la
    afirmacion del pitch dejo de ser cierta.
    """
    infracciones: list[str] = []

    for archivo in modulos_de(DOMINIO):
        permitidos = ESTANDAR | {"relevo.dominio"}
        externos = imports_de(archivo) - permitidos
        if externos:
            relativo = archivo.relative_to(RAIZ)
            infracciones.append(f"{relativo}: {', '.join(sorted(externos))}")

    assert not infracciones, (
        "El dominio importa paquetes externos y la regla de dependencia se "
        "rompio:\n  " + "\n  ".join(infracciones)
    )


@pytest.mark.bloqueante
def test_la_aplicacion_solo_importa_dominio() -> None:
    """Los casos de uso orquestan el dominio a traves de los puertos. Si
    importan un adaptador concreto, dejan de poder probarse con dobles y el
    hexagono se convierte en una cebolla mal cortada."""
    if not APLICACION.exists():
        pytest.skip("La capa de aplicacion aun no existe (bloque 9)")

    infracciones: list[str] = []
    permitidos = ESTANDAR | {"relevo.dominio", "relevo.aplicacion"}

    for archivo in modulos_de(APLICACION):
        externos = imports_de(archivo) - permitidos
        if externos:
            relativo = archivo.relative_to(RAIZ)
            infracciones.append(f"{relativo}: {', '.join(sorted(externos))}")

    assert not infracciones, (
        "La capa de aplicacion importa hacia afuera:\n  " + "\n  ".join(infracciones)
    )


def test_el_dominio_se_importa_sin_dependencias_instaladas() -> None:
    """Comprobacion complementaria: que los modulos carguen de verdad.

    El analisis estatico no ve un import escondido dentro de una funcion; este
    test si, porque ejecuta el modulo.
    """
    import importlib

    for archivo in modulos_de(DOMINIO):
        modulo = ".".join(archivo.relative_to(RAIZ / "src").with_suffix("").parts)
        importlib.import_module(modulo)


def test_los_puertos_son_interfaces_abstractas() -> None:
    """Un puerto que se puede instanciar no es un puerto: es una clase que
    alguien va a usar directamente, y ahi se acaba la intercambiabilidad."""
    import importlib
    import inspect
    from abc import ABC

    puertos = modulos_de(DOMINIO / "puertos")
    assert puertos, "No hay puertos definidos (bloque 2)"

    encontradas = 0
    for archivo in puertos:
        modulo = importlib.import_module(
            ".".join(archivo.relative_to(RAIZ / "src").with_suffix("").parts)
        )
        for _, clase in inspect.getmembers(modulo, inspect.isclass):
            if clase.__module__ != modulo.__name__ or not issubclass(clase, ABC):
                continue
            if not getattr(clase, "__abstractmethods__", None):
                continue
            encontradas += 1
            with pytest.raises(TypeError):
                clase()

    assert encontradas >= 5, "Se esperaban al menos cinco puertos abstractos"
