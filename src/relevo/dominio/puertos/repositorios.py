"""Puertos de persistencia.

El dominio declara QUE necesita guardar y leer; no sabe donde. SQLite,
PostgreSQL o una lista en memoria son detalles del adaptador.

Solo `abc` y libreria estandar: la regla de dependencia no admite excepciones
ni siquiera en las interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from relevo.dominio.entidades.ciclo_transicion import CicloTransicion, EstadoCiclo
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import Pasaporte, VersionPasaporte
from relevo.dominio.objetos_valor.ventana_transicion import Cohorte


class RepositorioPacientes(ABC):
    """Lectura y escritura de pacientes."""

    @abstractmethod
    def obtener(self, paciente_id: str) -> Paciente | None:
        """None si no existe. No se lanza excepcion: no encontrar a alguien es
        un resultado posible, no un error."""

    @abstractmethod
    def guardar(self, paciente: Paciente) -> None:
        """Alta o actualizacion, segun exista el id."""

    @abstractmethod
    def listar_todos(self) -> list[Paciente]:
        ...

    @abstractmethod
    def listar_por_cohorte(self, cohorte: Cohorte, hoy: date) -> list[Paciente]:
        """La cohorte depende de la fecha, asi que `hoy` es parte de la consulta.

        Un adaptador que la calcule con el reloj del sistema rompe la
        posibilidad de simular el paso del tiempo, que es como se prueba todo
        este dominio.
        """


class RepositorioCiclos(ABC):
    """Lectura y escritura del seguimiento de derivaciones."""

    @abstractmethod
    def obtener_por_paciente(self, paciente_id: str) -> CicloTransicion | None:
        ...

    @abstractmethod
    def guardar(self, ciclo: CicloTransicion) -> None:
        ...

    @abstractmethod
    def listar_abiertos(self) -> list[CicloTransicion]:
        """Los que aun no llegaron a contrarreferencia.

        Incluye los ya confirmados por la familia: el ciclo sigue formalmente
        abierto aunque para el proyecto la pregunta ya este respondida.
        """

    @abstractmethod
    def listar_por_estado(self, estado: EstadoCiclo) -> list[CicloTransicion]:
        ...


class RepositorioPasaportes(ABC):
    """Los documentos emitidos, con su estado de firma."""

    @abstractmethod
    def guardar(self, pasaporte: Pasaporte) -> None:
        ...

    @abstractmethod
    def listar_por_paciente(self, paciente_id: str) -> list[Pasaporte]:
        """Todos los emitidos, en orden de emision. Un paciente acumula hasta
        tres a lo largo de la ventana."""

    @abstractmethod
    def obtener_vigente(
        self, paciente_id: str, version: VersionPasaporte
    ) -> Pasaporte | None:
        """El ultimo no anulado de esa version, si existe."""
