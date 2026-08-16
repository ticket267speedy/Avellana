"""Compara las dos listas de medicacion y reporta. No decide.

Esta es la parte de la conciliacion que se puede automatizar sin riesgo:
encontrar las diferencias. Lo que NO se automatiza es resolverlas, y la
separacion entre las dos cosas esta en el tipo de retorno — este servicio
devuelve un `CasoDeConciliacion` abierto, nunca un Pasaporte modificado.

Funcion pura. Sin modelo de lenguaje, sin red, sin estado.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from relevo.dominio.entidades.conciliacion import (
    CasoDeConciliacion,
    Discrepancia,
    MedicacionDeclarada,
    es_dosis_equivalente,
    medicamento_es_el_mismo,
)
from relevo.dominio.entidades.diagnostico import Medicamento
from relevo.dominio.objetos_valor.origen_dato import TipoDiscrepancia


def conciliar(
    paciente_id: str,
    del_pasaporte: Sequence[Medicamento],
    declarados: Sequence[MedicacionDeclarada],
    hoy: date,
) -> CasoDeConciliacion:
    """Coteja las dos listas y devuelve el caso, abierto y asignado al INSN.

    NO modifica ninguna de las dos listas. Las recibe como `Sequence` y no como
    `list` justamente por eso: la firma dice que no va a tocarlas.

    Un caso sin discrepancias tambien se devuelve, con la tupla vacia. Es
    informacion: "se coteja y coincide" es un hecho que vale la pena registrar,
    y devolver `None` obligaria a quien llama a distinguir entre "no se
    coteja" y "coteje y estaba bien".
    """
    discrepancias: list[Discrepancia] = []

    # Solo se cotejan los que el paciente sigue tomando. Uno que declaro haber
    # dejado no es una discrepancia con el Pasaporte: es un cambio de
    # tratamiento, y se reporta como falta en la declaracion mas abajo.
    activos = [d for d in declarados if d.lo_sigue_tomando]

    for medicamento in del_pasaporte:
        pareja = _buscar_declarado(medicamento.nombre, activos)
        if pareja is None:
            discrepancias.append(
                Discrepancia(
                    tipo=TipoDiscrepancia.FALTA_EN_DECLARACION,
                    medicamento=medicamento.nombre,
                    valor_pasaporte=medicamento.dosis,
                )
            )
            continue

        # Solo se comparan dosis cuando las dos existen. Un hueco en el
        # Pasaporte —una dosis no verificada en la fuente— no es una
        # discrepancia: es el hueco deliberado que el medico tiene que llenar,
        # y contarlo como diferencia enterraria las diferencias de verdad.
        if (
            medicamento.dosis is not None
            and pareja.dosis is not None
            and not es_dosis_equivalente(medicamento.dosis, pareja.dosis)
        ):
            discrepancias.append(
                Discrepancia(
                    tipo=TipoDiscrepancia.DOSIS_DISTINTA,
                    medicamento=medicamento.nombre,
                    valor_pasaporte=medicamento.dosis,
                    valor_declarado=pareja.dosis,
                )
            )

        if (
            medicamento.frecuencia is not None
            and pareja.frecuencia is not None
            and not es_dosis_equivalente(medicamento.frecuencia, pareja.frecuencia)
        ):
            discrepancias.append(
                Discrepancia(
                    tipo=TipoDiscrepancia.FRECUENCIA_DISTINTA,
                    medicamento=medicamento.nombre,
                    valor_pasaporte=medicamento.frecuencia,
                    valor_declarado=pareja.frecuencia,
                )
            )

    for declarado in activos:
        if _buscar_en_pasaporte(declarado.nombre, del_pasaporte) is None:
            discrepancias.append(
                Discrepancia(
                    tipo=TipoDiscrepancia.FALTA_EN_PASAPORTE,
                    medicamento=declarado.nombre,
                    valor_declarado=declarado.dosis,
                )
            )

    return CasoDeConciliacion(
        paciente_id=paciente_id,
        fecha_apertura=hoy,
        discrepancias=tuple(discrepancias),
    )


def _buscar_declarado(
    nombre: str, declarados: Sequence[MedicacionDeclarada]
) -> MedicacionDeclarada | None:
    for d in declarados:
        if medicamento_es_el_mismo(nombre, d.nombre):
            return d
    return None


def _buscar_en_pasaporte(
    nombre: str, medicamentos: Sequence[Medicamento]
) -> Medicamento | None:
    for m in medicamentos:
        if medicamento_es_el_mismo(nombre, m.nombre):
            return m
    return None


def hay_algo_que_cotejar(caso: CasoDeConciliacion) -> bool:
    """Si este caso merece aparecer en la cola de trabajo del equipo.

    Un caso sin discrepancias se registra pero no se muestra: llenar la bandeja
    de casos que no piden nada es la forma mas rapida de que se deje de mirar.
    """
    return caso.total_discrepancias > 0
