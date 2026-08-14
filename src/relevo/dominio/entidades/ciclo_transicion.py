"""El ciclo de la derivacion: de que se emitio el Pasaporte a que el paciente
llego de verdad al servicio de adultos.

PLAN_TECNICO §7. Los plazos viven en `config/plazos_ciclo.yaml`; aqui solo
esta la maquina y su historial.

Por que existe esta entidad: hoy, al cumplir 18, el paciente simplemente deja
de aparecer y nadie sabe si llego a algun lado. El ciclo es lo que convierte
"lo derivamos" en "sabemos que llego".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from relevo.dominio.excepciones import TransicionInvalida


class EstadoCiclo(Enum):
    """Las seis etapas de la derivacion. El orden numerico es el orden real.

    Los valores enteros permiten comparar avance (`estado.value`), no son
    identificadores de base de datos.
    """

    PASAPORTE_EMITIDO = 1
    REFERENCIA_REGISTRADA = 2
    REFERENCIA_ACEPTADA = 3
    CITA_PROGRAMADA = 4
    CITA_CUMPLIDA = 5
    CONTRARREFERENCIA = 6

    @property
    def etiqueta(self) -> str:
        return {
            EstadoCiclo.PASAPORTE_EMITIDO: "Pasaporte emitido",
            EstadoCiclo.REFERENCIA_REGISTRADA: "Referencia registrada",
            EstadoCiclo.REFERENCIA_ACEPTADA: "Referencia aceptada",
            EstadoCiclo.CITA_PROGRAMADA: "Cita programada",
            EstadoCiclo.CITA_CUMPLIDA: "Cita cumplida",
            EstadoCiclo.CONTRARREFERENCIA: "Contrarreferencia recibida",
        }[self]

    @property
    def es_final(self) -> bool:
        return self is EstadoCiclo.CONTRARREFERENCIA


# Sucesor unico de cada estado. La maquina es lineal a proposito: no hay ramas
# ni saltos. Un salto significa que alguien no registro un paso, y perder ese
# registro es perder justamente el dato que el piloto viene a medir.
_SUCESOR: dict[EstadoCiclo, EstadoCiclo] = {
    EstadoCiclo.PASAPORTE_EMITIDO: EstadoCiclo.REFERENCIA_REGISTRADA,
    EstadoCiclo.REFERENCIA_REGISTRADA: EstadoCiclo.REFERENCIA_ACEPTADA,
    EstadoCiclo.REFERENCIA_ACEPTADA: EstadoCiclo.CITA_PROGRAMADA,
    EstadoCiclo.CITA_PROGRAMADA: EstadoCiclo.CITA_CUMPLIDA,
    EstadoCiclo.CITA_CUMPLIDA: EstadoCiclo.CONTRARREFERENCIA,
}


class FuenteConfirmacion(Enum):
    """Como nos enteramos de que el paciente llego a la cita.

    PLAN_TECNICO §7: el estudio de DIRIS Lima Norte documenta 110
    contrarreferencias sobre 19 951 referencias — 0.55 %. La via formal no
    funciona empiricamente. Esperar la contrarreferencia para cerrar el ciclo
    es esperar algo que en 99 de cada 100 casos no llega.

    Por eso la confirmacion admite dos fuentes y el indicador se desagrega:
    la proporcion de cada una es en si misma un hallazgo del piloto.
    """

    CONTRARREFERENCIA = "formal"
    CONFIRMACION_FAMILIA = "pragmatica"

    @property
    def etiqueta(self) -> str:
        return {
            FuenteConfirmacion.CONTRARREFERENCIA: "Contrarreferencia formal",
            FuenteConfirmacion.CONFIRMACION_FAMILIA: "Confirmacion de la familia",
        }[self]


@dataclass(frozen=True, slots=True)
class EventoCiclo:
    """Un cambio de estado, con quien lo registro y cuando.

    Inmutable: el historial no se corrige, se corrige hacia adelante. Un
    registro que se puede reescribir no sirve como evidencia del piloto.
    """

    estado: EstadoCiclo
    fecha: date
    registrado_por: str = ""
    fuente_confirmacion: FuenteConfirmacion | None = None
    """Solo tiene sentido al entrar a CITA_CUMPLIDA."""

    nota: str = ""

    def __str__(self) -> str:
        via = f" ({self.fuente_confirmacion.etiqueta})" if self.fuente_confirmacion else ""
        return f"{self.fecha.isoformat()} · {self.estado.etiqueta}{via}"


@dataclass
class CicloTransicion:
    """El seguimiento de un paciente desde el Pasaporte hasta la confirmacion.

    Se crea en el momento de emitir el Pasaporte: antes de eso no hay ciclo
    que seguir.
    """

    paciente_id: str
    fecha_inicio: date
    """Fecha de emision del Pasaporte. El estado 1 se da por hecho al crear."""

    destino_propuesto: str = ""
    """Servicio de adultos propuesto. PROPUESTO, no asignado: el sistema
    propone y una persona firma (PLAN_TECNICO §13)."""

    fecha_cita: date | None = None
    """Fecha de la cita en el servicio de adultos, cuando se programa.

    El plazo 4 -> 5 se cuenta desde aqui y no desde la fecha de programacion:
    una cita programada a tres meses no esta vencida a los treinta dias.
    """

    historial: list[EventoCiclo] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.historial:
            self.historial = [
                EventoCiclo(
                    estado=EstadoCiclo.PASAPORTE_EMITIDO,
                    fecha=self.fecha_inicio,
                    nota="Apertura del ciclo al emitir el Pasaporte",
                )
            ]

    # ── Estado ───────────────────────────────────────────────────────────────

    @property
    def estado(self) -> EstadoCiclo:
        return self.historial[-1].estado

    @property
    def fecha_estado_actual(self) -> date:
        """Desde cuando el ciclo esta en el estado en que esta.

        Es la fecha contra la que se mide el vencimiento del plazo.
        """
        return self.historial[-1].fecha

    @property
    def esta_cerrado(self) -> bool:
        """Cerrado formalmente: llego la contrarreferencia."""
        return self.estado.es_final

    @property
    def esta_confirmado(self) -> bool:
        """El paciente llego al servicio de adultos, por la via que sea.

        Esta es la pregunta que le importa al proyecto. `esta_cerrado` es la
        version burocratica de la misma pregunta, y casi nunca se cumple.
        """
        return self.estado.value >= EstadoCiclo.CITA_CUMPLIDA.value

    @property
    def fuente_de_confirmacion(self) -> FuenteConfirmacion | None:
        """Como se confirmo la llegada, si se confirmo."""
        for evento in self.historial:
            if evento.estado is EstadoCiclo.CITA_CUMPLIDA:
                return evento.fuente_confirmacion
        return None

    @property
    def siguiente_estado(self) -> EstadoCiclo | None:
        """El unico avance permitido desde aqui. None si el ciclo termino."""
        return _SUCESOR.get(self.estado)

    # ── Avance ───────────────────────────────────────────────────────────────

    def avanzar(
        self,
        estado: EstadoCiclo,
        fecha: date,
        registrado_por: str = "",
        fuente_confirmacion: FuenteConfirmacion | None = None,
        nota: str = "",
    ) -> EventoCiclo:
        """Registra el paso al siguiente estado.

        Rechaza saltos, retrocesos y repeticiones: la maquina es lineal.
        Rechaza tambien una fecha anterior al ultimo evento, porque un
        historial que no avanza en el tiempo no es un historial.
        """
        esperado = self.siguiente_estado
        if esperado is None:
            raise TransicionInvalida(
                f"El ciclo de {self.paciente_id} ya esta en {self.estado.etiqueta}: "
                "no hay estado posterior."
            )
        if estado is not esperado:
            raise TransicionInvalida(
                f"Desde {self.estado.etiqueta} solo se puede pasar a "
                f"{esperado.etiqueta}, no a {estado.etiqueta}. "
                "Un salto significa que alguien no registro un paso."
            )
        if fecha < self.fecha_estado_actual:
            raise TransicionInvalida(
                f"La fecha {fecha.isoformat()} es anterior al ultimo evento "
                f"({self.fecha_estado_actual.isoformat()})."
            )
        if estado is EstadoCiclo.CITA_CUMPLIDA and fuente_confirmacion is None:
            raise TransicionInvalida(
                "Confirmar una cita cumplida exige decir como se supo: "
                "contrarreferencia formal o confirmacion de la familia. "
                "La proporcion entre ambas es un hallazgo del piloto."
            )

        evento = EventoCiclo(
            estado=estado,
            fecha=fecha,
            registrado_por=registrado_por,
            fuente_confirmacion=fuente_confirmacion,
            nota=nota,
        )
        self.historial.append(evento)
        if estado is EstadoCiclo.CITA_PROGRAMADA and self.fecha_cita is None:
            # Respaldo: si nadie dijo para cuando es la cita, se asume el dia
            # del registro. Es conservador — adelanta el vencimiento — y hace
            # visible el dato que falta.
            self.fecha_cita = fecha
        return evento

    def dias_en_estado_actual(self, hoy: date) -> int:
        """Cuanto lleva parado aqui. Es el numerador del control de plazos."""
        referencia = self.fecha_estado_actual
        if self.estado is EstadoCiclo.CITA_PROGRAMADA and self.fecha_cita is not None:
            # El plazo 4 -> 5 se cuenta desde la fecha de la cita.
            referencia = self.fecha_cita
        return (hoy - referencia).days

    def __str__(self) -> str:
        return f"{self.paciente_id} · {self.estado.etiqueta} desde {self.fecha_estado_actual.isoformat()}"
