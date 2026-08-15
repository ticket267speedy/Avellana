"""Caso de uso: detectar que ciclos se estan quedando atras.

Es la mitad que faltaba de B4. La maquina de plazos ya existia y estaba bien
calibrada con el dato peruano; lo que no existia era nadie que la corriera y
convirtiera su salida en avisos. Sin esto, para enterarse de un vencimiento
habia que abrir una pantalla y acordarse de mirar.

Solo importa `dominio`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from relevo.dominio.entidades.ciclo_transicion import CicloTransicion
from relevo.dominio.eventos import EventoDominio, PlazoPorVencer, PlazoVencido
from relevo.dominio.puertos.repositorios import RepositorioCiclos
from relevo.dominio.servicios.maquina_ciclo import (
    EvaluacionPlazo,
    MaquinaCiclo,
    SituacionPlazo,
)


@dataclass(frozen=True, slots=True)
class ResultadoVencimientos:
    """Lo que encontro la pasada de hoy."""

    fecha: date
    eventos: tuple[EventoDominio, ...] = field(default_factory=tuple)
    evaluaciones: tuple[EvaluacionPlazo, ...] = field(default_factory=tuple)
    ciclos_revisados: int = 0

    @property
    def vencidos(self) -> tuple[PlazoVencido, ...]:
        return tuple(e for e in self.eventos if isinstance(e, PlazoVencido))

    @property
    def por_vencer(self) -> tuple[PlazoPorVencer, ...]:
        return tuple(e for e in self.eventos if isinstance(e, PlazoPorVencer))

    @property
    def hay_algo_que_avisar(self) -> bool:
        """Si sale falso, NO se manda correo.

        PLAN_TECNICO §10: un aviso que llega siempre deja de leerse. El silencio
        es informacion — significa que no hay nada parado.
        """
        return bool(self.eventos)


class EvaluarVencimientos:
    """Recorre los ciclos abiertos y devuelve lo que requiere accion.

    No modifica nada: evaluar plazos es una lectura. Avanzar un ciclo es un
    hecho que alguien registra, y mezclar las dos cosas haria que consultar el
    estado tuviera efectos.
    """

    def __init__(self, repositorio: RepositorioCiclos, maquina: MaquinaCiclo) -> None:
        self._repositorio = repositorio
        self._maquina = maquina

    def ejecutar(
        self, hoy: date, destinatario: str = "", ciclos: Iterable[CicloTransicion] | None = None
    ) -> ResultadoVencimientos:
        """`ciclos` permite pasar una coleccion concreta; por defecto, los abiertos."""
        pendientes = list(ciclos) if ciclos is not None else self._repositorio.listar_abiertos()
        evaluaciones = self._maquina.evaluar_todos(pendientes, hoy)

        eventos: list[EventoDominio] = []
        for ev in evaluaciones:
            if ev.situacion is SituacionPlazo.VENCIDO and ev.plazo_dias is not None:
                eventos.append(
                    PlazoVencido(
                        ocurrido_en=hoy,
                        paciente_id=ev.paciente_id,
                        estado=ev.estado,
                        dias_transcurridos=ev.dias_transcurridos,
                        dias_de_plazo=ev.plazo_dias,
                        destinatario=destinatario,
                    )
                )
            elif ev.situacion is SituacionPlazo.POR_VENCER:
                eventos.append(
                    PlazoPorVencer(
                        ocurrido_en=hoy,
                        paciente_id=ev.paciente_id,
                        estado=ev.estado,
                        dias_restantes=ev.dias_restantes or 0,
                        destinatario=destinatario,
                    )
                )

        return ResultadoVencimientos(
            fecha=hoy,
            eventos=tuple(eventos),
            evaluaciones=tuple(evaluaciones),
            ciclos_revisados=len(pendientes),
        )
