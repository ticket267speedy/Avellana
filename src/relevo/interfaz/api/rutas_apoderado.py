"""La vista del apoderado. NO es una vista aparte: es la del paciente filtrada.

El apoderado usa los mismos endpoints del paciente. Lo unico propio es esto:
saber QUE puede ver hoy y por que — y ver el aviso de que su acceso caduca el
dia que el paciente cumpla 18.

El acceso se calcula en cada peticion a partir de la fecha. Nunca se guarda un
booleano: un `tiene_acceso` persistido seguiria valiendo True el dia despues
del cumpleanos, y ese es exactamente el fallo que el mecanismo existe para
hacer imposible.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from relevo.dominio.entidades.acceso_apoderado import AccesoApoderado
from relevo.interfaz.api.dependencias import (
    ContenedorDep,
    HoyDep,
    exigir_paciente,
)
from relevo.interfaz.api.esquemas import PermisosApoderadoSalida

router = APIRouter(prefix="/api/apoderado", tags=["apoderado"])


@router.get("/{paciente_id}/permisos", response_model=PermisosApoderadoSalida)
def permisos(
    paciente_id: str, contenedor: ContenedorDep, hoy: HoyDep
) -> PermisosApoderadoSalida:
    """Que puede ver este apoderado hoy, con que base legal y hasta cuando.

    Se devuelve incluso cuando NO hay acceso, con `puede_ver_*` en False y el
    aviso explicando quien puede reactivarlo. Devolver un 403 seco dejaria a la
    familia sin saber por que dejo de funcionar ni que hacer al respecto, que
    es justo el problema que la Leccion 6 viene a evitar.
    """
    paciente = exigir_paciente(contenedor, paciente_id)

    guardado = (
        contenedor.repo_acceso.obtener(paciente_id)
        if contenedor.repo_acceso is not None
        else None
    )
    acceso = (
        guardado
        if isinstance(guardado, AccesoApoderado)
        else AccesoApoderado(
            paciente_id=paciente_id,
            fecha_nacimiento_paciente=paciente.fecha_nacimiento,
            nombre_apoderado="Apoderado registrado",
        )
    )

    permisos = contenedor.acceso_apoderado.permisos(acceso, hoy)
    return PermisosApoderadoSalida(
        puede_ver_estado_del_ciclo=permisos.puede_ver_estado_del_ciclo,
        puede_ver_pasaporte=permisos.puede_ver_pasaporte,
        puede_ver_aprendizaje=permisos.puede_ver_aprendizaje,
        base_legal=permisos.base_legal.value,
        base_legal_etiqueta=permisos.base_legal.etiqueta,
        norma=permisos.norma,
        aviso=permisos.aviso,
        dias_para_el_corte=permisos.dias_para_el_corte,
    )


@router.post("/{paciente_id}/consentimiento", response_model=PermisosApoderadoSalida)
def otorgar_consentimiento(
    paciente_id: str,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    alcance: str = "estado del ciclo de transicion",
) -> PermisosApoderadoSalida:
    """El PACIENTE autoriza a su apoderado. Solo el puede.

    Se puede otorgar antes de los 18: deja el acceso preparado para el dia del
    corte, y es justamente lo que la Leccion 6 le propone hacer al adolescente.

    Queda fechado y asentado en la cadena de auditoria.
    """
    paciente = exigir_paciente(contenedor, paciente_id)
    if contenedor.repo_acceso is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El sistema arranco sin persistencia: el consentimiento no se "
            "puede registrar, y un consentimiento que no queda registrado no "
            "es un consentimiento.",
        )

    guardado = contenedor.repo_acceso.obtener(paciente_id)
    acceso = (
        guardado
        if isinstance(guardado, AccesoApoderado)
        else AccesoApoderado(
            paciente_id=paciente_id,
            fecha_nacimiento_paciente=paciente.fecha_nacimiento,
            nombre_apoderado="Apoderado registrado",
        )
    )

    resultado = contenedor.acceso_apoderado.otorgar(
        acceso, paciente_id, hoy, alcance=alcance, medio="aplicacion"
    )
    contenedor.repo_acceso.guardar(
        paciente_id,
        acceso,
        columnas_extra={
            "paciente_id": paciente_id,
            "fecha_corte": acceso.fecha_de_corte.isoformat(),
        },
    )
    if contenedor.auditoria is not None:
        contenedor.auditoria.registrar(
            actor=paciente_id,
            accion="otorgar_consentimiento_apoderado",
            entidad="acceso_apoderado",
            entidad_id=paciente_id,
            valor_despues=alcance,
        )

    return PermisosApoderadoSalida(
        puede_ver_estado_del_ciclo=resultado.puede_ver_estado_del_ciclo,
        puede_ver_pasaporte=resultado.puede_ver_pasaporte,
        puede_ver_aprendizaje=resultado.puede_ver_aprendizaje,
        base_legal=resultado.base_legal.value,
        base_legal_etiqueta=resultado.base_legal.etiqueta,
        norma=resultado.norma,
        aviso=resultado.aviso,
        dias_para_el_corte=resultado.dias_para_el_corte,
    )
