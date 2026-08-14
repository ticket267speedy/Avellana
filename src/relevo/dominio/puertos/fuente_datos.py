"""Puerto de entrada de datos clinicos.

Este es EL puerto del pitch. La promesa ante el jurado es "el nucleo no cambia,
solo se cambia el adaptador de entrada segun el sistema del hospital". Este
archivo es esa promesa escrita: hoy la implementa `csv_sintetico.py`; el dia
que se sepa que hay del otro lado, la implementa `sisgalen_*.py` y no se toca
ni una linea del dominio.

Toda implementacion es de SOLO LECTURA. Escribir en el sistema del hospital
rompe la promesa central del proyecto (PLAN_TECNICO §13).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from relevo.dominio.entidades.paciente import Paciente


@dataclass(frozen=True, slots=True)
class InformeCarga:
    """Que se pudo leer y que no.

    Existe porque una carga silenciosa que descarta el 30 % de los registros es
    peor que una que falla: nadie se entera. Los motivos se muestran en la
    interfaz tal cual.
    """

    leidos: int
    cargados: int
    descartados: tuple[str, ...] = field(default_factory=tuple)
    """Un motivo por registro descartado, en castellano llano."""

    @property
    def hubo_perdida(self) -> bool:
        return self.cargados < self.leidos

    def __str__(self) -> str:
        return f"{self.cargados}/{self.leidos} registros cargados"


class FuenteDatosClinicos(ABC):
    """De donde salen los pacientes. Solo lectura, siempre."""

    @abstractmethod
    def leer_pacientes(self) -> list[Paciente]:
        """Todos los pacientes disponibles en la fuente."""

    @abstractmethod
    def leer_paciente(self, paciente_id: str) -> Paciente | None:
        ...

    @abstractmethod
    def ultimo_informe(self) -> InformeCarga | None:
        """El resultado de la ultima lectura. None si no se leyo nada aun."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Como se llama esta fuente en la interfaz: 'CSV sintetico',
        'SisGalenPlus'. Se muestra en pantalla: quien mira los datos tiene
        derecho a saber de donde vienen."""

    @property
    @abstractmethod
    def es_sintetica(self) -> bool:
        """True si los datos son inventados.

        Gobierna la marca de agua 'DATOS SINTETICOS — DEMO' de los documentos.
        Mientras dure el hackathon es True en todos los adaptadores que
        existen.
        """


class DirectorioDestinos(ABC):
    """Correspondencia entre diagnostico y servicio de adultos que corresponde.

    PENDIENTE MENTOR: el contenido del directorio (`config/destinos.csv`) lo
    define el INSN. El sistema PROPONE un destino; la asignacion la firma una
    persona. Automatizarla es clinica y legalmente inaceptable
    (PLAN_TECNICO §13).
    """

    @abstractmethod
    def proponer(self, paciente: Paciente, hoy: date) -> tuple[str, ...]:
        """Destinos candidatos, del mas al menos probable. Vacio si no hay
        correspondencia: es preferible no proponer nada a proponer cualquier
        cosa."""
