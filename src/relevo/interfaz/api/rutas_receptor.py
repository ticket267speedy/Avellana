"""La bandeja del hospital receptor y sus seis acciones.

El receptor deja de ser un DATO y pasa a ser un USUARIO. Eso es el dolor B4.

DOS REGLAS QUE ESTE ARCHIVO HACE CUMPLIR

1. **Aislamiento.** El receptor ve unicamente las referencias dirigidas a SU
   establecimiento. Lo que no le fue referido responde 404, nunca 403: un 403
   confirmaria que el paciente existe.

2. **Un clic por accion.** Ninguna de las seis es un formulario. Lo unico que
   el receptor aporta es un servicio de su propia cartera y, si falta algo, una
   seleccion de lista cerrada.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from relevo.aplicacion.acciones_receptor import (
    AccionReceptor,
    FaltaInformacion,
    ResultadoAccionReceptor,
)
from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.servicios.corte_etario import dias_para_corte
from relevo.interfaz.api.dependencias import (
    ContenedorDep,
    EstablecimientoDep,
    HoyDep,
    RolDep,
    exigir_ciclo,
    exigir_visibilidad,
)
from relevo.interfaz.api.esquemas import (
    AccionDisponibleSalida,
    AccionReceptorEntrada,
    FilaBandejaSalida,
    ResultadoAccionSalida,
)
from relevo.interfaz.api.roles import Rol

router = APIRouter(prefix="/api/receptor", tags=["receptor"])


@router.get("/bandeja", response_model=list[FilaBandejaSalida])
def bandeja(
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
    establecimiento: EstablecimientoDep,
) -> list[FilaBandejaSalida]:
    """Las referencias dirigidas a este establecimiento, y nada mas.

    Se ordena por dias para el corte etario y no por fecha de llegada: para el
    receptor, la referencia urgente no es la mas antigua sino la del
    adolescente que se queda sin ningun servicio dentro de tres semanas.
    """
    if rol is Rol.PROFESIONAL_RECEPTOR and not establecimiento:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Un profesional receptor tiene que declarar su establecimiento.",
        )

    filas: list[FilaBandejaSalida] = []
    for ciclo in contenedor.ciclos():
        if rol is Rol.PROFESIONAL_RECEPTOR:
            try:
                exigir_visibilidad(ciclo, rol, establecimiento)
            except HTTPException:
                continue
        # Un ciclo en preparacion todavia no ha salido del INSN: no le
        # corresponde al receptor verlo.
        if not ciclo.establecimiento_receptor or ciclo.estado.orden in (0, -1):
            continue

        paciente = contenedor.paciente(ciclo.paciente_id)
        dx = paciente.diagnostico_principal if paciente else None
        evaluacion = contenedor.evaluar_plazo(ciclo, hoy)

        filas.append(
            FilaBandejaSalida(
                paciente_id=ciclo.paciente_id,
                edad=paciente.edad(hoy) if paciente else 0,
                estado=ciclo.estado.value,
                etiqueta=ciclo.estado.etiqueta,
                dias_en_estado=ciclo.dias_en_estado_actual(hoy),
                situacion_plazo=evaluacion.situacion.value,
                dias_para_corte=(
                    dias_para_corte(ciclo.fecha_nacimiento, hoy)
                    if ciclo.fecha_nacimiento
                    else None
                ),
                diagnostico_principal=(
                    str(dx) if dx else "sin diagnostico registrado"
                ),
                acciones=[
                    AccionDisponibleSalida(codigo=a.value, etiqueta=a.etiqueta)
                    for a in contenedor.acciones_receptor.acciones_disponibles(ciclo)
                ],
            )
        )

    filas.sort(key=lambda f: (f.dias_para_corte is None, f.dias_para_corte or 0))
    return filas


@router.post("/{paciente_id}/{accion}", response_model=ResultadoAccionSalida)
def ejecutar_accion(
    paciente_id: str,
    accion: str,
    entrada: AccionReceptorEntrada,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
    establecimiento: EstablecimientoDep,
) -> ResultadoAccionSalida:
    """Las seis acciones, mas la variante de inasistencia. Un clic cada una."""
    ciclo = exigir_ciclo(contenedor, paciente_id)
    exigir_visibilidad(ciclo, rol, establecimiento)

    casos = contenedor.acciones_receptor

    try:
        if accion == AccionReceptor.CONFIRMAR_RECEPCION.value:
            resultado = casos.confirmar_recepcion(ciclo, hoy, entrada.quien)
        elif accion == AccionReceptor.INICIAR_EVALUACION.value:
            resultado = casos.iniciar_evaluacion(ciclo, hoy, entrada.quien)
        elif accion == AccionReceptor.SOLICITAR_INFORMACION.value:
            resultado = casos.solicitar_informacion(
                ciclo,
                _faltantes(entrada.faltantes),
                hoy,
                quien=entrada.quien,
                detalle=entrada.detalle,
            )
        elif accion == AccionReceptor.ACEPTAR_CON_SERVICIO.value:
            resultado = casos.aceptar_con_servicio(
                ciclo, entrada.servicio, hoy, entrada.quien
            )
        elif accion == AccionReceptor.PROGRAMAR_CITA.value:
            if entrada.fecha_cita is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Programar una cita exige la fecha de la cita.",
                )
            resultado = casos.programar_cita(
                ciclo, entrada.fecha_cita, hoy, entrada.quien
            )
        elif accion == AccionReceptor.CONFIRMAR_PRIMERA_ATENCION.value:
            resultado = casos.confirmar_primera_atencion(ciclo, hoy, entrada.quien)
        elif accion == "registrar_inasistencia":
            resultado = casos.registrar_inasistencia(ciclo, hoy, entrada.quien)
        else:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"'{accion}' no es una accion del receptor."
            )
    except TransicionInvalida as error:
        # 409 y no 422: la peticion esta bien formada, lo que pasa es que el
        # ciclo no esta donde el receptor cree. Suele significar que otra
        # persona ya lo movio, y el mensaje tiene que poder decirlo.
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    contenedor.guardar_ciclo(ciclo, actor=entrada.quien or "receptor")
    return _a_salida(resultado)


def _faltantes(codigos: list[str]) -> tuple[FaltaInformacion, ...]:
    """Traduce la lista CERRADA. Un codigo desconocido se rechaza, no se ignora.

    Ignorarlo dejaria una peticion de informacion vacia, que es un rechazo
    silencioso con otro nombre — exactamente lo que esta accion viene a evitar.
    """
    if not codigos:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Solicitar informacion exige decir que falta. Una peticion vacia es "
            "un rechazo silencioso con otro nombre.",
        )
    salida: list[FaltaInformacion] = []
    for codigo in codigos:
        try:
            salida.append(FaltaInformacion(codigo))
        except ValueError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"'{codigo}' no esta en la lista de informacion solicitable.",
            ) from None
    return tuple(salida)


def _a_salida(resultado: ResultadoAccionReceptor) -> ResultadoAccionSalida:
    avance = resultado.avance
    ciclo = resultado.ciclo
    return ResultadoAccionSalida(
        accion=resultado.accion.value,
        estado=ciclo.estado.value,
        etiqueta=ciclo.estado.etiqueta,
        responsable=resultado.responsable_actual.value,
        responsable_etiqueta=resultado.responsable_actual.etiqueta,
        cambio_de_turno=avance.cambio_de_turno if avance else False,
        devolvio_el_turno=resultado.devolvio_el_turno,
        gano_destino_asegurado=avance.gano_destino_asegurado if avance else False,
        mensaje=_mensaje(resultado),
    )


def _mensaje(resultado: ResultadoAccionReceptor) -> str:
    """Lo que se le dice al profesional despues del clic.

    Dice quien tiene el turno ahora, que es la unica pregunta que se hace
    despues de actuar: "¿ya no es cosa mia?".
    """
    if resultado.peticion is not None:
        return (
            f"Peticion registrada: {resultado.peticion.resumen()}. El turno "
            "vuelve al equipo del INSN y el plazo se reinicia."
        )
    if resultado.avance is not None and resultado.avance.gano_destino_asegurado:
        return (
            f"{resultado.ciclo.paciente_id} ya tiene destino asegurado: cumplir "
            "18 anios deja de ser un riesgo para este paciente."
        )
    return (
        f"{resultado.ciclo.estado.etiqueta}. Turno de "
        f"{resultado.responsable_actual.etiqueta}."
    )
