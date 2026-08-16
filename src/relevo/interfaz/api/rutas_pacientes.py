"""Radar, paciente y ciclo. Los handlers solo traducen HTTP <-> casos de uso.

Ninguna logica de negocio vive aqui. Si algo de este archivo empezara a decidir
—que estado sigue, quien tiene el turno, si un plazo vencio— seria la senal de
que hay que mover ese trozo a `aplicacion/`.

La prueba de que esa disciplina se cumplio: entre el checkpoint C3 y el C4, el
diff de `dominio/` y `aplicacion/` es de cero lineas. Anadir una API entera sin
tocar el nucleo ES la demostracion en vivo de la promesa del pitch.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, status

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.objetos_valor.estado_ciclo import ETAPAS_DE_TRAMITE
from relevo.dominio.objetos_valor.reingreso import MotivoReingreso
from relevo.dominio.servicios.corte_etario import dias_para_corte
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
from relevo.interfaz.api.esquemas import (
    AporteSalida,
    AvanzarCicloEntrada,
    CicloSalida,
    EtapaSalida,
    EventoSalida,
    FilaRadarSalida,
    IndiceSalida,
    PacienteSalida,
)
from relevo.interfaz.api.roles import Rol
from relevo.interfaz.arranque import Contenedor

router = APIRouter(prefix="/api/pacientes", tags=["pacientes"])


# ═══════════════════════════════════════════════════════════════════════════
# Traductores. Estan aqui y no en `esquemas.py` porque son la costura entre
# dos modelos, y una costura pertenece al sitio donde se cose.
# ═══════════════════════════════════════════════════════════════════════════


def indice_a_salida(indice: object) -> IndiceSalida:
    aportes = getattr(indice, "aportes", ())
    return IndiceSalida(
        valor=float(getattr(indice, "valor", 0.0)),
        z=float(getattr(indice, "z", 0.0)),
        estado=str(getattr(getattr(indice, "estado", None), "value", "")),
        confianza=float(getattr(indice, "confianza", 0.0)),
        datos_insuficientes=bool(getattr(indice, "datos_insuficientes", False)),
        aportes=[
            AporteSalida(
                nombre=a.nombre,
                valor=a.x,
                beta=a.beta,
                aporte=a.aporte,
                dato_faltante=a.dato_faltante,
            )
            for a in aportes
        ],
    )


def ciclo_a_salida(
    ciclo: CicloTransicion, contenedor: Contenedor, hoy: date
) -> CicloSalida:
    evaluacion = contenedor.evaluar_plazo(ciclo, hoy)
    alcanzados = {e.estado for e in ciclo.historial}

    return CicloSalida(
        paciente_id=ciclo.paciente_id,
        estado=ciclo.estado.value,
        etiqueta=ciclo.estado.etiqueta,
        etiqueta_llana=ciclo.estado.etiqueta_llana,
        responsable=ciclo.responsable.value,
        responsable_etiqueta=ciclo.responsable.etiqueta,
        fecha_estado=ciclo.fecha_estado_actual,
        dias_en_estado=ciclo.dias_en_estado_actual(hoy),
        plazo_dias=evaluacion.plazo_dias,
        situacion_plazo=evaluacion.situacion.value,
        fecha_limite=evaluacion.fecha_limite,
        establecimiento_receptor=ciclo.establecimiento_receptor,
        servicio_asignado=ciclo.servicio_asignado,
        fecha_cita=ciclo.fecha_cita,
        tiene_destino_asegurado=ciclo.tiene_destino_asegurado,
        transiciones_posibles=sorted(e.value for e in ciclo.transiciones_posibles),
        etapas=[
            EtapaSalida(
                orden=etapa.orden,
                estado=etapa.value,
                etiqueta=etapa.etiqueta,
                etiqueta_llana=etapa.etiqueta_llana,
                # Alcanzada si se paso por ella, o si el ciclo ya esta mas
                # adelante: un ciclo migrado del modelo de seis puede no tener
                # en el historial las etapas que aquel no distinguia.
                alcanzada=(
                    etapa in alcanzados
                    or (ciclo.estado.es_de_tramite and etapa.orden < ciclo.estado.orden)
                ),
                es_actual=etapa is ciclo.estado,
            )
            for etapa in ETAPAS_DE_TRAMITE
        ],
        historial=[
            EventoSalida(
                estado=e.estado.value,
                etiqueta=e.estado.etiqueta,
                fecha=e.fecha,
                registrado_por=e.registrado_por,
                nota=e.nota,
            )
            for e in ciclo.historial
        ],
    )


def _paciente_a_salida(paciente: Paciente, hoy: date) -> PacienteSalida:
    return PacienteSalida(
        id=paciente.id,
        edad=paciente.edad(hoy),
        sexo=paciente.sexo,
        procedencia=paciente.procedencia,
        tipo_seguro=paciente.tipo_seguro.value,
        meses_restantes=paciente.meses_hasta_corte(hoy),
        cohorte=paciente.cohorte(hoy).value,
        diagnosticos=[str(dx) for dx in paciente.diagnosticos],
        # `texto_seguro` y no la dosis cruda: si no esta verificada en la
        # fuente sale como hueco, nunca como un numero plausible (regla 8).
        medicamentos=[m.texto_seguro() for m in paciente.medicamentos],
        dispositivos=[str(d) for d in paciente.dispositivos],
        alergias=list(paciente.alergias),
        traq=paciente.traq.puntaje if paciente.traq else None,
        tiene_contacto_vigente=paciente.tiene_contacto_vigente(hoy),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════


@router.get("", response_model=list[FilaRadarSalida])
def listar_pacientes(
    contenedor: ContenedorDep, hoy: HoyDep, rol: RolDep
) -> list[FilaRadarSalida]:
    """El radar: la cohorte ordenada por IUT, con semaforo y turno.

    El IUT **no prioriza pacientes; ordena la cola de trabajo del equipo de
    transicion**. No decide quien se atiende primero en un hospital: decide a
    quien llama primero la trabajadora social. Cada fila trae su desglose
    completo, y cualquier persona puede reordenar la cola a mano.
    """
    exigir_lectura_clinica(rol)
    if rol is Rol.PROFESIONAL_RECEPTOR:
        # El receptor no tiene radar: tiene bandeja. Darle la cohorte entera
        # del INSN es el problema de proteccion de datos que decimos evitar.
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El profesional receptor ve su bandeja, no la cohorte del INSN.",
        )
    if not contenedor.pacientes():
        return []

    ciclos = {c.paciente_id: c for c in contenedor.ciclos()}
    filas: list[FilaRadarSalida] = []

    for fila in contenedor.radar(hoy).filas:
        ciclo = ciclos.get(fila.id)
        dx = fila.paciente.diagnostico_principal
        filas.append(
            FilaRadarSalida(
                id=fila.id,
                edad=fila.edad,
                meses_restantes=fila.meses_restantes,
                cohorte=fila.clasificacion.cohorte.value,
                diagnostico_principal=str(dx) if dx else "sin diagnostico registrado",
                indice=indice_a_salida(fila.indice),
                estado_ciclo=ciclo.estado.value if ciclo else None,
                estado_ciclo_etiqueta=ciclo.estado.etiqueta if ciclo else None,
                responsable=ciclo.responsable.etiqueta if ciclo else None,
                tiene_destino_asegurado=(
                    ciclo.tiene_destino_asegurado if ciclo else False
                ),
                dias_para_corte=dias_para_corte(fila.paciente.fecha_nacimiento, hoy),
                requiere_atencion_ahora=fila.requiere_atencion_ahora,
            )
        )
    return filas


@router.get("/{paciente_id}", response_model=PacienteSalida)
def obtener_paciente(
    paciente_id: str,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
    establecimiento: EstablecimientoDep,
) -> PacienteSalida:
    exigir_lectura_clinica(rol)
    paciente = exigir_paciente(contenedor, paciente_id)
    if rol is Rol.PROFESIONAL_RECEPTOR:
        exigir_visibilidad(exigir_ciclo(contenedor, paciente_id), rol, establecimiento)
    return _paciente_a_salida(paciente, hoy)


@router.get("/{paciente_id}/ciclo", response_model=CicloSalida)
def obtener_ciclo(
    paciente_id: str,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
    establecimiento: EstablecimientoDep,
) -> CicloSalida:
    """Estado, responsable, plazo y la linea de tiempo de siete etapas."""
    ciclo = exigir_ciclo(contenedor, paciente_id)
    exigir_visibilidad(ciclo, rol, establecimiento)
    return ciclo_a_salida(ciclo, contenedor, hoy)


@router.post("/{paciente_id}/ciclo/avanzar", response_model=CicloSalida)
def avanzar_ciclo(
    paciente_id: str,
    entrada: AvanzarCicloEntrada,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
    establecimiento: EstablecimientoDep,
) -> CicloSalida:
    """Un clic. Ni un dato clinico viaja con el."""
    exigir_lectura_clinica(rol)
    ciclo = exigir_ciclo(contenedor, paciente_id)
    exigir_visibilidad(ciclo, rol, establecimiento)

    try:
        destino = EstadoCiclo(entrada.estado)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"'{entrada.estado}' no es un estado del ciclo.",
        ) from None

    fuente = _fuente(entrada.fuente_confirmacion)
    motivo = _motivo(entrada.motivo_reingreso)

    try:
        if ciclo.estado is EstadoCiclo.REINGRESO and destino.es_de_tramite:
            contenedor.avanzar_ciclo.reclasificar(
                ciclo, destino, hoy, registrado_por=entrada.registrado_por
            )
        else:
            contenedor.avanzar_ciclo.ejecutar(
                ciclo,
                destino,
                hoy,
                registrado_por=entrada.registrado_por,
                fuente_confirmacion=fuente,
                motivo_reingreso=motivo,
                nota_administrativa=entrada.nota_administrativa,
            )
    except TransicionInvalida as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error

    contenedor.guardar_ciclo(ciclo, actor=entrada.registrado_por or rol.value)
    return ciclo_a_salida(ciclo, contenedor, hoy)


def _fuente(valor: str | None) -> FuenteConfirmacion | None:
    if not valor:
        return None
    try:
        return FuenteConfirmacion(valor)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"'{valor}' no es una fuente de confirmacion.",
        ) from None


def _motivo(valor: str | None) -> MotivoReingreso | None:
    if not valor:
        return None
    try:
        return MotivoReingreso(valor)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"'{valor}' no es un motivo de reingreso.",
        ) from None
