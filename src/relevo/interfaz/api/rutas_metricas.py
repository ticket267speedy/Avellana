"""Las dos cifras que abren el radar.

1. **Corte etario** — la metrica estrella de fracaso. Cuantos se quedan sin
   ningun servicio al cumplir 18. Cualquier otra cifra del sistema mide
   actividad; esta mide el dano que el proyecto existe para evitar.

2. **Cobertura de destinos** — el entregable de B1. Con el directorio vacio
   devuelve "100 % sin destino identificado", y ESA CIFRA NO SE ESCONDE: es la
   evidencia de brecha de oferta que el INSN puede llevar a una mesa de
   gestion. El sistema no inventa destinos; mide su ausencia.
"""

from __future__ import annotations

from fastapi import APIRouter

from relevo.dominio.entidades.destino import MotivoSinDestino, SinDestinoIdentificado
from relevo.interfaz.api.dependencias import ContenedorDep, HoyDep, RolDep
from relevo.interfaz.api.esquemas import (
    CoberturaDestinosSalida,
    CorteEtarioSalida,
    FilaRiesgoSalida,
    FracasoSalida,
)

router = APIRouter(prefix="/api/metricas", tags=["metricas"])


@router.get("/corte-etario", response_model=CorteEtarioSalida)
def corte_etario(
    contenedor: ContenedorDep, hoy: HoyDep, rol: RolDep
) -> CorteEtarioSalida:
    """Cumplir 18 no es el fracaso. Cumplir 18 SIN DESTINO ASEGURADO si lo es.

    La primera cita en el hospital de adultos ocurre, por definicion, despues
    de los 18. Lo que el corte del INSN impide es la atencion pediatrica, no la
    continuidad del tramite.

    Es agregada, asi que la ve tambien el ADMINISTRADOR: no hay dato clinico en
    un recuento.
    """
    del rol
    ciclos = contenedor.ciclos()
    resultado = contenedor.evaluar_corte.ejecutar(ciclos, hoy)

    return CorteEtarioSalida(
        en_riesgo_90_dias=resultado.metrica.en_riesgo_90_dias,
        ya_cumplieron_sin_destino=resultado.metrica.ya_cumplieron_sin_destino,
        total_cohorte=resultado.metrica.total_cohorte,
        horizonte_dias=resultado.horizonte_dias,
        titular=resultado.titular,
        en_riesgo=[
            FilaRiesgoSalida(
                paciente_id=f.paciente_id,
                dias_para_corte=f.dias_para_corte,
                estado=f.estado,
                responsable=f.responsable,
                es_urgente=f.es_urgente,
            )
            for f in resultado.en_riesgo
        ],
        consumados=[
            FracasoSalida(
                id_paciente=c.id_paciente,
                fecha_cumpleanios=c.fecha_cumpleanios,
                estado_al_cumplir=c.estado_al_cumplir.etiqueta,
                dias_en_ese_estado=c.dias_en_ese_estado,
            )
            for c in resultado.consumados
        ],
        # Un denominador que excluye casos en silencio produce una metrica que
        # mejora sola cuando empeoran los datos. Si hay ciclos sin fecha de
        # nacimiento, la interfaz tiene que poder decir cuantos.
        sin_fecha_de_nacimiento=list(
            contenedor.evaluar_corte.sin_fecha_de_nacimiento(list(ciclos))
        ),
    )


@router.get("/cobertura-destinos", response_model=CoberturaDestinosSalida)
def cobertura_destinos(
    contenedor: ContenedorDep, hoy: HoyDep, rol: RolDep
) -> CoberturaDestinosSalida:
    """Cuantos pacientes salen sin destino identificado, y por que motivo.

    Este numero hoy no lo tiene nadie. No mide que tan bueno es el software:
    mide un hueco del sistema de salud peruano que nadie habia cuantificado, y
    por eso vale como entregable aunque el directorio este vacio.
    """
    del rol, hoy
    directorio = contenedor.directorio_destinos
    por_motivo: dict[str, int] = {}
    con_destino = 0
    brecha = 0
    total = 0

    for paciente in contenedor.pacientes():
        dx = paciente.diagnostico_principal
        if dx is None:
            continue
        total += 1
        resultado = directorio.buscar(dx.codigo.valor, paciente.procedencia)
        if isinstance(resultado, SinDestinoIdentificado):
            clave = resultado.motivo.name
            por_motivo[clave] = por_motivo.get(clave, 0) + 1
            if resultado.requiere_escalamiento:
                brecha += 1
        else:
            con_destino += 1

    sin_destino = total - con_destino
    return CoberturaDestinosSalida(
        total_evaluados=total,
        con_destino=con_destino,
        sin_destino=sin_destino,
        porcentaje_sin_destino=round(100 * sin_destino / total, 1) if total else 0.0,
        por_motivo=por_motivo or {m.name: 0 for m in MotivoSinDestino},
        brecha_de_oferta=brecha,
        resumen_directorio=contenedor.resumen_directorio(),
    )
