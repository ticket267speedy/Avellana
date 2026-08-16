"""Conciliacion de medicacion: lo que dice el Pasaporte frente a lo que dice el
paciente.

═══════════════════════════════════════════════════════════════════════════════
LAS DOS REGLAS QUE ESTE MODULO EXISTE PARA HACER CUMPLIR
═══════════════════════════════════════════════════════════════════════════════

1. **Lo que declara el paciente NUNCA sobrescribe el Pasaporte.** Genera un
   caso de conciliacion asignado al equipo del INSN. El Pasaporte lo firma un
   medico (regla 4) y una dosis solo entra si aparece literalmente en la fuente
   (regla 8): dejar que una declaracion lo modifique romperia las dos a la vez.

2. **El sistema NUNCA decide cual version es la correcta.** Solo reporta la
   discrepancia. Que un adolescente diga que toma 2 ml y su historia diga 3 no
   significa que uno de los dos mienta —significa que hay que preguntarlo—, y
   ese es exactamente el tipo de decision que no puede tomar un programa.

Por que esto importa mas de lo que parece: hoy nadie coteja. El paciente llega
al hospital de adultos con una lista que sale de su historia pediatrica y otra
que sale de su casa, y la primera vez que alguien nota la diferencia es en la
consulta, si es que la nota. Esto es un mecanismo nuevo, no una pantalla.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from relevo.dominio.entidades.diagnostico import Medicamento
from relevo.dominio.objetos_valor.origen_dato import OrigenDato, TipoDiscrepancia
from relevo.dominio.objetos_valor.responsable import Responsable


@dataclass(frozen=True, slots=True)
class MedicacionDeclarada:
    """Lo que el paciente dice que toma. Su propia voz, sin corregir.

    NO es doble digitacion: este dato no lo tenia nadie mas. Es una de las tres
    puertas legitimas por las que entra informacion clinica al sistema (la
    tercera del principio "Relevo no pide datos, pide decisiones").

    `dosis` es texto libre A PROPOSITO y solo aqui: es lo que el paciente
    escribio, tal cual, y su valor esta justamente en no haberlo normalizado.
    Nunca se copia al Pasaporte sin pasar por una persona.
    """

    nombre: str
    dosis: str | None = None
    frecuencia: str | None = None
    fecha_declaracion: date | None = None
    lo_sigue_tomando: bool = True

    @property
    def origen(self) -> OrigenDato:
        return OrigenDato.INFORMADO_POR_PACIENTE

    def __str__(self) -> str:
        partes = [self.nombre]
        if self.dosis:
            partes.append(self.dosis)
        if self.frecuencia:
            partes.append(self.frecuencia)
        return " · ".join(partes)


class EstadoConciliacion(Enum):
    """En que punto esta la resolucion de una discrepancia."""

    ABIERTO = "abierto"
    EN_REVISION = "en_revision"
    RESUELTO = "resuelto"
    """Una persona la miro y decidio. El sistema nunca llega aqui solo."""

    @property
    def etiqueta(self) -> str:
        return {
            EstadoConciliacion.ABIERTO: "Abierto",
            EstadoConciliacion.EN_REVISION: "En revision",
            EstadoConciliacion.RESUELTO: "Resuelto",
        }[self]


@dataclass(frozen=True, slots=True)
class Discrepancia:
    """Una diferencia concreta entre las dos listas.

    Guarda los dos textos sin elegir entre ellos. Un campo unico "valor
    correcto" seria el sitio donde el sistema tomaria la decision que no le
    corresponde.
    """

    tipo: TipoDiscrepancia
    medicamento: str
    valor_pasaporte: str | None = None
    valor_declarado: str | None = None

    def descripcion(self) -> str:
        """Una linea neutral. Describe, no juzga."""
        if self.tipo is TipoDiscrepancia.FALTA_EN_PASAPORTE:
            return (
                f"{self.medicamento}: el paciente lo declara y el Pasaporte no "
                "lo registra"
            )
        if self.tipo is TipoDiscrepancia.FALTA_EN_DECLARACION:
            return (
                f"{self.medicamento}: el Pasaporte lo registra y el paciente no "
                "lo menciono"
            )
        return (
            f"{self.medicamento}: Pasaporte dice "
            f"'{self.valor_pasaporte or '—'}', el paciente dice "
            f"'{self.valor_declarado or '—'}'"
        )

    def __str__(self) -> str:
        return self.descripcion()


@dataclass
class CasoDeConciliacion:
    """Un cotejo pendiente, asignado a una persona del equipo del INSN.

    Se asigna SIEMPRE a `EQUIPO_INSN` y no al paciente ni al receptor: el
    paciente ya hizo su parte al declarar, y el receptor no tiene acceso a la
    historia pediatrica con la que hay que cotejar. Dejarlo sin dueno seria
    volver al problema que `Responsable` vino a resolver.
    """

    paciente_id: str
    fecha_apertura: date
    discrepancias: tuple[Discrepancia, ...] = ()
    estado: EstadoConciliacion = EstadoConciliacion.ABIERTO
    resuelto_por: str = ""
    fecha_resolucion: date | None = None
    nota_resolucion: str = ""
    """Que decidio la persona. Texto libre porque lo escribe un profesional
    sobre su propia decision, no sobre un dato clinico del paciente."""

    historial_estados: list[tuple[EstadoConciliacion, date]] = field(
        default_factory=list
    )

    @property
    def responsable(self) -> Responsable:
        """Siempre el equipo del INSN. Ver el docstring de la clase."""
        return Responsable.EQUIPO_INSN

    @property
    def esta_abierto(self) -> bool:
        return self.estado is not EstadoConciliacion.RESUELTO

    @property
    def total_discrepancias(self) -> int:
        return len(self.discrepancias)

    def discrepancias_de(self, tipo: TipoDiscrepancia) -> tuple[Discrepancia, ...]:
        return tuple(d for d in self.discrepancias if d.tipo is tipo)

    def tomar(self, fecha: date) -> None:
        """Alguien del equipo se hace cargo."""
        self.estado = EstadoConciliacion.EN_REVISION
        self.historial_estados.append((self.estado, fecha))

    def resolver(self, quien: str, fecha: date, nota: str) -> None:
        """Una persona decide. Es el unico camino a RESUELTO.

        Exige nombre y nota: una conciliacion resuelta sin decir quien ni que
        decidio no se puede auditar, y lo que no se puede auditar en este
        dominio equivale a no haber pasado.
        """
        if not quien.strip():
            raise ValueError(
                "Una conciliacion se resuelve con nombre y apellido. El sistema "
                "no decide cual version es la correcta: decide una persona, y "
                "esa persona queda registrada."
            )
        if not nota.strip():
            raise ValueError(
                "Resolver sin decir que se decidio deja el caso cerrado y la "
                "duda abierta."
            )
        self.estado = EstadoConciliacion.RESUELTO
        self.resuelto_por = quien
        self.fecha_resolucion = fecha
        self.nota_resolucion = nota
        self.historial_estados.append((self.estado, fecha))

    def __str__(self) -> str:
        return (
            f"{self.paciente_id} · {self.total_discrepancias} discrepancias · "
            f"{self.estado.etiqueta} · turno de {self.responsable.etiqueta}"
        )


def medicamento_es_el_mismo(a: str, b: str) -> bool:
    """Si dos nombres se refieren al mismo farmaco, para efectos del cotejo.

    Comparacion deliberadamente tosca —minusculas y sin espacios de sobra— y
    nada mas. No hay normalizacion por principio activo ni distancia de
    edicion: emparejar de mas produciria discrepancias de dosis falsas entre
    dos farmacos distintos, y ese error es mucho peor que reportar de mas.
    Reportar de mas solo cuesta una revision; emparejar mal produce un dato
    clinico equivocado.
    """
    return " ".join(a.lower().split()) == " ".join(b.lower().split())


def es_dosis_equivalente(a: str | None, b: str | None) -> bool:
    """Misma comparacion tosca para dosis. Ninguna aritmetica de unidades.

    Convertir "2 ml" a "2000 mcg" exigiria conocer la concentracion, y
    suponerla seria inventar una dosis — la regla 8, que es la que no se rompe
    nunca. Si los textos difieren, se reporta y decide una persona.
    """
    if a is None or b is None:
        return a == b
    return " ".join(a.lower().split()) == " ".join(b.lower().split())


__all__ = [
    "CasoDeConciliacion",
    "Discrepancia",
    "EstadoConciliacion",
    "Medicamento",
    "MedicacionDeclarada",
    "es_dosis_equivalente",
    "medicamento_es_el_mismo",
]
