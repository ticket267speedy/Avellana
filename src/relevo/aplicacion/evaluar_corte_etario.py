"""Caso de uso: la metrica estrella. Cuantos se quedan sin nada al cumplir 18.

Va arriba de todo en el radar. Cualquier otra cifra del sistema —Pasaportes
emitidos, referencias enviadas— mide actividad; esta mide el dano que el
proyecto existe para evitar.

Importa solo `dominio`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from relevo.dominio.entidades.ciclo_transicion import CicloTransicion
from relevo.dominio.servicios.corte_etario import (
    DIAS_HORIZONTE_RIESGO,
    CumplioDieciochoSinDestino,
    MetricaCorteEtario,
    dias_para_corte,
    en_riesgo_de_corte,
    fracasos,
    medir_corte_etario,
)


@dataclass(frozen=True, slots=True)
class FilaDeRiesgo:
    """Un paciente en riesgo, con lo justo para poder llamarlo hoy.

    Sin datos clinicos: esta lista se mira en una pantalla compartida y se
    imprime. Lleva identificador, dias que quedan y de quien es el turno — que
    es todo lo que hace falta para actuar.
    """

    paciente_id: str
    dias_para_corte: int
    estado: str
    responsable: str

    @property
    def es_urgente(self) -> bool:
        """Menos de 30 dias. A esa altura una referencia nueva ya no llega."""
        return self.dias_para_corte < 30

    def linea(self) -> str:
        return (
            f"{self.paciente_id}: cumple 18 en {self.dias_para_corte} dias · "
            f"{self.estado} · turno de {self.responsable}"
        )


@dataclass(frozen=True, slots=True)
class ResultadoCorteEtario:
    """La metrica agregada mas las dos listas nominales.

    Las listas van con la metrica y no aparte porque un numero agregado no
    permite hacer nada: para llamar a alguien hace falta saber a quien.
    """

    metrica: MetricaCorteEtario
    en_riesgo: tuple[FilaDeRiesgo, ...]
    consumados: tuple[CumplioDieciochoSinDestino, ...]
    horizonte_dias: int = DIAS_HORIZONTE_RIESGO

    @property
    def titular(self) -> str:
        return self.metrica.titular()

    @property
    def hay_algo_que_hacer(self) -> bool:
        return self.metrica.hay_algo_que_hacer


@dataclass(frozen=True, slots=True)
class EvaluarCorteEtario:
    """Recorre la cohorte y produce la cifra que abre el radar."""

    def ejecutar(
        self, ciclos: Iterable[CicloTransicion], hoy: date
    ) -> ResultadoCorteEtario:
        lista = list(ciclos)
        # Solo entran los ciclos con fecha de nacimiento: sin ella el corte no
        # se puede evaluar y el dominio se detiene en vez de imputar una edad.
        # Se filtran aqui, en la aplicacion, porque decidir que hacer con un
        # dato incompleto es orquestacion, no regla de negocio.
        evaluables = [c for c in lista if c.fecha_nacimiento is not None]

        metrica = medir_corte_etario(evaluables, hoy)

        riesgo = [
            FilaDeRiesgo(
                paciente_id=c.paciente_id,
                dias_para_corte=dias_para_corte(c.fecha_nacimiento, hoy),
                estado=c.estado.etiqueta,
                responsable=c.responsable.etiqueta,
            )
            for c in evaluables
            if c.fecha_nacimiento is not None and en_riesgo_de_corte(c, hoy)
        ]
        # Lo mas urgente arriba: quien menos dias le quedan.
        riesgo.sort(key=lambda f: f.dias_para_corte)

        return ResultadoCorteEtario(
            metrica=metrica,
            en_riesgo=tuple(riesgo),
            consumados=tuple(fracasos(evaluables, hoy)),
        )

    def sin_fecha_de_nacimiento(
        self, ciclos: Sequence[CicloTransicion]
    ) -> tuple[str, ...]:
        """Los ciclos que no se pueden evaluar, para poder decirlo.

        Un denominador que excluye casos en silencio produce una metrica que
        mejora sola cuando empeoran los datos. Si hay ciclos sin fecha, la
        interfaz tiene que poder decir cuantos.
        """
        return tuple(c.paciente_id for c in ciclos if c.fecha_nacimiento is None)
