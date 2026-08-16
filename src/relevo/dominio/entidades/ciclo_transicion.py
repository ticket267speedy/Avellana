"""El ciclo de la derivacion: de que se prepara el traspaso a que el paciente
llego de verdad al servicio de adultos.

PLAN_TECNICO §7, ampliado a nueve estados por la rubrica del INSN. Los plazos
viven en `config/plazos_ciclo.yaml`; el grafo de estados en
`objetos_valor/estado_ciclo.py`; aqui esta la entidad y su historial.

Por que existe: hoy, al cumplir 18, el paciente simplemente deja de aparecer y
nadie sabe si llego a algun lado. El ciclo es lo que convierte "lo derivamos"
en "sabemos que llego".

Recordatorio del corte etario, que se confunde con facilidad: cumplir 18 no
cierra el ciclo. El ciclo sigue abierto —y debe seguir— hasta confirmar el
destino. Lo que se cierra a los 18 es la atencion pediatrica, no el tramite.
Ver el docstring de `objetos_valor/estado_ciclo.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.objetos_valor.estado_ciclo import (
    ESTADOS_CON_DESTINO_ASEGURADO,
    ESTADOS_LEGADO,
    ETAPAS_DE_TRAMITE,
    TRANSICIONES_PERMITIDAS,
    EstadoCiclo,
    estado_desde_persistido,
    transiciones_desde,
)
from relevo.dominio.objetos_valor.reingreso import (
    AccionCiclo,
    MotivoReingreso,
    Reingreso,
    acciones_permitidas,
)
from relevo.dominio.objetos_valor.responsable import Responsable, responsable_de

__all__ = [
    "AccionCiclo",
    "CicloTransicion",
    "ESTADOS_CON_DESTINO_ASEGURADO",
    "ESTADOS_LEGADO",
    "ETAPAS_DE_TRAMITE",
    "EstadoCiclo",
    "EventoCiclo",
    "FuenteConfirmacion",
    "MotivoReingreso",
    "Reingreso",
    "Responsable",
    "TRANSICIONES_PERMITIDAS",
    "estado_desde_persistido",
    "responsable_de",
    "transiciones_desde",
]


class FuenteConfirmacion(Enum):
    """Como nos enteramos de que el paciente llego a la cita.

    PLAN_TECNICO §7: el estudio de DIRIS Lima Norte documenta 110
    contrarreferencias sobre 19 951 referencias — 0.55 %. La via formal no
    funciona empiricamente. Esperar la contrarreferencia para cerrar el ciclo
    es esperar algo que en 99 de cada 100 casos no llega.

    Por eso la confirmacion admite tres fuentes y el indicador se desagrega:
    la proporcion de cada una es en si misma un hallazgo del piloto.
    """

    CONTRARREFERENCIA = "formal"
    CONFIRMACION_FAMILIA = "pragmatica"
    CONFIRMACION_RECEPTOR = "receptor"
    """El profesional del receptor lo marca en su bandeja.

    Es nueva respecto del modelo de seis estados y es la via que el sistema
    hace posible: antes, entre la contrarreferencia formal (0.55 %) y llamar a
    la familia no habia nada. Un clic del receptor en su propia pantalla es la
    confirmacion mas barata y mas fiable de las tres."""

    @property
    def etiqueta(self) -> str:
        return {
            FuenteConfirmacion.CONTRARREFERENCIA: "Contrarreferencia formal",
            FuenteConfirmacion.CONFIRMACION_FAMILIA: "Confirmación de la familia",
            FuenteConfirmacion.CONFIRMACION_RECEPTOR: "Confirmación del receptor",
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
    """Solo tiene sentido al entrar a PRIMERA_ATENCION_CONFIRMADA."""

    motivo_reingreso: MotivoReingreso | None = None
    """Solo tiene sentido al entrar a REINGRESO."""

    nota: str = ""
    """Nota administrativa. NUNCA contenido clinico: el dato clinico entra por
    el extractor con verificacion y firma, no por un campo de texto libre
    (principio de cero doble digitacion)."""

    def __str__(self) -> str:
        via = f" ({self.fuente_confirmacion.etiqueta})" if self.fuente_confirmacion else ""
        if self.motivo_reingreso is not None:
            via = f" ({self.motivo_reingreso.etiqueta})"
        return f"{self.fecha.isoformat()} · {self.estado.etiqueta}{via}"


@dataclass
class CicloTransicion:
    """El seguimiento de un paciente desde la preparacion hasta la confirmacion."""

    paciente_id: str
    fecha_inicio: date
    """Fecha de apertura del ciclo. El estado PREPARACION se da por hecho."""

    fecha_nacimiento: date | None = None
    """La del paciente. El ciclo la lleva porque el corte etario es una regla
    DEL CICLO, no solo del paciente: `acciones_permitidas` y
    `evaluar_corte_etario` la necesitan, y el profesional del receptor ve el
    ciclo sin tener acceso al expediente completo del paciente.

    Admite None para no romper los ciclos ya persistidos sin ella. Donde falta,
    el sistema se pone en el peor caso: sin poder demostrar que el paciente es
    menor de 18, las acciones clinicas quedan prohibidas."""

    destino_propuesto: str = ""
    """Servicio de adultos propuesto. PROPUESTO, no asignado: el sistema
    propone y una persona firma (PLAN_TECNICO §13)."""

    establecimiento_receptor: str = ""
    """A que establecimiento se dirigio la referencia.

    Es la clave del aislamiento por rol: un profesional receptor ve unicamente
    las referencias dirigidas a SU establecimiento. Sin este campo, darle una
    bandeja al receptor seria darle la cohorte pediatrica entera del INSN."""

    servicio_asignado: str = ""
    """Servicio y medico que el receptor asigno al aceptar. Se llena en
    ACEPTADO_CON_SERVICIO: aceptar sin servicio concreto es una carta amable
    que no le da cita a nadie."""

    fecha_cita: date | None = None
    """Fecha de la cita en el servicio de adultos, cuando se programa.

    El plazo de CITA_PROGRAMADA se cuenta desde aqui y no desde la fecha de
    programacion: una cita programada a tres meses no esta vencida a los siete
    dias de haberse programado."""

    historial: list[EventoCiclo] = field(default_factory=list)
    reingresos: list[Reingreso] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.historial:
            self.historial = [
                EventoCiclo(
                    estado=EstadoCiclo.PREPARACION,
                    fecha=self.fecha_inicio,
                    nota="Apertura del ciclo",
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
    def responsable(self) -> Responsable:
        """¿Quien tiene el turno ahora? La pregunta central de la interfaz."""
        return responsable_de(self.estado)

    @property
    def esta_confirmado(self) -> bool:
        """El paciente llego al servicio de adultos y fue atendido."""
        return self.estado is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA

    @property
    def esta_cerrado(self) -> bool:
        """Termino bien y sin nada pendiente.

        Ojo: no es inmutable. Un ciclo cerrado puede reabrirse a REINGRESO si
        el seguimiento no continua.
        """
        return self.estado.es_final

    @property
    def tiene_destino_asegurado(self) -> bool:
        """True si cumplir 18 ya no supone quedarse sin ningun servicio.

        Es la pregunta que define la metrica estrella de fracaso. Ver
        `servicios/corte_etario.py`.
        """
        return self.estado in ESTADOS_CON_DESTINO_ASEGURADO

    @property
    def fuente_de_confirmacion(self) -> FuenteConfirmacion | None:
        """Como se confirmo la llegada, si se confirmo. La ultima que hubo."""
        for evento in reversed(self.historial):
            if evento.estado is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA:
                return evento.fuente_confirmacion
        return None

    @property
    def transiciones_posibles(self) -> frozenset[EstadoCiclo]:
        """A donde puede ir el ciclo desde donde esta."""
        return transiciones_desde(self.estado)

    @property
    def siguiente_estado(self) -> EstadoCiclo | None:
        """El avance natural de la linea de tramite, si lo hay.

        Existe para la barra de demo y para las pantallas de un solo boton. El
        grafo real tiene ramas: quien necesite todas usa `transiciones_posibles`.
        """
        orden = self.estado.orden
        if orden < 0:
            return None
        siguientes = [
            e for e in self.transiciones_posibles if e.orden == orden + 1
        ]
        return siguientes[0] if siguientes else None

    @property
    def reingresos_sin_reclasificar(self) -> tuple[Reingreso, ...]:
        """Reapertura pendiente de decidir a que estado vuelve el caso.

        REINGRESO es transitorio: esta lista es la cola de trabajo que evita
        que se convierta en un cajon donde los casos dificiles van a morir.
        """
        return tuple(r for r in self.reingresos if not r.esta_reclasificado)

    def acciones_permitidas(self, hoy: date) -> frozenset[AccionCiclo]:
        """Que se puede hacer con este ciclo hoy.

        Con el paciente >= 18, solo acciones administrativas. La regla la
        aplica `objetos_valor/reingreso.py`, no esta entidad, para que viva en
        un solo sitio y un solo test la vigile.
        """
        return acciones_permitidas(self, hoy)

    # ── Avance ───────────────────────────────────────────────────────────────

    def avanzar(
        self,
        estado: EstadoCiclo,
        fecha: date,
        registrado_por: str = "",
        fuente_confirmacion: FuenteConfirmacion | None = None,
        motivo_reingreso: MotivoReingreso | None = None,
        nota: str = "",
    ) -> EventoCiclo:
        """Registra el paso a otro estado.

        Rechaza cualquier transicion que no este en el grafo explicito, y
        rechaza una fecha anterior al ultimo evento: un historial que no avanza
        en el tiempo no es un historial.
        """
        permitidas = self.transiciones_posibles
        if estado not in permitidas:
            destinos = ", ".join(sorted(e.etiqueta for e in permitidas))
            raise TransicionInvalida(
                f"Desde {self.estado.etiqueta} no se puede pasar a "
                f"{estado.etiqueta}. Destinos permitidos: {destinos}."
            )
        if fecha < self.fecha_estado_actual:
            raise TransicionInvalida(
                f"La fecha {fecha.isoformat()} es anterior al ultimo evento "
                f"({self.fecha_estado_actual.isoformat()})."
            )
        if estado is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA and fuente_confirmacion is None:
            raise TransicionInvalida(
                "Confirmar una primera atencion exige decir como se supo: "
                "contrarreferencia formal, confirmacion del receptor o "
                "confirmacion de la familia. La proporcion entre las tres es "
                "un hallazgo del piloto."
            )
        if estado is EstadoCiclo.REINGRESO and motivo_reingreso is None:
            raise TransicionInvalida(
                "Reabrir un ciclo exige decir por que. Un reingreso sin motivo "
                "no se puede contar, y contarlos por motivo es lo que "
                "distingue una inasistencia de un destino que no funciono."
            )

        evento = EventoCiclo(
            estado=estado,
            fecha=fecha,
            registrado_por=registrado_por,
            fuente_confirmacion=fuente_confirmacion,
            motivo_reingreso=motivo_reingreso,
            nota=nota,
        )
        self.historial.append(evento)

        if estado is EstadoCiclo.REINGRESO and motivo_reingreso is not None:
            self.reingresos.append(
                Reingreso(
                    motivo=motivo_reingreso,
                    fecha=fecha,
                    registrado_por=registrado_por,
                    nota_administrativa=nota,
                )
            )
        if estado is EstadoCiclo.CITA_PROGRAMADA and self.fecha_cita is None:
            # Respaldo: si nadie dijo para cuando es la cita, se asume el dia
            # del registro. Es conservador —adelanta el vencimiento— y hace
            # visible el dato que falta.
            self.fecha_cita = fecha
        return evento

    def reclasificar(
        self, estado: EstadoCiclo, fecha: date, registrado_por: str = ""
    ) -> EventoCiclo:
        """Saca el ciclo de REINGRESO hacia un estado de tramite.

        Metodo aparte de `avanzar` porque hace dos cosas que `avanzar` no hace:
        exige estar en REINGRESO y cierra el registro de reapertura pendiente.
        """
        if self.estado is not EstadoCiclo.REINGRESO:
            raise TransicionInvalida(
                f"Solo se reclasifica un ciclo en {EstadoCiclo.REINGRESO.etiqueta}; "
                f"este esta en {self.estado.etiqueta}."
            )
        evento = self.avanzar(estado, fecha, registrado_por=registrado_por)
        pendientes = self.reingresos_sin_reclasificar
        if pendientes:
            ultimo = self.reingresos.index(pendientes[-1])
            # Los Reingreso son inmutables: se sustituye por una copia cerrada.
            anterior = self.reingresos[ultimo]
            self.reingresos[ultimo] = Reingreso(
                motivo=anterior.motivo,
                fecha=anterior.fecha,
                registrado_por=anterior.registrado_por,
                reclasificado_a=estado,
                nota_administrativa=anterior.nota_administrativa,
            )
        return evento

    def dias_en_estado_actual(self, hoy: date) -> int:
        """Cuanto lleva parado aqui. Es el numerador del control de plazos."""
        referencia = self.fecha_estado_actual
        if self.estado is EstadoCiclo.CITA_PROGRAMADA and self.fecha_cita is not None:
            # El plazo de la cita se cuenta desde la fecha de la cita.
            referencia = self.fecha_cita
        return (hoy - referencia).days

    def __str__(self) -> str:
        return (
            f"{self.paciente_id} · {self.estado.etiqueta} desde "
            f"{self.fecha_estado_actual.isoformat()} · turno de "
            f"{self.responsable.etiqueta}"
        )
