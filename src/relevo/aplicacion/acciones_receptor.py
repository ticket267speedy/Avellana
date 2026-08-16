"""Las seis acciones del hospital receptor.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTE ARCHIVO CIERRA EL DOLOR B4
═══════════════════════════════════════════════════════════════════════════════

Hasta ahora el hospital receptor era un DATO —una cadena de texto en
`destino_propuesto`— y no un usuario. El ciclo pasaba de "referencia
registrada" a "referencia aceptada" sin que existiera contacto humano entre
equipos. Eso es transferencia FRIA, que es justo lo que el INSN dice que falla:
su entregable 7 pide "transferencia calida", con ese nombre.

CERO FORMULARIOS. Las seis acciones son un clic cada una. El receptor no teclea
diagnostico, ni tratamiento, ni filiacion: eso ya esta en el expediente que
recibio. Lo unico que hace es decidir y avanzar.

La tercera accion —solicitar informacion complementaria— es la mas importante
de las seis: es lo unico que convierte un rechazo silencioso en una peticion
trazable. El 13.6 % de las referencias vuelve por informacion incompleta
(DIRIS Lima Norte) y hoy nadie sabe cual ni por que.

Importa solo `dominio`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.objetos_valor.reingreso import MotivoReingreso
from relevo.dominio.objetos_valor.responsable import Responsable
from relevo.dominio.servicios.maquina_ciclo import MaquinaCiclo

from relevo.aplicacion.avanzar_ciclo import AvanzarCiclo, ResultadoAvance


class AccionReceptor(Enum):
    """Las seis. Cada una es una transicion con responsable y plazo."""

    CONFIRMAR_RECEPCION = "confirmar_recepcion"
    INICIAR_EVALUACION = "iniciar_evaluacion"
    SOLICITAR_INFORMACION = "solicitar_informacion"
    ACEPTAR_CON_SERVICIO = "aceptar_con_servicio"
    PROGRAMAR_CITA = "programar_cita"
    CONFIRMAR_PRIMERA_ATENCION = "confirmar_primera_atencion"

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    @property
    def desde(self) -> EstadoCiclo | None:
        """Estado en el que la accion esta disponible. None = varios."""
        return _DESDE.get(self)


_ETIQUETAS: dict[AccionReceptor, str] = {
    AccionReceptor.CONFIRMAR_RECEPCION: "Confirmar recepcion",
    AccionReceptor.INICIAR_EVALUACION: "Iniciar evaluacion",
    AccionReceptor.SOLICITAR_INFORMACION: "Solicitar informacion complementaria",
    AccionReceptor.ACEPTAR_CON_SERVICIO: "Aceptar y asignar servicio",
    AccionReceptor.PROGRAMAR_CITA: "Programar cita",
    AccionReceptor.CONFIRMAR_PRIMERA_ATENCION: "Confirmar primera atencion",
}

_DESDE: dict[AccionReceptor, EstadoCiclo] = {
    AccionReceptor.CONFIRMAR_RECEPCION: EstadoCiclo.REFERENCIA_ENVIADA,
    AccionReceptor.INICIAR_EVALUACION: EstadoCiclo.RECEPCION_CONFIRMADA,
    AccionReceptor.SOLICITAR_INFORMACION: EstadoCiclo.EN_EVALUACION,
    AccionReceptor.ACEPTAR_CON_SERVICIO: EstadoCiclo.EN_EVALUACION,
    AccionReceptor.PROGRAMAR_CITA: EstadoCiclo.ACEPTADO_CON_SERVICIO,
    AccionReceptor.CONFIRMAR_PRIMERA_ATENCION: EstadoCiclo.CITA_PROGRAMADA,
}


class FaltaInformacion(Enum):
    """Lista CERRADA de lo que el receptor puede pedir.

    Cerrada a proposito. Un campo de texto libre aqui seria la puerta trasera
    por la que volveria la doble digitacion —y, peor, por la que un profesional
    escribiria contenido clinico que nadie verifico ni firmo.

    `OTRO` existe porque una lista cerrada sin escape obliga a mentir; lleva
    detalle en texto, pero ese texto es complementario y nunca el portador del
    dato clinico.
    """

    EPICRISIS = "falta_epicrisis"
    RESULTADO_LABORATORIO = "falta_resultado_laboratorio"
    CONSENTIMIENTO = "falta_consentimiento"
    DATO_DE_CONTACTO = "falta_dato_de_contacto"
    OTRO = "otro"

    @property
    def etiqueta(self) -> str:
        return {
            FaltaInformacion.EPICRISIS: "Falta la epicrisis",
            FaltaInformacion.RESULTADO_LABORATORIO: "Falta un resultado de laboratorio",
            FaltaInformacion.CONSENTIMIENTO: "Falta el consentimiento",
            FaltaInformacion.DATO_DE_CONTACTO: "Falta un dato de contacto",
            FaltaInformacion.OTRO: "Otro",
        }[self]


@dataclass(frozen=True, slots=True)
class PeticionDeInformacion:
    """Una peticion trazable. Esto es lo que convierte el silencio en dato."""

    faltantes: tuple[FaltaInformacion, ...]
    fecha: date
    solicitado_por: str = ""
    detalle: str = ""
    """Texto libre OPCIONAL y complementario. Nunca el portador del dato
    clinico: para eso estan los codigos de `faltantes`."""

    def __post_init__(self) -> None:
        if not self.faltantes:
            raise ValueError(
                "Una peticion de informacion sin decir que falta es un rechazo "
                "silencioso con otro nombre."
            )

    def resumen(self) -> str:
        return ", ".join(f.etiqueta for f in self.faltantes)


@dataclass(frozen=True, slots=True)
class ResultadoAccionReceptor:
    """Lo que devuelve cualquiera de las seis."""

    accion: AccionReceptor
    ciclo: CicloTransicion
    avance: ResultadoAvance | None
    """None en SOLICITAR_INFORMACION: esa accion no cambia de estado."""

    peticion: PeticionDeInformacion | None = None
    devolvio_el_turno: bool = False

    @property
    def responsable_actual(self) -> Responsable:
        return self.ciclo.responsable


@dataclass(frozen=True, slots=True)
class AccionesReceptor:
    """Las seis acciones, cada una de un clic.

    `avanzar` se inyecta en vez de instanciarse: los plazos son politica
    clinica cargada de `config/`, y este caso de uso no debe conocerlos.
    """

    avanzar: AvanzarCiclo

    @classmethod
    def con_maquina(cls, maquina: MaquinaCiclo) -> AccionesReceptor:
        return cls(avanzar=AvanzarCiclo(maquina=maquina))

    # ── 1 ────────────────────────────────────────────────────────────────────
    def confirmar_recepcion(
        self, ciclo: CicloTransicion, hoy: date, quien: str = ""
    ) -> ResultadoAccionReceptor:
        """Acuso de recibo. NO significa aceptar."""
        avance = self.avanzar.ejecutar(
            ciclo, EstadoCiclo.RECEPCION_CONFIRMADA, hoy, registrado_por=quien
        )
        return ResultadoAccionReceptor(
            accion=AccionReceptor.CONFIRMAR_RECEPCION, ciclo=ciclo, avance=avance
        )

    # ── 2 ────────────────────────────────────────────────────────────────────
    def iniciar_evaluacion(
        self, ciclo: CicloTransicion, hoy: date, quien: str = ""
    ) -> ResultadoAccionReceptor:
        """Un medico abrio el expediente."""
        avance = self.avanzar.ejecutar(
            ciclo, EstadoCiclo.EN_EVALUACION, hoy, registrado_por=quien
        )
        return ResultadoAccionReceptor(
            accion=AccionReceptor.INICIAR_EVALUACION, ciclo=ciclo, avance=avance
        )

    # ── 3 · la mas importante de las seis ────────────────────────────────────
    def solicitar_informacion(
        self,
        ciclo: CicloTransicion,
        faltantes: tuple[FaltaInformacion, ...],
        hoy: date,
        quien: str = "",
        detalle: str = "",
    ) -> ResultadoAccionReceptor:
        """Pide lo que falta. NO cambia de estado: devuelve el turno al INSN.

        No cambia de estado a proposito. Retroceder a PREPARACION borraria del
        historial que el expediente si llego a evaluarse, y ese hecho es
        justamente lo que distingue "lo estan viendo y falta algo" de "nadie lo
        ha abierto". El turno se devuelve reiniciando el plazo, que es lo que
        de verdad hace falta.
        """
        peticion = PeticionDeInformacion(
            faltantes=faltantes, fecha=hoy, solicitado_por=quien, detalle=detalle
        )
        # Se anota en el historial como un evento del mismo estado: el ciclo no
        # avanza, pero el hecho queda registrado con fecha y con quien lo pidio.
        ciclo.historial.append(
            type(ciclo.historial[-1])(
                estado=ciclo.estado,
                fecha=hoy,
                registrado_por=quien,
                nota=f"Informacion complementaria solicitada: {peticion.resumen()}",
            )
        )
        return ResultadoAccionReceptor(
            accion=AccionReceptor.SOLICITAR_INFORMACION,
            ciclo=ciclo,
            avance=None,
            peticion=peticion,
            devolvio_el_turno=True,
        )

    # ── 4 ────────────────────────────────────────────────────────────────────
    def aceptar_con_servicio(
        self, ciclo: CicloTransicion, servicio: str, hoy: date, quien: str = ""
    ) -> ResultadoAccionReceptor:
        """Acepta Y asigna servicio. Las dos cosas o ninguna.

        `servicio` es una seleccion de la cartera del establecimiento, no texto
        clinico libre: es el nombre de un servicio y el medico responsable.
        Aceptar sin servicio concreto es una carta amable que no le da cita a
        nadie, y por eso se rechaza.
        """
        if not servicio.strip():
            raise TransicionInvalida(
                "Aceptar exige asignar servicio. Una aceptacion sin servicio "
                "concreto no le da cita a nadie."
            )
        ciclo.servicio_asignado = servicio
        avance = self.avanzar.ejecutar(
            ciclo, EstadoCiclo.ACEPTADO_CON_SERVICIO, hoy, registrado_por=quien
        )
        return ResultadoAccionReceptor(
            accion=AccionReceptor.ACEPTAR_CON_SERVICIO, ciclo=ciclo, avance=avance
        )

    # ── 5 ────────────────────────────────────────────────────────────────────
    def programar_cita(
        self,
        ciclo: CicloTransicion,
        fecha_cita: date,
        hoy: date,
        quien: str = "",
    ) -> ResultadoAccionReceptor:
        """Pone fecha. El turno pasa al paciente: nadie puede ir por el."""
        ciclo.fecha_cita = fecha_cita
        avance = self.avanzar.ejecutar(
            ciclo, EstadoCiclo.CITA_PROGRAMADA, hoy, registrado_por=quien
        )
        return ResultadoAccionReceptor(
            accion=AccionReceptor.PROGRAMAR_CITA, ciclo=ciclo, avance=avance
        )

    # ── 6 ────────────────────────────────────────────────────────────────────
    def confirmar_primera_atencion(
        self, ciclo: CicloTransicion, hoy: date, quien: str = ""
    ) -> ResultadoAccionReceptor:
        """El paciente llego y fue atendido.

        Un clic del receptor en su propia bandeja es la confirmacion mas barata
        y mas fiable de las tres fuentes: la contrarreferencia formal llega en
        el 0.55 % de los casos y llamar a la familia cuesta una llamada.
        """
        avance = self.avanzar.ejecutar(
            ciclo,
            EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
            hoy,
            registrado_por=quien,
            fuente_confirmacion=FuenteConfirmacion.CONFIRMACION_RECEPTOR,
        )
        return ResultadoAccionReceptor(
            accion=AccionReceptor.CONFIRMAR_PRIMERA_ATENCION,
            ciclo=ciclo,
            avance=avance,
        )

    # ── 6b · la variante que no se puede olvidar ─────────────────────────────
    def registrar_inasistencia(
        self, ciclo: CicloTransicion, hoy: date, quien: str = ""
    ) -> ResultadoAccionReceptor:
        """El paciente no se presento. Reabre el ciclo con su motivo.

        Es la variante de la accion 6 y no una septima accion: en la bandeja
        del receptor aparecen juntas, porque son las dos respuestas posibles a
        la misma pregunta.
        """
        avance = self.avanzar.ejecutar(
            ciclo,
            EstadoCiclo.REINGRESO,
            hoy,
            registrado_por=quien,
            motivo_reingreso=MotivoReingreso.NO_ASISTIO_A_PRIMERA_CITA,
        )
        return ResultadoAccionReceptor(
            accion=AccionReceptor.CONFIRMAR_PRIMERA_ATENCION,
            ciclo=ciclo,
            avance=avance,
        )

    # ── Bandeja ──────────────────────────────────────────────────────────────
    def acciones_disponibles(
        self, ciclo: CicloTransicion
    ) -> tuple[AccionReceptor, ...]:
        """Que botones pintar para este ciclo. Nunca todos a la vez.

        Una bandeja que muestra las seis acciones siempre obliga al profesional
        a razonar cual toca, que es exactamente el trabajo que el sistema
        deberia estarle ahorrando.
        """
        return tuple(a for a in AccionReceptor if _DESDE.get(a) is ciclo.estado)


__all__ = [
    "AccionReceptor",
    "AccionesReceptor",
    "FaltaInformacion",
    "PeticionDeInformacion",
    "ResultadoAccionReceptor",
]
