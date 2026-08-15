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


# ═══════════════════════════════════════════════════════════════════════════
# La regla que faltaba: la fuga hacia AFUERA del hexagono
#
# Los tests de arriba vigilan que nada de adentro mire hacia afuera. Nadie
# vigilaba lo contrario: que la interfaz salte por encima de la aplicacion y
# hable directamente con los adaptadores.
#
# La regla se estaba rompiendo justo en la direccion que el test no miraba.
# ═══════════════════════════════════════════════════════════════════════════

INTERFAZ = RAIZ / "src" / "relevo" / "interfaz"

# Archivos autorizados a nombrar implementaciones concretas.
#
# `arranque.py` es la composicion de dependencias: por definicion las conoce
# todas, ese es su trabajo.
#
# Los CLI cumplen el MISMO papel para la linea de comandos: son puntos de
# entrada que arman lo que necesitan y arrancan. La excepcion se limita a
# `interfaz/cli/` y no se extiende a las pantallas, que es donde la fuga hacia
# afuera hace dano de verdad — una pantalla que conoce adaptadores es una
# pantalla que no se puede sustituir sin reescribir la orquestacion.
#
# Si un CLI crece hasta tener logica propia, esa logica va a un caso de uso.
# La excepcion cubre el cableado, no la orquestacion.
ARRANQUE_PERMITIDO = ("relevo/interfaz/arranque.py",)
CARPETAS_DE_COMPOSICION = ("relevo/interfaz/cli/",)

# Servicios de dominio que la interfaz no debe instanciar. Construir una
# `CalculadoraIUT` desde una pantalla es hacer de capa de aplicacion sin serlo:
# la pantalla pasa a saber COMO se prioriza en vez de QUE pedir.
SERVICIOS_DE_DOMINIO = (
    "CalculadoraIUT",
    "ClasificadorCohorte",
    "MaquinaCiclo",
    "VerificadorExtraccion",
)


def _archivos_de_interfaz() -> list[Path]:
    """Las pantallas. Excluye los puntos de composicion."""
    salida: list[Path] = []
    for p in modulos_de(INTERFAZ):
        ruta = p.as_posix()
        if ruta.endswith(ARRANQUE_PERMITIDO):
            continue
        if any(carpeta in ruta for carpeta in CARPETAS_DE_COMPOSICION):
            continue
        salida.append(p)
    return salida


@pytest.mark.bloqueante
def test_la_interfaz_no_importa_infraestructura_directamente() -> None:
    """La interfaz habla con casos de uso, no con adaptadores.

    Si la pantalla sabe que hay que instanciar `CohorteSintetica` y cargar un
    YAML, entonces cambiar Streamlit por FastAPI obliga a reescribir la
    orquestacion entera — y la frase del pitch, "solo se cambia el adaptador",
    deja de ser cierta.
    """
    infracciones: list[str] = []
    for archivo in _archivos_de_interfaz():
        for paquete in imports_de(archivo):
            if paquete == "relevo.infraestructura":
                infracciones.append(str(archivo.relative_to(RAIZ)))
                break

    assert not infracciones, (
        f"{len(infracciones)} archivos de la interfaz importan infraestructura "
        "directamente:\n  " + "\n  ".join(sorted(infracciones))
        + "\n\nLa interfaz sabe COMO se hace en vez de QUE pedir. "
        "Mover la orquestacion a un caso de uso en aplicacion/ y dejar la "
        "composicion de dependencias en interfaz/arranque.py."
    )


@pytest.mark.bloqueante
def test_la_interfaz_no_instancia_servicios_de_dominio() -> None:
    """Instanciar un servicio de dominio desde la pantalla es saltarse la capa
    de aplicacion, que es precisamente la que deberia orquestarlo."""
    infracciones: list[str] = []
    for archivo in _archivos_de_interfaz():
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.ImportFrom) or not nodo.module:
                continue
            if not nodo.module.startswith("relevo.dominio.servicios"):
                continue
            traidos = [a.name for a in nodo.names if a.name in SERVICIOS_DE_DOMINIO]
            if traidos:
                infracciones.append(
                    f"{archivo.relative_to(RAIZ)}: {', '.join(sorted(traidos))}"
                )

    assert not infracciones, (
        f"{len(infracciones)} archivos de la interfaz instancian servicios de "
        "dominio:\n  " + "\n  ".join(sorted(infracciones))
        + "\n\nEsos servicios los orquesta un caso de uso, no una pantalla."
    )


def test_la_aplicacion_no_es_vestigial() -> None:
    """La orquestacion vive en `aplicacion/`, no en el adaptador de entrada.

    No mide calidad: mide donde esta el peso. Una interfaz mucho mas grande que
    la capa de aplicacion significa que se la comio, y entonces la logica no se
    puede probar sin levantar un navegador.

    El umbral de 3:1 es generoso a proposito — una interfaz siempre tiene mas
    lineas por el maquetado. Lo que se vigila es el orden de magnitud.
    TODO: bajar a 2:1 cuando A2 este terminado.
    """
    def lineas(carpeta: Path) -> int:
        return sum(
            len(p.read_text(encoding="utf-8").splitlines()) for p in modulos_de(carpeta)
        )

    lineas_interfaz = lineas(INTERFAZ)
    lineas_aplicacion = lineas(APLICACION)
    assert lineas_aplicacion > 0, "No hay capa de aplicacion"

    razon = lineas_interfaz / lineas_aplicacion
    assert razon <= 3.0, (
        f"La interfaz tiene {lineas_interfaz} lineas y la aplicacion "
        f"{lineas_aplicacion}: razon {razon:.1f}:1.\n"
        "La orquestacion se mudo al adaptador de entrada. Extraer casos de uso "
        "a aplicacion/ hasta bajar de 3:1."
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
