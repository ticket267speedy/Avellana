"""Conciliacion de medicacion: el paciente declara, el equipo del INSN coteja.

Lo que el paciente declara NUNCA sobrescribe el Pasaporte. Abre un caso
asignado al equipo del INSN, y una persona decide. El sistema reporta la
discrepancia; no elige cual version es la correcta.

Nota sobre el prefijo: la declaracion del paciente vive bajo `/api/pacientes/`
y la resolucion bajo `/api/insn/`. No es cosmetica — es lo que permite que
`test_sin_captura_clinica_por_personal` recorra los endpoints de personal por
prefijo y compruebe que ninguno acepta un campo clinico de escritura libre.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from relevo.dominio.entidades.conciliacion import (
    CasoDeConciliacion,
    MedicacionDeclarada,
)
from relevo.interfaz.api.dependencias import (
    ContenedorDep,
    HoyDep,
    RolDep,
    exigir_lectura_clinica,
    exigir_paciente,
)
from relevo.interfaz.api.esquemas import (
    ConciliacionSalida,
    DeclararMedicacionEntrada,
    DiscrepanciaSalida,
    LineaMedicacionSalida,
    ResolverConciliacionEntrada,
)

router = APIRouter(tags=["conciliacion"])

# Las declaraciones del paciente viven en memoria del proceso mientras dura la
# demo. NO van a SQLite todavia a proposito: son datos clinicos declarados sin
# verificar, y persistirlos sin haber definido su ciclo de vida —cuanto duran,
# quien los borra, que pasa cuando el equipo los resuelve— seria acumular
# informacion sensible sin politica de retencion.
# TODO: confirmar con mentor — retencion de lo declarado por el paciente.
_DECLARADAS: dict[str, list[MedicacionDeclarada]] = {}


def _a_salida(
    contenedor: ContenedorDep, paciente_id: str, caso: CasoDeConciliacion, requiere: bool
) -> ConciliacionSalida:
    paciente = contenedor.paciente(paciente_id)
    declarados = _DECLARADAS.get(paciente_id, [])
    lineas = (
        contenedor.conciliar.vista_para_el_paciente(paciente, declarados)
        if paciente
        else ()
    )
    return ConciliacionSalida(
        paciente_id=paciente_id,
        requiere_revision=requiere,
        responsable=caso.responsable.etiqueta,
        titular=(
            "Se cotejo la medicacion y coincide."
            if not requiere
            else f"{caso.total_discrepancias} diferencias. Las revisa el equipo "
            "del INSN."
        ),
        lineas=[
            LineaMedicacionSalida(
                nombre=le.nombre,
                dosis=le.dosis,
                frecuencia=le.frecuencia,
                origen=le.origen.value,
                insignia=le.insignia,
                hay_que_completar=le.hay_que_completar,
            )
            for le in lineas
        ],
        discrepancias=[
            DiscrepanciaSalida(
                tipo=d.tipo.value,
                etiqueta=d.tipo.etiqueta,
                medicamento=d.medicamento,
                valor_pasaporte=d.valor_pasaporte,
                valor_declarado=d.valor_declarado,
                descripcion=d.descripcion(),
            )
            for d in caso.discrepancias
        ],
    )


@router.post(
    "/api/pacientes/{paciente_id}/medicacion/declarar",
    response_model=ConciliacionSalida,
    tags=["conciliacion"],
)
def declarar_medicacion(
    paciente_id: str,
    entrada: DeclararMedicacionEntrada,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
) -> ConciliacionSalida:
    """El paciente dice lo que toma, con sus palabras.

    Es la unica entrada clinica de texto libre de toda la API, y viene del
    paciente. No es doble digitacion: nadie mas tenia este dato.
    """
    exigir_lectura_clinica(rol)
    paciente = exigir_paciente(contenedor, paciente_id)

    declarados = [
        MedicacionDeclarada(
            nombre=m.nombre,
            dosis=m.dosis,
            frecuencia=m.frecuencia,
            fecha_declaracion=hoy,
            lo_sigue_tomando=m.lo_sigue_tomando,
        )
        for m in entrada.medicamentos
    ]
    _DECLARADAS[paciente_id] = declarados

    resultado = contenedor.conciliar.ejecutar(paciente, declarados, hoy)
    return _a_salida(contenedor, paciente_id, resultado.caso, resultado.requiere_revision)


@router.get(
    "/api/pacientes/{paciente_id}/conciliacion", response_model=ConciliacionSalida
)
def ver_conciliacion(
    paciente_id: str, contenedor: ContenedorDep, hoy: HoyDep, rol: RolDep
) -> ConciliacionSalida:
    """Las dos listas juntas, cada linea con su insignia de origen.

    Mezcladas y etiquetadas, no en dos tablas separadas: dos tablas obligarian
    al paciente a cotejarlas el mismo, que es justo el trabajo que este
    mecanismo viene a hacer.
    """
    exigir_lectura_clinica(rol)
    paciente = exigir_paciente(contenedor, paciente_id)
    declarados = _DECLARADAS.get(paciente_id, [])
    resultado = contenedor.conciliar.ejecutar(paciente, declarados, hoy)
    return _a_salida(contenedor, paciente_id, resultado.caso, resultado.requiere_revision)


@router.post(
    "/api/insn/{paciente_id}/conciliacion/resolver", response_model=ConciliacionSalida
)
def resolver_conciliacion(
    paciente_id: str,
    entrada: ResolverConciliacionEntrada,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
) -> ConciliacionSalida:
    """Una persona decide. El sistema nunca elige cual version es la correcta.

    Exige nombre y nota: una conciliacion resuelta sin decir quien ni que
    decidio no se puede auditar, y lo que no se puede auditar en este dominio
    equivale a no haber pasado.
    """
    exigir_lectura_clinica(rol)
    paciente = exigir_paciente(contenedor, paciente_id)
    declarados = _DECLARADAS.get(paciente_id, [])
    resultado = contenedor.conciliar.ejecutar(paciente, declarados, hoy)

    try:
        resultado.caso.tomar(hoy)
        resultado.caso.resolver(entrada.quien, hoy, entrada.nota)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)
        ) from error

    if contenedor.auditoria is not None:
        contenedor.auditoria.registrar(
            actor=entrada.quien,
            accion="resolver_conciliacion",
            entidad="conciliacion",
            entidad_id=paciente_id,
            valor_despues=entrada.nota,
        )
    return _a_salida(contenedor, paciente_id, resultado.caso, False)
