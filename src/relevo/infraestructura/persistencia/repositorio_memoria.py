"""Repositorios en memoria. Implementan los puertos de persistencia.

Por que esto y no SQLite todavia: para la demo no hace falta persistencia entre
corridas — el proceso nocturno regenera la cohorte entera — y los mapeadores
ORM <-> dominio son el trabajo mas tedioso y menos diferenciador del proyecto.
La arquitectura hexagonal existe justamente para poder aplazar esta decision.

Cuando SQLite entre, sera un reemplazo directo: el resto del sistema no se
entera porque habla con el puerto, no con esta clase. Esa afirmacion es
demostrable, y es la que se responde si el jurado pregunta por persistencia.
"""

from __future__ import annotations

from datetime import date

from relevo.dominio.entidades.ciclo_transicion import CicloTransicion, EstadoCiclo
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import (
    EstadoPasaporte,
    Pasaporte,
    VersionPasaporte,
)
from relevo.dominio.objetos_valor.ventana_transicion import Cohorte
from relevo.dominio.puertos.repositorios import (
    RepositorioCiclos,
    RepositorioPacientes,
    RepositorioPasaportes,
)


class RepositorioPacientesMemoria(RepositorioPacientes):
    def __init__(self, pacientes: list[Paciente] | None = None) -> None:
        self._por_id: dict[str, Paciente] = {p.id: p for p in (pacientes or [])}

    def obtener(self, paciente_id: str) -> Paciente | None:
        return self._por_id.get(paciente_id)

    def guardar(self, paciente: Paciente) -> None:
        self._por_id[paciente.id] = paciente

    def listar_todos(self) -> list[Paciente]:
        return list(self._por_id.values())

    def listar_por_cohorte(self, cohorte: Cohorte, hoy: date) -> list[Paciente]:
        return [p for p in self._por_id.values() if p.cohorte(hoy) is cohorte]


class RepositorioCiclosMemoria(RepositorioCiclos):
    def __init__(self) -> None:
        self._por_paciente: dict[str, CicloTransicion] = {}

    def obtener_por_paciente(self, paciente_id: str) -> CicloTransicion | None:
        return self._por_paciente.get(paciente_id)

    def guardar(self, ciclo: CicloTransicion) -> None:
        self._por_paciente[ciclo.paciente_id] = ciclo

    def listar_abiertos(self) -> list[CicloTransicion]:
        return [c for c in self._por_paciente.values() if not c.esta_cerrado]

    def listar_por_estado(self, estado: EstadoCiclo) -> list[CicloTransicion]:
        return [c for c in self._por_paciente.values() if c.estado is estado]


class RepositorioPasaportesMemoria(RepositorioPasaportes):
    def __init__(self) -> None:
        self._por_paciente: dict[str, list[Pasaporte]] = {}

    def guardar(self, pasaporte: Pasaporte) -> None:
        self._por_paciente.setdefault(pasaporte.paciente_id, []).append(pasaporte)

    def listar_por_paciente(self, paciente_id: str) -> list[Pasaporte]:
        return list(self._por_paciente.get(paciente_id, []))

    def obtener_vigente(
        self, paciente_id: str, version: VersionPasaporte
    ) -> Pasaporte | None:
        candidatos = [
            p
            for p in self._por_paciente.get(paciente_id, [])
            if p.version is version and p.estado is not EstadoPasaporte.ANULADO
        ]
        return candidatos[-1] if candidatos else None
