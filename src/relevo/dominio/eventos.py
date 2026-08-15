"""Eventos de dominio: las cosas que pasan.

POR QUE ESTO ES EL HUECO GRANDE DEL PROYECTO
Todo el negocio consiste en que pasan cosas — se emite un Pasaporte, vence un
plazo, alguien confirma una cita. `CicloTransicion` ya llevaba su historia con
`EventoCiclo`, pero esos eventos no salian de la entidad: nadie se suscribia y
nada reaccionaba. Con un modelo solo consultado, para enterarte de un
vencimiento tienes que ir a preguntar, y eso significa que alguien tiene que
acordarse de mirar.

El principio rector del proyecto es el contrario: **el sistema busca a la
persona; la persona no busca al sistema.** Estos eventos son ese principio
escrito en codigo en vez de en el dossier.

COMO SE PUBLICAN
No se publican desde aqui. El dominio NO conoce ningun bus de eventos: las
entidades y los servicios los DEVUELVEN, y el caso de uso decide que hacer con
ellos. Es lo mas simple que funciona y mantiene el dominio sin dependencias.

Sin imports externos, como todo `dominio/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from relevo.dominio.entidades.ciclo_transicion import EstadoCiclo, FuenteConfirmacion


@dataclass(frozen=True, slots=True)
class EventoDominio:
    """Algo que paso. Inmutable, fechado, y con el paciente al que le paso.

    Inmutable a proposito: un hecho no se corrige, se corrige hacia adelante
    con otro hecho. Un registro reescribible no sirve como evidencia del piloto.
    """

    ocurrido_en: date
    paciente_id: str

    @property
    def descripcion(self) -> str:
        """Una linea para el registro. Sin datos clinicos: puede acabar en un
        correo o en la pantalla de bloqueo de un telefono."""
        return f"{self.paciente_id}: evento sin descripcion"


@dataclass(frozen=True, slots=True)
class PlazoVencido(EventoDominio):
    """Una etapa del ciclo supero su plazo.

    Es EL evento del proyecto. La contrarreferencia se documenta al 0.55 % en
    el Peru (estudio DIRIS Lima Norte, 110 de 19 951), asi que esperar a que el
    ciclo se cierre solo es esperar algo que no llega. El unico modo de cerrarlo
    es que el vencimiento avise.
    """

    estado: EstadoCiclo
    dias_transcurridos: int
    dias_de_plazo: int
    destinatario: str = ""

    @property
    def dias_de_retraso(self) -> int:
        return self.dias_transcurridos - self.dias_de_plazo

    @property
    def descripcion(self) -> str:
        return (
            f"{self.paciente_id}: {self.estado.etiqueta} vencido hace "
            f"{self.dias_de_retraso} dias"
        )


@dataclass(frozen=True, slots=True)
class PlazoPorVencer(EventoDominio):
    """Entro en la franja de preaviso: todavia se puede hacer algo.

    Existe separado de `PlazoVencido` porque exigen acciones distintas. Avisar
    solo cuando ya es tarde convierte el sistema en un registro de fracasos.
    """

    estado: EstadoCiclo
    dias_restantes: int
    destinatario: str = ""

    @property
    def descripcion(self) -> str:
        return (
            f"{self.paciente_id}: {self.estado.etiqueta} vence en "
            f"{self.dias_restantes} dias"
        )


@dataclass(frozen=True, slots=True)
class PacienteEntroEnVentana(EventoDominio):
    """Cumplio 14: entra en la cohorte activa y empieza la preparacion."""

    edad: int
    meses_hasta_corte: int

    @property
    def descripcion(self) -> str:
        return (
            f"{self.paciente_id}: entra en ventana de transicion "
            f"({self.meses_hasta_corte} meses hasta el corte)"
        )


@dataclass(frozen=True, slots=True)
class PasaporteEmitido(EventoDominio):
    """Se emitio un Pasaporte. Abre el ciclo de seguimiento."""

    edad_hito: int
    """14, 16 o 17. La version depende de la edad."""

    @property
    def descripcion(self) -> str:
        return f"{self.paciente_id}: Pasaporte v{self.edad_hito} emitido"


@dataclass(frozen=True, slots=True)
class CicloAvanzo(EventoDominio):
    """El ciclo paso al siguiente estado."""

    desde: EstadoCiclo
    hasta: EstadoCiclo

    @property
    def descripcion(self) -> str:
        return f"{self.paciente_id}: {self.desde.etiqueta} -> {self.hasta.etiqueta}"


@dataclass(frozen=True, slots=True)
class CitaConfirmada(EventoDominio):
    """El paciente llego al servicio de adultos.

    `fuente` no es un detalle administrativo: la proporcion entre
    contrarreferencia formal y confirmacion de la familia es, en si misma, un
    hallazgo del piloto.
    """

    fuente: FuenteConfirmacion

    @property
    def descripcion(self) -> str:
        return f"{self.paciente_id}: cita cumplida ({self.fuente.etiqueta})"
