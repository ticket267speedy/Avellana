"""Agregado de dominio <-> documento JSON.

`RepositorioPacientesSQLite` recibe `a_documento` y `desde_documento` por
inyeccion: no conoce la forma del agregado. Este archivo es esa forma.

═══════════════════════════════════════════════════════════════════════════════
LA REGLA DE ESTE ARCHIVO
═══════════════════════════════════════════════════════════════════════════════

    Si un campo no entra aqui, se pierde al reiniciar — y se pierde en
    silencio, que es lo peor.

Por eso el test de ida y vuelta con 50 semillas no es opcional: es lo unico que
garantiza que cerrar la aplicacion no borre informacion. Una serializacion
incompleta no lanza ninguna excepcion; simplemente devuelve un paciente con un
diagnostico menos.

Los ciclos se leen con `estado_desde_persistido`, que acepta tanto el modelo de
nueve estados como los seis originales. Nada se borra para simplificar la
migracion: borrar filas seria perder el historico que el piloto viene a medir.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from relevo.dominio.entidades.acceso_apoderado import (
    AccesoApoderado,
    ConsentimientoExplicito,
)
from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EventoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.entidades.conciliacion import (
    CasoDeConciliacion,
    Discrepancia,
    EstadoConciliacion,
)
from relevo.dominio.entidades.diagnostico import (
    CategoriaCCC,
    Cirugia,
    Contacto,
    Diagnostico,
    Dispositivo,
    HistoriaTextoLibre,
    Medicamento,
    ResultadoTRAQ,
    TipoContacto,
    TipoSeguro,
)
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.progreso_aprendizaje import (
    AvanceHabilidad,
    ProgresoAprendizaje,
)
from relevo.dominio.objetos_valor.codigo_cie10 import CodigoCIE10
from relevo.dominio.objetos_valor.estado_ciclo import estado_desde_persistido
from relevo.dominio.objetos_valor.habilidad import EstadoHabilidad, Habilidad
from relevo.dominio.objetos_valor.origen_dato import TipoDiscrepancia
from relevo.dominio.objetos_valor.reingreso import MotivoReingreso, Reingreso
from relevo.dominio.objetos_valor.telefono import Telefono

# ─────────────────────────────────────────────────────────────────────────────
# Ayudas
# ─────────────────────────────────────────────────────────────────────────────


def _f(valor: date | None) -> str | None:
    return valor.isoformat() if valor is not None else None


def _d(valor: Any) -> date | None:
    """Fecha desde ISO. None se conserva como None, nunca como epoch.

    Una fecha ausente y el 1 de enero de 1970 son cosas distintas, y confundir
    las dos produce un paciente de 56 anios en la cohorte.
    """
    if valor in (None, ""):
        return None
    return date.fromisoformat(str(valor))


def _d_exigida(valor: Any, campo: str) -> date:
    fecha = _d(valor)
    if fecha is None:
        raise ValueError(
            f"El documento no trae '{campo}', que es obligatorio. Reconstruir "
            "un agregado a partir de un documento incompleto produce datos "
            "plausibles y falsos."
        )
    return fecha


# ─────────────────────────────────────────────────────────────────────────────
# Paciente
# ─────────────────────────────────────────────────────────────────────────────


def paciente_a_documento(p: Paciente) -> dict[str, Any]:
    """Serializa el agregado completo. Sin perder nada."""
    return {
        "id": p.id,
        "fecha_nacimiento": p.fecha_nacimiento.isoformat(),
        "sexo": p.sexo,
        "procedencia": p.procedencia,
        "tipo_seguro": p.tipo_seguro.value,
        "diagnosticos": [
            {
                "codigo": dx.codigo.valor,
                "descripcion": dx.descripcion,
                "categoria": dx.categoria.value,
                "es_principal": dx.es_principal,
                "es_raro": dx.es_raro,
                "fecha_diagnostico": _f(dx.fecha_diagnostico),
                "activo": dx.activo,
            }
            for dx in p.diagnosticos
        ],
        "medicamentos": [
            {
                "nombre": m.nombre,
                "dosis": m.dosis,
                "via": m.via,
                "frecuencia": m.frecuencia,
                "verificada_en_fuente": m.verificada_en_fuente,
            }
            for m in p.medicamentos
        ],
        "dispositivos": [
            {
                "tipo": d.tipo,
                "descripcion": d.descripcion,
                "fecha_colocacion": _f(d.fecha_colocacion),
            }
            for d in p.dispositivos
        ],
        "alergias": list(p.alergias),
        "cirugias": [
            {"nombre": c.nombre, "fecha": _f(c.fecha), "institucion": c.institucion}
            for c in p.cirugias
        ],
        "contactos": [
            {
                "nombre": c.nombre,
                "tipo": c.tipo.value,
                "telefono": (
                    {
                        "numero": c.telefono.numero,
                        "verificado_en": _f(c.telefono.verificado_en),
                        "es_del_paciente": c.telefono.es_del_paciente,
                    }
                    if c.telefono is not None
                    else None
                ),
                "correo": c.correo,
                "verificado_en": _f(c.verificado_en),
            }
            for c in p.contactos
        ],
        "ultima_consulta": _f(p.ultima_consulta),
        "traq": (
            {"puntaje": p.traq.puntaje, "fecha": p.traq.fecha.isoformat()}
            if p.traq is not None
            else None
        ),
        "texto_libre": dict(p.texto_libre.secciones),
    }


def paciente_desde_documento(d: dict[str, Any]) -> Paciente:
    """Reconstruye. Inverso exacto del anterior."""
    return Paciente(
        id=str(d["id"]),
        fecha_nacimiento=_d_exigida(d.get("fecha_nacimiento"), "fecha_nacimiento"),
        sexo=str(d.get("sexo", "")),
        procedencia=str(d.get("procedencia", "")),
        tipo_seguro=TipoSeguro(d.get("tipo_seguro", TipoSeguro.NINGUNO.value)),
        diagnosticos=[
            Diagnostico(
                codigo=CodigoCIE10(dx["codigo"]),
                descripcion=dx.get("descripcion", ""),
                categoria=CategoriaCCC(dx.get("categoria", CategoriaCCC.OTRA.value)),
                es_principal=bool(dx.get("es_principal", False)),
                es_raro=bool(dx.get("es_raro", False)),
                fecha_diagnostico=_d(dx.get("fecha_diagnostico")),
                activo=bool(dx.get("activo", True)),
            )
            for dx in d.get("diagnosticos", [])
        ],
        medicamentos=[
            Medicamento(
                nombre=m["nombre"],
                dosis=m.get("dosis"),
                via=m.get("via"),
                frecuencia=m.get("frecuencia"),
                verificada_en_fuente=bool(m.get("verificada_en_fuente", False)),
            )
            for m in d.get("medicamentos", [])
        ],
        dispositivos=[
            Dispositivo(
                tipo=x["tipo"],
                descripcion=x.get("descripcion", ""),
                fecha_colocacion=_d(x.get("fecha_colocacion")),
            )
            for x in d.get("dispositivos", [])
        ],
        alergias=list(d.get("alergias", [])),
        cirugias=[
            Cirugia(
                nombre=c["nombre"],
                fecha=_d(c.get("fecha")),
                institucion=c.get("institucion", ""),
            )
            for c in d.get("cirugias", [])
        ],
        contactos=[
            Contacto(
                nombre=c.get("nombre", ""),
                tipo=TipoContacto(c.get("tipo", TipoContacto.OTRO.value)),
                telefono=(
                    Telefono(
                        numero=c["telefono"]["numero"],
                        verificado_en=_d(c["telefono"].get("verificado_en")),
                        es_del_paciente=bool(
                            c["telefono"].get("es_del_paciente", False)
                        ),
                    )
                    if c.get("telefono")
                    else None
                ),
                correo=c.get("correo"),
                verificado_en=_d(c.get("verificado_en")),
            )
            for c in d.get("contactos", [])
        ],
        ultima_consulta=_d(d.get("ultima_consulta")),
        traq=(
            ResultadoTRAQ(
                puntaje=float(d["traq"]["puntaje"]),
                fecha=_d_exigida(d["traq"]["fecha"], "traq.fecha"),
            )
            if d.get("traq")
            else None
        ),
        texto_libre=HistoriaTextoLibre(secciones=dict(d.get("texto_libre", {}))),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ciclo de transicion
# ─────────────────────────────────────────────────────────────────────────────


def ciclo_a_documento(c: CicloTransicion) -> dict[str, Any]:
    return {
        "paciente_id": c.paciente_id,
        "fecha_inicio": c.fecha_inicio.isoformat(),
        "fecha_nacimiento": _f(c.fecha_nacimiento),
        "destino_propuesto": c.destino_propuesto,
        "establecimiento_receptor": c.establecimiento_receptor,
        "servicio_asignado": c.servicio_asignado,
        "fecha_cita": _f(c.fecha_cita),
        "historial": [
            {
                "estado": e.estado.value,
                "fecha": e.fecha.isoformat(),
                "registrado_por": e.registrado_por,
                "fuente_confirmacion": (
                    e.fuente_confirmacion.value if e.fuente_confirmacion else None
                ),
                "motivo_reingreso": (
                    e.motivo_reingreso.value if e.motivo_reingreso else None
                ),
                "nota": e.nota,
            }
            for e in c.historial
        ],
        "reingresos": [
            {
                "motivo": r.motivo.value,
                "fecha": r.fecha.isoformat(),
                "registrado_por": r.registrado_por,
                "reclasificado_a": (
                    r.reclasificado_a.value if r.reclasificado_a else None
                ),
                "nota_administrativa": r.nota_administrativa,
            }
            for r in c.reingresos
        ],
    }


def ciclo_desde_documento(d: dict[str, Any]) -> CicloTransicion:
    """Reconstruye un ciclo, traduciendo estados del modelo viejo si hace falta.

    El historial se asigna directamente en vez de reproducirse con `avanzar()`:
    un ciclo persistido bajo el modelo de seis estados contiene transiciones
    que el grafo de nueve no permite, y revalidarlas al leer haria imposible
    abrir la base antigua. La validacion se aplica a lo que se escribe de aqui
    en adelante, no a lo que ya ocurrio.
    """
    historial = [
        EventoCiclo(
            estado=estado_desde_persistido(e["estado"]),
            fecha=_d_exigida(e.get("fecha"), "historial.fecha"),
            registrado_por=e.get("registrado_por", ""),
            fuente_confirmacion=(
                FuenteConfirmacion(e["fuente_confirmacion"])
                if e.get("fuente_confirmacion")
                else None
            ),
            motivo_reingreso=(
                MotivoReingreso(e["motivo_reingreso"])
                if e.get("motivo_reingreso")
                else None
            ),
            nota=e.get("nota", ""),
        )
        for e in d.get("historial", [])
    ]

    return CicloTransicion(
        paciente_id=str(d["paciente_id"]),
        fecha_inicio=_d_exigida(d.get("fecha_inicio"), "fecha_inicio"),
        fecha_nacimiento=_d(d.get("fecha_nacimiento")),
        destino_propuesto=d.get("destino_propuesto", ""),
        establecimiento_receptor=d.get("establecimiento_receptor", ""),
        servicio_asignado=d.get("servicio_asignado", ""),
        fecha_cita=_d(d.get("fecha_cita")),
        historial=historial,
        reingresos=[
            Reingreso(
                motivo=MotivoReingreso(r["motivo"]),
                fecha=_d_exigida(r.get("fecha"), "reingresos.fecha"),
                registrado_por=r.get("registrado_por", ""),
                reclasificado_a=(
                    estado_desde_persistido(r["reclasificado_a"])
                    if r.get("reclasificado_a")
                    else None
                ),
                nota_administrativa=r.get("nota_administrativa", ""),
            )
            for r in d.get("reingresos", [])
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Progreso de aprendizaje
# ─────────────────────────────────────────────────────────────────────────────


def progreso_a_documento(p: ProgresoAprendizaje) -> dict[str, Any]:
    return {
        "paciente_id": p.paciente_id,
        "estados": {h.value: e.value for h, e in p.estados.items()},
        "historial": [
            {
                "habilidad": a.habilidad.value,
                "estado": a.estado.value,
                "fecha": a.fecha.isoformat(),
                "nota": a.nota,
            }
            for a in p.historial
        ],
        "lecciones_vistas": sorted(p.lecciones_vistas),
    }


def progreso_desde_documento(d: dict[str, Any]) -> ProgresoAprendizaje:
    return ProgresoAprendizaje(
        paciente_id=str(d["paciente_id"]),
        estados={
            Habilidad(h): EstadoHabilidad(e) for h, e in d.get("estados", {}).items()
        },
        historial=[
            AvanceHabilidad(
                habilidad=Habilidad(a["habilidad"]),
                estado=EstadoHabilidad(a["estado"]),
                fecha=_d_exigida(a.get("fecha"), "historial.fecha"),
                nota=a.get("nota", ""),
            )
            for a in d.get("historial", [])
        ],
        lecciones_vistas=set(d.get("lecciones_vistas", [])),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Conciliacion
# ─────────────────────────────────────────────────────────────────────────────


def conciliacion_a_documento(c: CasoDeConciliacion) -> dict[str, Any]:
    return {
        "paciente_id": c.paciente_id,
        "fecha_apertura": c.fecha_apertura.isoformat(),
        "estado": c.estado.value,
        "resuelto_por": c.resuelto_por,
        "fecha_resolucion": _f(c.fecha_resolucion),
        "nota_resolucion": c.nota_resolucion,
        "discrepancias": [
            {
                "tipo": d.tipo.value,
                "medicamento": d.medicamento,
                "valor_pasaporte": d.valor_pasaporte,
                "valor_declarado": d.valor_declarado,
            }
            for d in c.discrepancias
        ],
        "historial_estados": [
            [e.value, f.isoformat()] for e, f in c.historial_estados
        ],
    }


def conciliacion_desde_documento(d: dict[str, Any]) -> CasoDeConciliacion:
    return CasoDeConciliacion(
        paciente_id=str(d["paciente_id"]),
        fecha_apertura=_d_exigida(d.get("fecha_apertura"), "fecha_apertura"),
        discrepancias=tuple(
            Discrepancia(
                tipo=TipoDiscrepancia(x["tipo"]),
                medicamento=x["medicamento"],
                valor_pasaporte=x.get("valor_pasaporte"),
                valor_declarado=x.get("valor_declarado"),
            )
            for x in d.get("discrepancias", [])
        ),
        estado=EstadoConciliacion(d.get("estado", EstadoConciliacion.ABIERTO.value)),
        resuelto_por=d.get("resuelto_por", ""),
        fecha_resolucion=_d(d.get("fecha_resolucion")),
        nota_resolucion=d.get("nota_resolucion", ""),
        historial_estados=[
            (EstadoConciliacion(e), _d_exigida(f, "historial_estados"))
            for e, f in d.get("historial_estados", [])
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Acceso del apoderado
# ─────────────────────────────────────────────────────────────────────────────


def acceso_a_documento(a: AccesoApoderado) -> dict[str, Any]:
    """Ojo: NO se guarda ningun `tiene_acceso`.

    La base legal se calcula en cada consulta a partir de la fecha. Un booleano
    persistido seguiria valiendo True el dia despues del cumpleanos 18, y ese
    es exactamente el fallo que el modulo existe para hacer imposible.
    """
    return {
        "paciente_id": a.paciente_id,
        "fecha_nacimiento_paciente": a.fecha_nacimiento_paciente.isoformat(),
        "nombre_apoderado": a.nombre_apoderado,
        "parentesco": a.parentesco,
        "consentimiento": (
            {
                "otorgado_por_paciente": a.consentimiento.otorgado_por_paciente,
                "fecha": a.consentimiento.fecha.isoformat(),
                "alcance": a.consentimiento.alcance,
                "medio": a.consentimiento.medio,
            }
            if a.consentimiento is not None
            else None
        ),
        "revocado_en": _f(a.revocado_en),
        "historial": [[tipo, f.isoformat()] for tipo, f in a.historial],
    }


def acceso_desde_documento(d: dict[str, Any]) -> AccesoApoderado:
    consentimiento = d.get("consentimiento")
    return AccesoApoderado(
        paciente_id=str(d["paciente_id"]),
        fecha_nacimiento_paciente=_d_exigida(
            d.get("fecha_nacimiento_paciente"), "fecha_nacimiento_paciente"
        ),
        nombre_apoderado=d.get("nombre_apoderado", ""),
        parentesco=d.get("parentesco", ""),
        consentimiento=(
            ConsentimientoExplicito(
                otorgado_por_paciente=consentimiento["otorgado_por_paciente"],
                fecha=_d_exigida(consentimiento["fecha"], "consentimiento.fecha"),
                alcance=consentimiento.get("alcance", ""),
                medio=consentimiento.get("medio", ""),
            )
            if consentimiento
            else None
        ),
        revocado_en=_d(d.get("revocado_en")),
        historial=[
            (tipo, _d_exigida(f, "historial")) for tipo, f in d.get("historial", [])
        ],
    )


__all__ = [
    "acceso_a_documento",
    "acceso_desde_documento",
    "ciclo_a_documento",
    "ciclo_desde_documento",
    "conciliacion_a_documento",
    "conciliacion_desde_documento",
    "paciente_a_documento",
    "paciente_desde_documento",
    "progreso_a_documento",
    "progreso_desde_documento",
]
