"""La aplicacion FastAPI. Un router por area, ninguno con logica de negocio.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTE ARCHIVO ES LA DEMOSTRACION DEL PITCH
═══════════════════════════════════════════════════════════════════════════════

Anadir `interfaz/api/` completo —siete areas, veinte endpoints, un frontend
detras— sin tocar UNA SOLA LINEA de `dominio/` ni de `aplicacion/` **es** la
demostracion en vivo de la promesa: *"el nucleo no cambia, solo se cambia el
adaptador de entrada"*.

No es una afirmacion que haya que creerse: esta en el historial de git. El diff
del nucleo entre el checkpoint C3 y el C4 es de cero lineas.

Y hay dos adaptadores de entrada distintos sobre el mismo nucleo, la misma base
de datos y la misma auditoria: esta API es el producto, y `interfaz/web/app.py`
(Streamlit) es la consola tecnica. Esa es la diapositiva de arquitectura — no
hay que explicarla, se muestra.

Se sirven tambien los estaticos del frontend, para que el despliegue sea un
solo proceso:

    uvicorn relevo.interfaz.api.principal:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from relevo.interfaz.api import (
    rutas_aprendizaje,
    rutas_apoderado,
    rutas_conciliacion,
    rutas_demo,
    rutas_insn,
    rutas_metricas,
    rutas_pacientes,
    rutas_receptor,
)

# `src/relevo/interfaz/api/principal.py` -> `src/relevo/interfaz/web/`
WEB = Path(__file__).resolve().parents[1] / "web"

DESCRIPCION = """
**Relevo** — acompanamiento de la transicion pediatrico-adulto, INSN San Borja.

Todos los datos de esta demostracion son **sinteticos**. Ninguno corresponde a
una persona real.

**Modelo de despliegue: on-premise, dentro de la red del hospital.** No es
"local en una laptop": la laptop es la maqueta del modelo, no el modelo. El
dato clinico no sale de la red del INSN en ningun momento, y no hay ningun
proveedor externo de modelos de lenguaje — Ollama corre en la misma maquina y
se le habla por HTTP plano a `localhost:11434`.

**El IUT no prioriza pacientes: ordena la cola de trabajo del equipo de
transicion.** No decide quien se atiende primero en un hospital; decide a quien
llama primero la trabajadora social. Cada puntaje muestra sus factores con su
peso, y cualquier persona puede reordenar la cola a mano.
"""

app = FastAPI(
    title="Relevo — API",
    version="0.2.0",
    description=DESCRIPCION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Los routers, en una constante y no en linea, para que los tests puedan
# recorrerlos sin depender de como los guarde FastAPI por dentro: segun la
# version, `app.routes` los deja planos o los envuelve, y un test de
# arquitectura que se rompe al actualizar una dependencia se acaba borrando.
ROUTERS = (
    rutas_pacientes.router,
    rutas_aprendizaje.router,
    rutas_conciliacion.router,
    rutas_insn.router,
    rutas_receptor.router,
    rutas_apoderado.router,
    rutas_metricas.router,
    rutas_demo.router,
)

for _router in ROUTERS:
    app.include_router(_router)


@app.get("/api/salud", tags=["sistema"])
def salud() -> dict[str, str | bool]:
    """Comprobacion de vida. No toca la base ni el modelo.

    Deliberadamente tonta: si consultara SQLite o Ollama, un fallo de
    cualquiera de los dos haria parecer caida la aplicacion entera.
    """
    return {
        "estado": "ok",
        "servicio": "relevo",
        "datos_sinteticos": True,
        "despliegue": "on-premise (red del hospital)",
    }


if (WEB / "index.html").exists() and (WEB / "estatico").is_dir():
    # Los estaticos van despues de los routers: FastAPI resuelve por orden de
    # registro, y un `StaticFiles` montado en la raiz antes que las rutas se
    # comeria `/api/...`.
    app.mount(
        "/estatico",
        StaticFiles(directory=WEB / "estatico"),
        name="estatico",
    )

    @app.get("/", include_in_schema=False)
    def indice() -> FileResponse:
        """El unico HTML. El enrutado del cliente es por hash (`#/...`).

        Router por hash y no por rutas del servidor a proposito: asi no hace
        falta una regla de reescritura para que recargar `#/insn/radar`
        funcione, y el despliegue sigue siendo un solo proceso sin
        configuracion.
        """
        return FileResponse(WEB / "index.html")
