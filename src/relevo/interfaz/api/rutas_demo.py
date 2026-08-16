"""La barra de control de demo: reiniciar, avanzar etapa, cambiar de rol.

Es lo que `sembrar.py` ya hacia por linea de comandos, expuesto por HTTP para
que se pueda demostrar sin salir de la pantalla. Nada de aqui es
funcionalidad del producto: es andamio de la demostracion, y esta separado en
su propio router para que se vea que lo es.

`POST /api/demo/cambiar-rol` NO es autenticacion y no finge serlo. Hasta que
exista la sesion de servidor (C6), la interfaz declara su rol en una cabecera y
el servidor le cree. Se dice aqui en voz alta porque es exactamente el tipo de
cosa que un jurado tecnico pregunta.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from relevo.dominio.entidades.ciclo_transicion import EstadoCiclo
from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.objetos_valor.reingreso import MotivoReingreso
from relevo.interfaz.api.dependencias import (
    FECHA_DEMO,
    ContenedorDep,
    HoyDep,
    exigir_ciclo,
)
from relevo.interfaz.api.esquemas import (
    AvanzarEtapaEntrada,
    CambiarRolEntrada,
    EstadoDemoSalida,
)
from relevo.interfaz.api.roles import Rol

router = APIRouter(prefix="/api/demo", tags=["demo"])

AVISO_DEMO = (
    "Todos los datos son sinteticos. Ninguno corresponde a una persona real."
)


@router.get("/estado", response_model=EstadoDemoSalida)
def estado(contenedor: ContenedorDep) -> EstadoDemoSalida:
    """Que hay en la base ahora mismo, y si la cadena de auditoria esta intacta."""
    conteo = contenedor.bd.contar() if contenedor.bd else {}
    intacta, _ = contenedor.verificar_auditoria()
    return EstadoDemoSalida(
        es_demo=True,
        pacientes=int(conteo.get("paciente", 0)),
        ciclos=int(conteo.get("ciclo", 0)),
        entradas_auditoria=int(conteo.get("auditoria", 0)),
        cadena_intacta=intacta,
        fecha_referencia=FECHA_DEMO,
        aviso=AVISO_DEMO,
    )


@router.post("/reiniciar", response_model=EstadoDemoSalida)
def reiniciar(contenedor: ContenedorDep, hoy: HoyDep) -> EstadoDemoSalida:
    """Vuelve al punto de partida. Misma semilla = misma cohorte.

    La auditoria se conserva: un registro de auditoria que se puede borrar no
    es un registro de auditoria. En la demo eso significa que reiniciar dos
    veces deja rastro de las dos, que es justamente lo que se quiere poder
    ensenar.
    """
    if contenedor.bd is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El sistema arranco sin persistencia: no hay nada que reiniciar.",
        )
    contenedor.bd.vaciar(conservar_auditoria=True)
    contenedor.sembrar_demo(
        n_pacientes=42,
        semilla_aleatoria=20260816,
        hoy=hoy,
        ciclos_abiertos=18,
        reparto_estados={},
        vencidos_forzados=3,
    )
    return estado(contenedor)


@router.post("/avanzar-etapa")
def avanzar_etapa(
    entrada: AvanzarEtapaEntrada, contenedor: ContenedorDep, hoy: HoyDep
) -> dict[str, str]:
    """Empuja un ciclo una etapa hacia adelante, para demostrar el recorrido.

    Usa el avance natural de la linea de tramite. Si el ciclo esta en
    REINGRESO, lo reclasifica; si esta en PERDIDA_DE_SEGUIMIENTO, lo reabre —
    porque una demo que se queda atascada en la perdida no puede ensenar la
    parte del modelo que mas nos distingue.
    """
    ciclo = exigir_ciclo(contenedor, entrada.paciente_id)

    try:
        if ciclo.estado is EstadoCiclo.PERDIDA_DE_SEGUIMIENTO:
            contenedor.registrar_reingreso.ejecutar(
                ciclo,
                MotivoReingreso.REAPARECE_TRAS_PERDIDA,
                hoy,
                registrado_por="barra de demo",
            )
        elif ciclo.estado is EstadoCiclo.REINGRESO:
            contenedor.avanzar_ciclo.reclasificar(
                ciclo,
                EstadoCiclo.ACEPTADO_CON_SERVICIO,
                hoy,
                registrado_por="barra de demo",
            )
        else:
            siguiente = ciclo.siguiente_estado
            if siguiente is None:
                return {
                    "estado": ciclo.estado.value,
                    "mensaje": "El ciclo ya llego al final del recorrido.",
                }
            from relevo.dominio.entidades.ciclo_transicion import FuenteConfirmacion

            contenedor.avanzar_ciclo.ejecutar(
                ciclo,
                siguiente,
                hoy,
                registrado_por="barra de demo",
                fuente_confirmacion=(
                    FuenteConfirmacion.CONFIRMACION_RECEPTOR
                    if siguiente is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA
                    else None
                ),
            )
    except TransicionInvalida as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    contenedor.guardar_ciclo(ciclo, actor="barra de demo")
    return {
        "estado": ciclo.estado.value,
        "etiqueta": ciclo.estado.etiqueta,
        "responsable": ciclo.responsable.etiqueta,
        "mensaje": f"Turno de {ciclo.responsable.etiqueta}.",
    }


@router.post("/cambiar-rol")
def cambiar_rol(entrada: CambiarRolEntrada) -> dict[str, str]:
    """Devuelve el rol validado y a donde va. NO es autenticacion.

    El servidor no guarda sesion todavia: la interfaz manda el rol elegido en
    la cabecera `X-Relevo-Rol` en cada peticion. Esto solo valida que el valor
    exista y dice cual es la pantalla inicial de ese rol.
    """
    try:
        rol = Rol(entrada.rol)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"'{entrada.rol}' no es un rol. Validos: "
            + ", ".join(r.value for r in Rol),
        ) from None
    return {
        "rol": rol.value,
        "etiqueta": rol.etiqueta,
        "ruta_inicial": rol.ruta_inicial,
        "aviso": "La seleccion de rol en la demo no es autenticacion.",
    }
