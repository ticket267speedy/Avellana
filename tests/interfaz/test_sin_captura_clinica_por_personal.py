"""BLOQUEANTE — al personal de salud no se le pide teclear ningun dato clinico.

═══════════════════════════════════════════════════════════════════════════════
CERO DOBLE DIGITACION — RESTRICCION DE PRODUCTO, NO PREFERENCIA
═══════════════════════════════════════════════════════════════════════════════

Esto es lo que mata a los proyectos de salud digital, y hay que blindarlo con
codigo y no con buenas intenciones.

**El INSN ya tiene SisGalenPlus. Nadie va a teclear los mismos datos dos
veces.** Si Relevo pide que el personal vuelva a escribir diagnostico,
tratamiento o filiacion, el sistema se abandona en la segunda semana por muy
bien construido que este. Este es el motivo real por el que el extractor y el
verificador existen.

    Relevo no pide datos. Pide decisiones.

Este test recorre los esquemas Pydantic de todos los endpoints bajo
`/api/insn/` y `/api/receptor/` y falla si alguno acepta un campo clinico de
escritura libre. Los unicos campos de escritura admitidos para personal son
veredictos de verificacion, selecciones de lista cerrada y notas
administrativas explicitamente marcadas como no clinicas.
"""

from __future__ import annotations

import inspect

import pytest
from fastapi.routing import APIRoute
from pydantic import BaseModel

from relevo.interfaz.api.esquemas import EntradaDePaciente, EntradaDePersonal
from relevo.interfaz.api.principal import ROUTERS

# Prefijos de los endpoints que usa el personal de salud.
PREFIJOS_DE_PERSONAL = ("/api/insn/", "/api/receptor/")

# Nombres de campo que, si aparecieran en un esquema de entrada de personal,
# significarian que le estamos pidiendo que teclee un dato clinico.
CAMPOS_CLINICOS_PROHIBIDOS = (
    "diagnostico",
    "diagnosticos",
    "cie10",
    "codigo_cie",
    "tratamiento",
    "medicamento",
    "medicamentos",
    "medicacion",
    "dosis",
    "posologia",
    "via_administracion",
    "frecuencia",
    "alergia",
    "alergias",
    "antecedente",
    "antecedentes",
    "resultado_laboratorio",
    "examen",
    "anamnesis",
    "epicrisis_texto",
    "evolucion",
    "sintoma",
    "sintomas",
    "hallazgo",
    "hallazgos",
    "peso",
    "talla",
    "presion_arterial",
    "observacion_clinica",
    "indicacion",
    "indicaciones",
)

# Campos de texto que SI puede escribir el personal, con su motivo. La lista es
# corta a proposito: cada entrada nueva aqui es una decision de producto, no un
# detalle de implementacion.
CAMPOS_ADMINISTRATIVOS_PERMITIDOS = {
    # Quien registra la accion. Es identidad, no dato del paciente.
    "quien",
    "registrado_por",
    # Contexto de gestion: con quien se hablo, por que via. El nombre lleva la
    # palabra "administrativa" a proposito — un campo llamado `nota` a secas
    # acabaria recibiendo diagnosticos.
    "nota_administrativa",
    # La decision del profesional sobre su propio proceso de conciliacion
    # ("se confirmo con la madre por telefono"), no un dato clinico.
    "nota",
    # Precisa QUE DOCUMENTO falta. Complementa la lista cerrada `faltantes`;
    # nunca es el portador del dato clinico.
    "detalle",
    # Seleccion de la cartera de servicios del establecimiento receptor.
    "servicio",
    # Selecciones de lista cerrada: se validan contra un enum del dominio.
    "estado",
    "motivo",
    "faltantes",
    "fuente_confirmacion",
    "motivo_reingreso",
    "fecha_cita",
}


def _rutas_de_la_api() -> list[APIRoute]:
    """Todos los endpoints, leidos de los routers y no de `app.routes`.

    Segun la version, FastAPI deja las rutas incluidas planas en `app.routes` o
    las envuelve en un objeto interno. Recorrer los routers —que son la fuente
    de verdad de lo que la aplicacion monta— evita que este test bloqueante se
    rompa al actualizar una dependencia, y un test que se rompe solo se acaba
    borrando.
    """
    return [r for router in ROUTERS for r in router.routes if isinstance(r, APIRoute)]


def _esquemas_de_entrada(prefijos: tuple[str, ...]) -> list[tuple[str, type[BaseModel]]]:
    """(ruta, modelo) de cada cuerpo que aceptan esos endpoints."""
    encontrados: list[tuple[str, type[BaseModel]]] = []
    for ruta in _rutas_de_la_api():
        if not any(ruta.path.startswith(p) for p in prefijos):
            continue
        for parametro in inspect.signature(ruta.endpoint).parameters.values():
            anotacion = parametro.annotation
            if inspect.isclass(anotacion) and issubclass(anotacion, BaseModel):
                encontrados.append((ruta.path, anotacion))
    return encontrados


# ═══════════════════════════════════════════════════════════════════════════
# La regla
# ═══════════════════════════════════════════════════════════════════════════


def test_hay_endpoints_de_personal_que_verificar() -> None:
    """Un test que pasa porque no encontro nada no verifica nada."""
    rutas = [
        r.path
        for r in _rutas_de_la_api()
        if any(r.path.startswith(p) for p in PREFIJOS_DE_PERSONAL)
    ]
    assert len(rutas) >= 3, f"solo se encontraron {rutas}"


@pytest.mark.bloqueante
def test_ningun_endpoint_de_personal_acepta_un_campo_clinico_libre() -> None:
    """El INSN ya tiene SisGalenPlus. Nadie teclea lo mismo dos veces."""
    infracciones: list[str] = []

    for ruta, modelo in _esquemas_de_entrada(PREFIJOS_DE_PERSONAL):
        for nombre in modelo.model_fields:
            minuscula = nombre.lower()
            if any(p in minuscula for p in CAMPOS_CLINICOS_PROHIBIDOS):
                infracciones.append(f"{ruta} · {modelo.__name__}.{nombre}")

    assert not infracciones, (
        "Endpoints de personal de salud que piden un dato clinico tecleado:\n  "
        + "\n  ".join(infracciones)
        + "\n\nEl dato clinico entra por el extractor con verificacion y firma, "
        "por el sistema del hospital, o por el propio paciente. Nunca por el "
        "teclado del personal de salud."
    )


@pytest.mark.bloqueante
def test_todo_campo_de_texto_del_personal_esta_en_la_lista_permitida() -> None:
    """La otra mitad de la regla, y la que de verdad la sostiene.

    El test de arriba prohibe una lista de nombres; este exige que TODO campo
    de entrada del personal este explicitamente permitido. Sin el, bastaria
    inventar un nombre nuevo —`comentario_del_medico`— para colar un campo
    clinico sin que ninguna prohibicion se activara.
    """
    infracciones: list[str] = []

    for ruta, modelo in _esquemas_de_entrada(PREFIJOS_DE_PERSONAL):
        for nombre in modelo.model_fields:
            if nombre not in CAMPOS_ADMINISTRATIVOS_PERMITIDOS:
                infracciones.append(f"{ruta} · {modelo.__name__}.{nombre}")

    assert not infracciones, (
        "Campos de entrada de personal que nadie declaro como administrativos:\n  "
        + "\n  ".join(infracciones)
        + "\n\nSi el campo es legitimo, anadirlo a CAMPOS_ADMINISTRATIVOS_"
        "PERMITIDOS con su motivo. Cada entrada de esa lista es una decision de "
        "producto, no un detalle de implementacion."
    )


@pytest.mark.bloqueante
def test_los_esquemas_de_personal_rechazan_campos_extra() -> None:
    """Sin `extra="forbid"`, un cliente podria enviar {"diagnostico": "..."} y
    Pydantic lo descartaria en silencio.

    Un campo clinico que llega y se ignora es un campo clinico que alguien creyo
    haber guardado.
    """
    for ruta, modelo in _esquemas_de_entrada(PREFIJOS_DE_PERSONAL):
        assert modelo.model_config.get("extra") == "forbid", (
            f"{ruta} · {modelo.__name__} acepta campos extra en silencio."
        )


def test_el_marcador_de_entrada_de_personal_se_usa_de_verdad() -> None:
    """Heredar de `EntradaDePersonal` es declarar que eso lo teclea un
    profesional. Si nadie heredara, el marcador seria decorativo."""
    modelos = {m for _, m in _esquemas_de_entrada(PREFIJOS_DE_PERSONAL)}
    marcados = [m for m in modelos if issubclass(m, EntradaDePersonal)]
    assert len(marcados) == len(modelos), (
        "Hay esquemas de personal que no heredan de EntradaDePersonal: "
        f"{sorted(m.__name__ for m in modelos - set(marcados))}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# La contraparte: el paciente SI puede escribir sobre si mismo
# ═══════════════════════════════════════════════════════════════════════════


def test_el_paciente_si_puede_declarar_su_propia_medicacion() -> None:
    """No es doble digitacion: ese dato no lo tenia nadie mas.

    Es la tercera de las tres puertas legitimas, y su valor esta justamente en
    no haberlo normalizado. Nunca sobrescribe el Pasaporte.
    """
    from relevo.interfaz.api.esquemas import MedicacionDeclaradaEntrada

    assert issubclass(MedicacionDeclaradaEntrada, EntradaDePaciente)
    assert "dosis" in MedicacionDeclaradaEntrada.model_fields
