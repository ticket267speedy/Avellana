"""Acciones del equipo del INSN sobre un ciclo, y el Pasaporte.

Prefijo `/api/insn/` a proposito: junto con `/api/receptor/`, es el conjunto de
endpoints que `test_sin_captura_clinica_por_personal` recorre para comprobar
que **ninguno acepta un campo clinico de escritura libre**.

Lo que el profesional del INSN hace aqui es exactamente lo que dice el
principio: confirmar, corregir, firmar y avanzar el ciclo. Ni un diagnostico
tecleado.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.objetos_valor.reingreso import MotivoReingreso
from relevo.interfaz.api.dependencias import (
    ContenedorDep,
    EstablecimientoDep,
    HoyDep,
    RolDep,
    exigir_ciclo,
    exigir_lectura_clinica,
    exigir_paciente,
    exigir_visibilidad,
)
from relevo.interfaz.api.esquemas import EntradaDePersonal
from relevo.interfaz.api.roles import Rol

router = APIRouter(tags=["insn"])


class RegistrarReingresoEntrada(EntradaDePersonal):
    """Reabrir un ciclo. Un clic y un motivo de lista cerrada.

    `nota_administrativa` esta explicitamente marcada como no clinica: describe
    la gestion —con quien se hablo, por que via—, nunca al paciente.
    """

    motivo: str
    registrado_por: str = ""
    nota_administrativa: str = ""


@router.post("/api/insn/{paciente_id}/reingreso")
def registrar_reingreso(
    paciente_id: str,
    entrada: RegistrarReingresoEntrada,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
) -> dict[str, object]:
    """Reabre el ciclo. Con el paciente >= 18, solo gestion administrativa.

    La respuesta lleva `solo_administrativas` y el aviso correspondiente: es lo
    que impide que alguien —del equipo o del jurado— lea "reingreso" como
    "vuelve a atenderse en el INSN".
    """
    exigir_lectura_clinica(rol)
    ciclo = exigir_ciclo(contenedor, paciente_id)

    try:
        motivo = MotivoReingreso(entrada.motivo)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"'{entrada.motivo}' no es un motivo de reingreso.",
        ) from None

    try:
        resultado = contenedor.registrar_reingreso.ejecutar(
            ciclo,
            motivo,
            hoy,
            registrado_por=entrada.registrado_por,
            nota_administrativa=entrada.nota_administrativa,
        )
    except TransicionInvalida as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    contenedor.guardar_ciclo(ciclo, actor=entrada.registrado_por or "insn")

    return {
        "estado": ciclo.estado.value,
        "etiqueta": ciclo.estado.etiqueta,
        "motivo": motivo.value,
        "motivo_etiqueta": motivo.etiqueta,
        "responsable": ciclo.responsable.etiqueta,
        "solo_administrativas": resultado.solo_administrativas,
        "acciones": sorted(a.value for a in resultado.acciones),
        "aviso": resultado.aviso(),
    }


@router.get("/api/insn/reingresos-estancados")
def reingresos_estancados(
    contenedor: ContenedorDep, hoy: HoyDep, rol: RolDep
) -> list[dict[str, object]]:
    """Los ciclos que llevan demasiado tiempo en REINGRESO sin reclasificar.

    REINGRESO es transitorio. Esta lista es lo que impide que se convierta en
    el cajon donde los casos dificiles van a morir sin que nadie lo note.
    """
    exigir_lectura_clinica(rol)
    estancados = contenedor.registrar_reingreso.reingresos_estancados(
        list(contenedor.ciclos()), hoy
    )
    return [
        {
            "paciente_id": c.paciente_id,
            "dias_sin_reclasificar": c.dias_en_estado_actual(hoy),
            "motivos": [r.motivo.etiqueta for r in c.reingresos_sin_reclasificar],
        }
        for c in estancados
    ]


@router.get("/api/pacientes/{paciente_id}/pasaporte")
def descargar_pasaporte(
    paciente_id: str,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
    establecimiento: EstablecimientoDep,
) -> Response:
    """El Pasaporte de Salud 18+ en PDF, listo para imprimir y firmar.

    Sale con marca de agua "DATOS SINTETICOS — DEMO" y con el aviso normativo
    al pie. Ninguna dosis no verificada en la fuente se imprime como valor: sale
    como hueco, para que el medico lo llene (regla 8).

    El ADMINISTRADOR no puede abrir esto: es lectura clinica. El receptor si,
    pero solo de las referencias dirigidas a su establecimiento — que es
    precisamente para lo que el Pasaporte existe.
    """
    exigir_lectura_clinica(rol)
    if rol is Rol.PROFESIONAL_RECEPTOR:
        exigir_visibilidad(
            exigir_ciclo(contenedor, paciente_id), rol, establecimiento
        )

    paciente = exigir_paciente(contenedor, paciente_id)
    pdf = contenedor.emitir_pasaporte(paciente, hoy)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="pasaporte_{paciente_id}.pdf"'
            )
        },
    )


@router.get("/api/pacientes/{paciente_id}/fhir")
def descargar_fhir(
    paciente_id: str,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
    establecimiento: EstablecimientoDep,
) -> Response:
    """El Bundle HL7 FHIR CorePE R4 (MINSA) en JSON, listo para intercambio institucional.

    Estructura validada conforme a la Guía Nacional CorePE y al International Patient Summary.
    """
    exigir_lectura_clinica(rol)
    if rol is Rol.PROFESIONAL_RECEPTOR:
        exigir_visibilidad(
            exigir_ciclo(contenedor, paciente_id), rol, establecimiento
        )

    paciente = exigir_paciente(contenedor, paciente_id)
    fhir_json = contenedor.emitir_fhir(paciente, hoy)
    return Response(
        content=fhir_json,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="FHIR_CorePE_{paciente_id}.json"'
            )
        },
    )

