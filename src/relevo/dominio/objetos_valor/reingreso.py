"""Reingreso al ciclo, y el limite que ninguna reapertura puede cruzar.

═══════════════════════════════════════════════════════════════════════════════
LA REGLA QUE ESTE ARCHIVO HACE CUMPLIR
═══════════════════════════════════════════════════════════════════════════════

REINGRESO es un estado del CICLO DE TRANSICION, no un reingreso al INSN. El
ciclo es un artefacto administrativo que vive en Relevo. Que se reabra no
implica —ni puede implicar— ninguna atencion clinica pediatrica.

Con el paciente >= 18 anios, un ciclo reabierto habilita SOLO acciones
administrativas: reenviar el Pasaporte, contactar al receptor, contactar a la
familia, reclasificar el ciclo. Ninguna accion clinica del INSN es posible,
porque **el INSN no atiende a mayores de 18 bajo ninguna circunstancia**
(regla institucional, `CLAUDE.md`).

Eso esta impedido por codigo, no solo documentado: `acciones_permitidas()` es
la puerta, y `tests/dominio/test_reingreso_no_reabre_atencion.py` la vigila.

# TODO: confirmar con mentor — si el equipo de transicion del INSN esta
# facultado para gestion administrativa de un ex-paciente mayor de 18 anios.
# Provisional: se asume que si, porque la NT 018-MINSA obliga a la
# contrarreferencia y esa obligacion no caduca con la edad del paciente.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from relevo.dominio.objetos_valor.estado_ciclo import EstadoCiclo
from relevo.dominio.objetos_valor.ventana_transicion import EDAD_CORTE, edad_en


class MotivoReingreso(Enum):
    """Por que se reabre un ciclo. Cada motivo pide una respuesta distinta.

    Guardar el motivo y no un booleano `reabierto` es lo que permite contar
    despues cuantos reingresos fueron por inasistencia y cuantos por un destino
    que no funciono. Son dos problemas distintos del sistema de salud y piden
    dos intervenciones distintas.
    """

    REAPARECE_TRAS_PERDIDA = "reaparece_tras_perdida"
    """Se le habia perdido el rastro y volvio a aparecer. El mejor caso: el
    paciente sigue queriendo continuidad."""

    NO_ASISTIO_A_PRIMERA_CITA = "no_asistio_a_primera_cita"
    """Habia cita y no llego. Hay que averiguar por que antes de reprogramar:
    reprogramar sin saber suele producir una segunda inasistencia."""

    ATENDIDO_SIN_CONTINUIDAD = "atendido_sin_continuidad"
    """Lo atendieron una vez y ahi se acabo. El caso que mas se parece al
    fracaso silencioso: en el papel figura como exito."""

    CAMBIO_DE_DESTINO = "cambio_de_destino"
    """El destino asignado dejo de servir — mudanza, cierre de servicio, cambio
    de regimen de seguro. El ciclo se rehace hacia otro receptor."""

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS_MOTIVO[self]

    def __str__(self) -> str:
        return self.etiqueta


_ETIQUETAS_MOTIVO: dict[MotivoReingreso, str] = {
    MotivoReingreso.REAPARECE_TRAS_PERDIDA: "Reaparece tras pérdida de seguimiento",
    MotivoReingreso.NO_ASISTIO_A_PRIMERA_CITA: "No asistió a la primera cita",
    MotivoReingreso.ATENDIDO_SIN_CONTINUIDAD: "Atendido una vez, sin continuidad",
    MotivoReingreso.CAMBIO_DE_DESTINO: "Cambio de destino",
}


class AccionCiclo(Enum):
    """Todo lo que se puede hacer sobre un ciclo.

    Estan juntas a proposito, clinicas y administrativas en el mismo enum, para
    que la separacion sea una propiedad comprobable (`es_clinica`) y no una
    convencion de nombres que se olvida al anadir la siguiente.
    """

    # ── Administrativas ──────────────────────────────────────────────────────
    # Ninguna implica atender al paciente. Todas siguen disponibles despues de
    # los 18 porque la obligacion de cerrar la derivacion no caduca con la edad.
    REENVIAR_PASAPORTE = "reenviar_pasaporte"
    """Vuelve a enviar un documento YA firmado. No genera contenido clinico
    nuevo: por eso es administrativa."""

    CONTACTAR_RECEPTOR = "contactar_receptor"
    CONTACTAR_FAMILIA = "contactar_familia"
    REGISTRAR_REINGRESO = "registrar_reingreso"
    RECLASIFICAR_CICLO = "reclasificar_ciclo"
    AVANZAR_TRAMITE = "avanzar_tramite"
    """Registrar que el tramite avanzo. Es anotar un hecho administrativo que
    ocurrio fuera del INSN, tipicamente en el hospital receptor."""

    REGISTRAR_PERDIDA = "registrar_perdida"

    # ── Clinicas del INSN ────────────────────────────────────────────────────
    # Todas exigen que un profesional del INSN vea al paciente o produzca
    # contenido clinico nuevo sobre el. Imposibles a partir de los 18.
    PROGRAMAR_CONSULTA_INSN = "programar_consulta_insn"
    EMITIR_PASAPORTE = "emitir_pasaporte"
    """Emitir uno NUEVO exige que un medico del INSN revise y firme, y firmar
    sobre un paciente al que la institucion no puede atender no es posible.
    Distinto de reenviar uno ya firmado."""

    ACTUALIZAR_DIAGNOSTICO = "actualizar_diagnostico"
    AJUSTAR_TRATAMIENTO = "ajustar_tratamiento"
    REGISTRAR_EVALUACION_CLINICA = "registrar_evaluacion_clinica"

    @property
    def es_clinica(self) -> bool:
        """True si exige atencion o juicio clinico del INSN sobre el paciente."""
        return self in _ACCIONES_CLINICAS_INSN

    @property
    def es_administrativa(self) -> bool:
        return not self.es_clinica

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS_ACCION[self]


_ACCIONES_CLINICAS_INSN: frozenset[AccionCiclo] = frozenset(
    {
        AccionCiclo.PROGRAMAR_CONSULTA_INSN,
        AccionCiclo.EMITIR_PASAPORTE,
        AccionCiclo.ACTUALIZAR_DIAGNOSTICO,
        AccionCiclo.AJUSTAR_TRATAMIENTO,
        AccionCiclo.REGISTRAR_EVALUACION_CLINICA,
    }
)

ACCIONES_ADMINISTRATIVAS: frozenset[AccionCiclo] = frozenset(
    a for a in AccionCiclo if a not in _ACCIONES_CLINICAS_INSN
)

_ETIQUETAS_ACCION: dict[AccionCiclo, str] = {
    AccionCiclo.REENVIAR_PASAPORTE: "Reenviar el Pasaporte ya firmado",
    AccionCiclo.CONTACTAR_RECEPTOR: "Contactar al hospital receptor",
    AccionCiclo.CONTACTAR_FAMILIA: "Contactar a la familia",
    AccionCiclo.REGISTRAR_REINGRESO: "Registrar reingreso al ciclo",
    AccionCiclo.RECLASIFICAR_CICLO: "Reclasificar el ciclo",
    AccionCiclo.AVANZAR_TRAMITE: "Registrar avance del trámite",
    AccionCiclo.REGISTRAR_PERDIDA: "Registrar pérdida de seguimiento",
    AccionCiclo.PROGRAMAR_CONSULTA_INSN: "Programar consulta en el INSN",
    AccionCiclo.EMITIR_PASAPORTE: "Emitir un Pasaporte nuevo",
    AccionCiclo.ACTUALIZAR_DIAGNOSTICO: "Actualizar diagnóstico",
    AccionCiclo.AJUSTAR_TRATAMIENTO: "Ajustar tratamiento",
    AccionCiclo.REGISTRAR_EVALUACION_CLINICA: "Registrar evaluación clínica",
}


@dataclass(frozen=True, slots=True)
class Reingreso:
    """El registro de una reapertura. Inmutable, como todo el historial.

    `reclasificado_a` empieza en None a proposito: un reingreso sin
    reclasificar es una tarea pendiente del equipo, y tiene que poder contarse
    como tal. REINGRESO es transitorio; quedarse ahi es el fallo.
    """

    motivo: MotivoReingreso
    fecha: date
    registrado_por: str = ""
    reclasificado_a: EstadoCiclo | None = None
    nota_administrativa: str = ""
    """Nota EXPLICITAMENTE no clinica. No admite diagnostico, dosis ni
    resultado: para eso esta el Pasaporte, que un medico firma."""

    def __post_init__(self) -> None:
        if self.reclasificado_a is not None and not self.reclasificado_a.es_de_tramite:
            raise ValueError(
                "Un reingreso se reclasifica a uno de los siete estados de "
                f"tramite, no a {self.reclasificado_a.name}. Reclasificar a "
                "REINGRESO o a PERDIDA_DE_SEGUIMIENTO deja el ciclo en el "
                "mismo limbo del que se queria sacar."
            )

    @property
    def esta_reclasificado(self) -> bool:
        return self.reclasificado_a is not None


def acciones_permitidas(ciclo: object, hoy: date) -> frozenset[AccionCiclo]:
    """Con el paciente >= 18, un ciclo reabierto solo habilita acciones
    administrativas. Ninguna accion clinica del INSN es posible: el INSN
    no atiende mayores de 18 bajo ninguna circunstancia (CLAUDE.md).

    Recibe el ciclo como `object` y lee sus atributos por nombre para no crear
    un import circular con `entidades/ciclo_transicion.py`, que ya importa este
    modulo. Es el unico sitio del dominio donde se hace, y esta acotado a dos
    atributos.

    Regla de seguridad: si no se conoce la fecha de nacimiento, se asume lo
    peor y se niegan las acciones clinicas. Una edad desconocida no es una edad
    valida, y el corte etario es demasiado duro para resolverlo por optimismo.
    """
    fecha_nacimiento = getattr(ciclo, "fecha_nacimiento", None)
    estado = getattr(ciclo, "estado", None)

    if fecha_nacimiento is None:
        # Sin fecha de nacimiento no se puede demostrar que el paciente es
        # menor de 18. Solo administrativas.
        return _filtrar_por_estado(ACCIONES_ADMINISTRATIVAS, estado)

    if edad_en(fecha_nacimiento, hoy) >= EDAD_CORTE:
        return _filtrar_por_estado(ACCIONES_ADMINISTRATIVAS, estado)

    # Menor de 18: sigue siendo paciente del INSN y todo esta disponible.
    return _filtrar_por_estado(frozenset(AccionCiclo), estado)


def _filtrar_por_estado(
    candidatas: frozenset[AccionCiclo], estado: object
) -> frozenset[AccionCiclo]:
    """Quita las acciones que no tienen sentido en el estado en que esta.

    Es una restriccion de coherencia, no de seguridad: la puerta del corte
    etario ya se aplico antes de llamar aqui. Se mantiene separada para que
    nadie confunda las dos y relaje la primera al tocar la segunda.
    """
    if not isinstance(estado, EstadoCiclo):
        return candidatas

    fuera: set[AccionCiclo] = set()
    if estado is not EstadoCiclo.REINGRESO:
        fuera.add(AccionCiclo.RECLASIFICAR_CICLO)
    if estado is EstadoCiclo.PERDIDA_DE_SEGUIMIENTO:
        # Ya esta perdido: volver a registrarlo no anade informacion.
        fuera.add(AccionCiclo.REGISTRAR_PERDIDA)
    if estado.es_final:
        fuera.add(AccionCiclo.AVANZAR_TRAMITE)
    return frozenset(candidatas - fuera)
