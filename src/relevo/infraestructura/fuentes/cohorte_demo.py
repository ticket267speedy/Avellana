"""La cohorte de la demostracion: dos casos con nombre y 40 de fondo.

TODO SINTETICO (regla 1). Ningun dato corresponde a una persona real.

POR QUE DOS CASOS CON NOMBRE Y NO UNO
El protagonista —Sindrome de Hunter— sale SIN destino identificado, y esa es la
demostracion: el sistema no puede inventar un servicio de adultos que no
existe, y en cambio produce la evidencia de que falta. Pero un unico caso sin
destino se lee como un fallo del software. El caso de contraste —asma
persistente, que si tiene servicio equivalente— es lo que convierte el vacio en
hallazgo: mismo sistema, dos pacientes, resultados distintos por motivos que
estan fuera del software.

El resto de la cohorte lo genera `CohorteSintetica`, que ya existia y ya
produce distribucion de IUT no trivial.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    FuenteConfirmacion,
)
from relevo.dominio.entidades.diagnostico import (
    CategoriaCCC,
    Cirugia,
    Contacto,
    Diagnostico,
    Dispositivo,
    Medicamento,
    ResultadoTRAQ,
    TipoContacto,
    TipoSeguro,
)
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.dominio.objetos_valor.codigo_cie10 import CodigoCIE10
from relevo.dominio.objetos_valor.estado_ciclo import (
    ETAPAS_DE_TRAMITE,
    EstadoCiclo,
    estado_desde_persistido,
)
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.infraestructura.fuentes.cohorte_sintetica import CohorteSintetica

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
RUTA_SEMILLA = RAIZ_PROYECTO / "config" / "semilla_demo.yaml"


def cargar_semilla(ruta: Path | None = None) -> dict[str, Any]:
    ruta = ruta or RUTA_SEMILLA
    if not ruta.exists():
        raise ConfiguracionIncompleta(
            f"No existe {ruta}. La cohorte de demo se define en archivo para "
            "que sea reproducible: misma semilla, misma cohorte."
        )
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ConfiguracionIncompleta(f"{ruta} no contiene un mapa YAML.")
    return datos


def _fecha(valor: Any) -> date | None:
    return date.fromisoformat(str(valor)) if valor else None


def _paciente_desde_semilla(bloque: dict[str, Any]) -> Paciente:
    """Construye un paciente con nombre a partir del YAML.

    `nombre_demo` NO se guarda en la entidad: `Paciente` no tiene campo de
    nombre a proposito, porque el sistema no necesita el nombre real para nada
    y guardarlo solo agrega riesgo. El nombre de la semilla vive en el YAML
    para que el equipo pueda referirse al caso al ensayar el pitch.
    """
    return Paciente(
        id=str(bloque["id"]),
        fecha_nacimiento=date.fromisoformat(str(bloque["fecha_nacimiento"])),
        sexo=str(bloque.get("sexo", "")),
        procedencia=str(bloque.get("procedencia", "")),
        tipo_seguro=TipoSeguro(str(bloque.get("tipo_seguro", "NINGUNO"))),
        diagnosticos=[
            Diagnostico(
                codigo=CodigoCIE10(str(dx["codigo"])),
                descripcion=str(dx.get("descripcion", "")),
                categoria=CategoriaCCC(str(dx.get("categoria", "otra"))),
                es_principal=bool(dx.get("principal", False)),
                es_raro=bool(dx.get("raro", False)),
            )
            for dx in bloque.get("diagnosticos", [])
        ],
        medicamentos=[
            Medicamento(
                nombre=str(m["nombre"]),
                dosis=m.get("dosis"),
                via=m.get("via"),
                frecuencia=m.get("frecuencia"),
                # Regla 8: la dosis solo entra si la semilla la declara
                # verificada. La de idursulfasa no lo esta, y por eso sale como
                # hueco en el Pasaporte.
                verificada_en_fuente=bool(m.get("verificada_en_fuente", False)),
            )
            for m in bloque.get("medicamentos", [])
        ],
        dispositivos=[
            Dispositivo(tipo=str(d["tipo"]), descripcion=str(d.get("descripcion", "")))
            for d in bloque.get("dispositivos", [])
        ],
        alergias=[str(a) for a in bloque.get("alergias", [])],
        cirugias=[
            Cirugia(
                nombre=str(c["nombre"]),
                fecha=_fecha(c.get("fecha")),
                institucion=str(c.get("institucion", "")),
            )
            for c in bloque.get("cirugias", [])
        ],
        contactos=[
            Contacto(
                nombre=str(c.get("nombre", "")),
                tipo=TipoContacto(str(c.get("tipo", "otro"))),
                telefono=(
                    Telefono(
                        numero=str(c["telefono"]),
                        verificado_en=_fecha(c.get("verificado_en")),
                        es_del_paciente=str(c.get("tipo")) == "paciente",
                    )
                    if c.get("telefono")
                    else None
                ),
                verificado_en=_fecha(c.get("verificado_en")),
            )
            for c in bloque.get("contactos", [])
        ],
        ultima_consulta=_fecha(bloque.get("ultima_consulta")),
        traq=(
            ResultadoTRAQ(
                puntaje=float(bloque["traq"]["puntaje"]),
                fecha=date.fromisoformat(str(bloque["traq"]["fecha"])),
            )
            if bloque.get("traq")
            else None
        ),
    )


def _ciclo_desde_semilla(
    paciente: Paciente, bloque: dict[str, Any], hoy: date
) -> CicloTransicion:
    """Un ciclo puesto directamente en el estado que la semilla pide.

    Se construye el historial recorriendo la linea de tramite en vez de
    saltarla: un ciclo de demo cuyo historial tenga un solo evento se ve
    sospechoso en la linea de tiempo, y la linea de tiempo es lo que se
    demuestra.
    """
    ciclo_yaml = bloque.get("ciclo", {})
    objetivo = estado_desde_persistido(str(ciclo_yaml.get("estado", "PREPARACION")))
    dias = int(ciclo_yaml.get("dias_en_estado", 0))

    ciclo = CicloTransicion(
        paciente_id=paciente.id,
        fecha_inicio=hoy - timedelta(days=dias + 60),
        fecha_nacimiento=paciente.fecha_nacimiento,
        establecimiento_receptor=str(ciclo_yaml.get("establecimiento_receptor", "")),
        servicio_asignado=str(ciclo_yaml.get("servicio_asignado", "")),
    )
    _recorrer_hasta(ciclo, objetivo, hoy - timedelta(days=dias), hoy)
    return ciclo


def _recorrer_hasta(
    ciclo: CicloTransicion, objetivo: EstadoCiclo, fecha_final: date, hoy: date
) -> None:
    """Avanza el ciclo por la linea de tramite hasta el estado pedido.

    Los estados intermedios se reparten en el tiempo entre la apertura y
    `fecha_final`, para que la linea de tiempo de la demo tenga fechas
    plausibles y no cinco eventos el mismo dia.
    """
    if objetivo is EstadoCiclo.PERDIDA_DE_SEGUIMIENTO:
        ciclo.avanzar(EstadoCiclo.REFERENCIA_ENVIADA, ciclo.fecha_inicio)
        ciclo.avanzar(EstadoCiclo.PERDIDA_DE_SEGUIMIENTO, fecha_final)
        return

    camino = [e for e in ETAPAS_DE_TRAMITE if 0 < e.orden <= objetivo.orden]
    if not camino:
        return

    inicio = ciclo.fecha_inicio
    tramo = max(1, (fecha_final - inicio).days // max(1, len(camino)))
    for i, estado in enumerate(camino, start=1):
        fecha = fecha_final if estado is objetivo else inicio + timedelta(days=tramo * i)
        fecha = min(max(fecha, ciclo.fecha_estado_actual), hoy)
        extras: dict[str, Any] = {}
        if estado is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA:
            extras["fuente_confirmacion"] = FuenteConfirmacion.CONFIRMACION_RECEPTOR
        ciclo.avanzar(estado, fecha, registrado_por="semilla de demo", **extras)


def construir_cohorte_demo(
    hoy: date,
    ruta_semilla: Path | None = None,
    ajustes: dict[str, Any] | None = None,
) -> tuple[list[Paciente], list[CicloTransicion]]:
    """Los dos casos con nombre mas la cohorte de fondo, con sus ciclos.

    Determinista: misma semilla, misma cohorte, hasta el ultimo digito del IUT.
    Es lo que hace que el ensayo del pitch sea reproducible.

    `ajustes` sobreescribe claves del YAML —numero de pacientes, semilla,
    reparto de estados— para que el CLI pueda pedir una cohorte distinta sin
    editar el archivo. Lo que NO se puede sobreescribir son los dos casos con
    nombre: el caso Hunter es el pitch, y que dependiera de un parametro seria
    poder ensayar una demo distinta de la que se presenta.
    """
    # Un ajuste en None significa "no lo cambies", no "ponlo a nada": el CLI no
    # siempre tiene valor para todas las claves, y dejar que un None borrara el
    # reparto de estados vaciaria la demo de ciclos sin que nadie lo notara.
    validos = {k: v for k, v in (ajustes or {}).items() if v is not None}
    semilla = {**cargar_semilla(ruta_semilla), **validos}
    total = int(semilla.get("pacientes", 42))

    pacientes: list[Paciente] = []
    ciclos: list[CicloTransicion] = []

    for clave in ("caso_protagonista", "caso_contraste"):
        bloque = semilla.get(clave)
        if not bloque:
            continue
        paciente = _paciente_desde_semilla(bloque)
        pacientes.append(paciente)
        ciclos.append(_ciclo_desde_semilla(paciente, bloque, hoy))

    # El fondo: lo genera el generador que ya existia. Se le pide `total -
    # len(pacientes)` para que el numero de la semilla sea el total real y no
    # haya que sumar de cabeza al leer el YAML.
    fondo = CohorteSintetica(
        cantidad=max(0, total - len(pacientes)),
        hoy=hoy,
        semilla=int(semilla.get("semilla_aleatoria", 20260816)),
    )
    pacientes.extend(fondo.leer_pacientes())

    ciclos.extend(
        _ciclos_de_fondo(
            [p for p in pacientes if p.id not in {c.paciente_id for c in ciclos}],
            semilla,
            hoy,
        )
    )
    return pacientes, ciclos


def _ciclos_de_fondo(
    pacientes: list[Paciente], semilla: dict[str, Any], hoy: date
) -> list[CicloTransicion]:
    """Reparte los ciclos abiertos entre los estados que pide la semilla.

    `ciclos_vencidos_forzados` crea ciclos con la fecha atrasada a proposito,
    para que `correr_noche` tenga siempre algo que avisar en la demo. Sin eso,
    la demostracion de las alertas dependeria de que dia sea hoy.
    """
    reparto: dict[str, int] = semilla.get("reparto_estados_ciclo", {}) or {}
    vencidos = int(semilla.get("ciclos_vencidos_forzados", 0))

    ciclos: list[CicloTransicion] = []
    indice = 0
    for nombre_estado, cuantos in reparto.items():
        estado = estado_desde_persistido(nombre_estado)
        for _ in range(int(cuantos)):
            if indice >= len(pacientes):
                break
            paciente = pacientes[indice]
            indice += 1
            # Los primeros `vencidos` se atrasan 200 dias: seguro fuera de
            # plazo en cualquier estado de la tabla.
            dias = 200 if len(ciclos) < vencidos else 10
            ciclo = CicloTransicion(
                paciente_id=paciente.id,
                fecha_inicio=hoy - timedelta(days=dias + 60),
                fecha_nacimiento=paciente.fecha_nacimiento,
                establecimiento_receptor="HOSPITAL NACIONAL  DOS DE MAYO",
            )
            _recorrer_hasta(ciclo, estado, hoy - timedelta(days=dias), hoy)
            ciclos.append(ciclo)
    return ciclos
