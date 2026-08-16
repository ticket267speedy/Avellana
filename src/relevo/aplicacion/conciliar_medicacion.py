"""Caso de uso: cotejar lo que el paciente declara con lo que dice el Pasaporte.

El sistema reporta la diferencia y abre un caso. No decide cual version es la
correcta, y no toca el Pasaporte. Las dos cosas estan garantizadas en el
dominio; este caso de uso solo orquesta.

Importa solo `dominio`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from relevo.dominio.entidades.conciliacion import (
    CasoDeConciliacion,
    MedicacionDeclarada,
)
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.objetos_valor.origen_dato import OrigenDato, TipoDiscrepancia
from relevo.dominio.servicios.conciliador import conciliar, hay_algo_que_cotejar


@dataclass(frozen=True, slots=True)
class LineaDeMedicacion:
    """Una linea de la tabla que ve el paciente, con su insignia de origen.

    Es la traduccion de `EstadoCampo` al idioma de quien lo lee. Un adolescente
    no necesita saber que un campo esta en ambar: necesita saber que esa dosis
    la dijo el.
    """

    nombre: str
    dosis: str | None
    frecuencia: str | None
    origen: OrigenDato

    @property
    def insignia(self) -> str:
        return self.origen.etiqueta_corta

    @property
    def hay_que_completar(self) -> bool:
        """True si la dosis es un hueco a proposito, no un olvido.

        Un hueco visible obliga al medico a llenarlo; una dosis plausible pero
        inventada no obliga a nada (regla 8).
        """
        return self.origen is OrigenDato.VERIFICADO_INSN and self.dosis is None


@dataclass(frozen=True, slots=True)
class ResultadoConciliacion:
    caso: CasoDeConciliacion
    requiere_revision: bool

    @property
    def total(self) -> int:
        return self.caso.total_discrepancias

    def por_tipo(self, tipo: TipoDiscrepancia) -> int:
        return len(self.caso.discrepancias_de(tipo))

    def titular(self) -> str:
        if not self.requiere_revision:
            return "Se cotejo la medicacion y coincide."
        return (
            f"{self.total} diferencias entre lo que declara el paciente y el "
            "Pasaporte. Las revisa el equipo del INSN."
        )


@dataclass(frozen=True, slots=True)
class ConciliarMedicacion:
    """Coteja y abre el caso. Nunca escribe en el Pasaporte."""

    def ejecutar(
        self,
        paciente: Paciente,
        declarados: Sequence[MedicacionDeclarada],
        hoy: date,
    ) -> ResultadoConciliacion:
        caso = conciliar(paciente.id, paciente.medicamentos, declarados, hoy)
        return ResultadoConciliacion(
            caso=caso, requiere_revision=hay_algo_que_cotejar(caso)
        )

    def vista_para_el_paciente(
        self, paciente: Paciente, declarados: Sequence[MedicacionDeclarada]
    ) -> tuple[LineaDeMedicacion, ...]:
        """Las dos listas juntas, cada linea con su origen.

        Se presentan mezcladas y etiquetadas en vez de en dos tablas separadas:
        lo que el paciente necesita ver es SU medicacion completa, y de donde
        sale cada cosa. Dos tablas le obligarian a cotejarlas el mismo, que es
        justo el trabajo que este mecanismo viene a hacer.
        """
        lineas = [
            LineaDeMedicacion(
                nombre=m.nombre,
                dosis=m.dosis,
                frecuencia=m.frecuencia,
                origen=(
                    OrigenDato.VERIFICADO_INSN
                    if m.verificada_en_fuente
                    else OrigenDato.PENDIENTE_DE_COTEJO
                ),
            )
            for m in paciente.medicamentos
        ]
        conocidos = {m.nombre.lower() for m in paciente.medicamentos}
        lineas.extend(
            LineaDeMedicacion(
                nombre=d.nombre,
                dosis=d.dosis,
                frecuencia=d.frecuencia,
                origen=OrigenDato.INFORMADO_POR_PACIENTE,
            )
            for d in declarados
            if d.lo_sigue_tomando and d.nombre.lower() not in conocidos
        )
        return tuple(lineas)

    def cola_del_equipo(
        self, casos: Iterable[CasoDeConciliacion]
    ) -> tuple[CasoDeConciliacion, ...]:
        """Los casos abiertos con algo que mirar, el mas antiguo primero.

        Los casos sin discrepancias se registran pero no entran: llenar la
        bandeja de cosas que no piden nada es la forma mas rapida de que se
        deje de mirar.
        """
        pendientes = [
            c for c in casos if c.esta_abierto and c.total_discrepancias > 0
        ]
        return tuple(sorted(pendientes, key=lambda c: c.fecha_apertura))
