"""Caso de uso: reabrir un ciclo, y sacarlo del limbo despues.

REINGRESO es transitorio. Este caso de uso tiene dos mitades a proposito —
`ejecutar` reabre y `reclasificar` cierra la reapertura— porque un sistema que
solo supiera reabrir convertiria el estado en el cajon donde los casos dificiles
van a morir sin que nadie lo note.

Recordatorio, porque es la confusion que costo tiempo: esto reabre el CICLO
ADMINISTRATIVO, no la atencion pediatrica. Con el paciente >= 18 solo quedan
habilitadas acciones administrativas, y eso lo impone `acciones_permitidas` en
el dominio.

Importa solo `dominio`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from relevo.dominio.entidades.ciclo_transicion import CicloTransicion, EstadoCiclo
from relevo.dominio.objetos_valor.reingreso import (
    AccionCiclo,
    MotivoReingreso,
    acciones_permitidas,
)
from relevo.dominio.servicios.maquina_ciclo import MaquinaCiclo

from relevo.aplicacion.avanzar_ciclo import AvanzarCiclo, ResultadoAvance

# Dias que puede estar un ciclo en REINGRESO antes de que se considere
# abandonado. Coincide con el plazo de la tabla del ciclo, que es provisional.
# TODO: confirmar con mentor.
DIAS_PARA_RECLASIFICAR = 7


@dataclass(frozen=True, slots=True)
class ResultadoReingreso:
    """El reingreso, con lo que se puede hacer a partir de ahora.

    `acciones` va aqui y no se consulta aparte porque la pregunta inmediata
    tras reabrir un ciclo de un paciente mayor de edad es exactamente esa: y la
    respuesta —solo administrativas— es la que evita el malentendido.
    """

    avance: ResultadoAvance
    motivo: MotivoReingreso
    acciones: frozenset[AccionCiclo]

    @property
    def solo_administrativas(self) -> bool:
        return not any(a.es_clinica for a in self.acciones)

    def aviso(self) -> str | None:
        """El texto que la interfaz muestra sobre un ciclo reabierto.

        Existe para que nadie —ni el equipo ni un jurado— lea "reingreso" como
        "vuelve a atenderse en el INSN".
        """
        if self.solo_administrativas:
            return (
                "Este ciclo esta reabierto para gestion administrativa. El "
                "paciente es mayor de 18 anios y el INSN no puede atenderlo: "
                "solo se puede reenviar documentacion y contactar al receptor "
                "o a la familia."
            )
        return None


@dataclass(frozen=True, slots=True)
class RegistrarReingreso:
    """Reabre ciclos y vigila que no se queden reabiertos."""

    avanzar: AvanzarCiclo

    @classmethod
    def con_maquina(cls, maquina: MaquinaCiclo) -> RegistrarReingreso:
        return cls(avanzar=AvanzarCiclo(maquina=maquina))

    def ejecutar(
        self,
        ciclo: CicloTransicion,
        motivo: MotivoReingreso,
        hoy: date,
        registrado_por: str = "",
        nota_administrativa: str = "",
    ) -> ResultadoReingreso:
        avance = self.avanzar.ejecutar(
            ciclo,
            EstadoCiclo.REINGRESO,
            hoy,
            registrado_por=registrado_por,
            motivo_reingreso=motivo,
            nota_administrativa=nota_administrativa,
        )
        return ResultadoReingreso(
            avance=avance,
            motivo=motivo,
            acciones=acciones_permitidas(ciclo, hoy),
        )

    def reclasificar(
        self,
        ciclo: CicloTransicion,
        estado: EstadoCiclo,
        hoy: date,
        registrado_por: str = "",
    ) -> ResultadoAvance:
        """Devuelve el ciclo a la linea de tramite."""
        return self.avanzar.reclasificar(
            ciclo, estado, hoy, registrado_por=registrado_por
        )

    def reingresos_estancados(
        self, ciclos: Iterable[CicloTransicion], hoy: date
    ) -> list[CicloTransicion]:
        """Los que llevan demasiado tiempo sin reclasificar.

        Es la cola de trabajo que impide que REINGRESO se convierta en un
        vertedero. Se ordena por antiguedad: el que lleva mas tiempo parado
        arriba.
        """
        limite = hoy - timedelta(days=DIAS_PARA_RECLASIFICAR)
        estancados = [
            c
            for c in ciclos
            if c.estado is EstadoCiclo.REINGRESO and c.fecha_estado_actual <= limite
        ]
        return sorted(estancados, key=lambda c: c.fecha_estado_actual)
