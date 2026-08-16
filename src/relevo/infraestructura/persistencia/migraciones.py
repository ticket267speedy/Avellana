"""Migracion del esquema. v1 -> v2: los nueve estados del ciclo.

═══════════════════════════════════════════════════════════════════════════════
NADA SE BORRA
═══════════════════════════════════════════════════════════════════════════════

Borrar filas para simplificar una migracion es perder justamente el historico
que el piloto viene a medir. Aqui se TRADUCE: cada estado del modelo de seis se
reescribe al del modelo de nueve, tanto en la columna indexada como dentro del
documento JSON, y el mapa de traduccion esta en un solo sitio
(`dominio/objetos_valor/estado_ciclo.py`, `ESTADOS_LEGADO`).

La migracion es idempotente: correrla dos veces no cambia nada, porque
`estado_desde_persistido` reconoce los valores nuevos y los devuelve tal cual.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from relevo.dominio.objetos_valor.estado_ciclo import (
    EstadoCiclo,
    estado_desde_persistido,
)


@dataclass(frozen=True, slots=True)
class InformeMigracion:
    """Que se toco, para poder decirlo en voz alta.

    Una migracion silenciosa es indistinguible de una que no corrio. Si el
    numero de ciclos traducidos no cuadra con lo que habia, hay que enterarse
    en ese momento y no tres demos despues.
    """

    version_anterior: int
    version_nueva: int
    ciclos_revisados: int
    ciclos_traducidos: int
    estados_encontrados: dict[str, str]
    """Valor viejo -> valor nuevo, para cada traduccion que se hizo."""

    @property
    def hubo_cambios(self) -> bool:
        return self.ciclos_traducidos > 0

    def resumen(self) -> str:
        if self.version_anterior == self.version_nueva:
            return f"Esquema ya en v{self.version_nueva}: nada que migrar."
        if not self.hubo_cambios:
            return (
                f"Esquema v{self.version_anterior} -> v{self.version_nueva}. "
                "No habia ciclos con estados del modelo anterior."
            )
        traducciones = ", ".join(
            f"{viejo} -> {nuevo}" for viejo, nuevo in sorted(self.estados_encontrados.items())
        )
        return (
            f"Esquema v{self.version_anterior} -> v{self.version_nueva}. "
            f"{self.ciclos_traducidos} de {self.ciclos_revisados} ciclos "
            f"traducidos ({traducciones}). Ninguna fila borrada."
        )


def version_actual(bd: Any) -> int:
    with bd.conectar() as cx:
        fila = cx.execute(
            "SELECT MAX(version) v FROM esquema_version"
        ).fetchone()
    return int(fila["v"] or 0)


def migrar(bd: Any, version_objetivo: int) -> InformeMigracion:
    """Lleva la base a `version_objetivo`. Idempotente y sin perdidas."""
    anterior = version_actual(bd)
    revisados = 0
    traducidos = 0
    encontrados: dict[str, str] = {}

    with bd.conectar() as cx:
        filas = cx.execute("SELECT id, estado, documento FROM ciclo").fetchall()
        for fila in filas:
            revisados += 1
            nuevo_estado, doc, cambio, vistos = _traducir_ciclo(
                fila["estado"], fila["documento"]
            )
            encontrados.update(vistos)
            if not cambio:
                continue
            traducidos += 1
            cx.execute(
                "UPDATE ciclo SET estado = ?, documento = ?, "
                "cerrado = ?, actualizado = ? WHERE id = ?",
                (
                    nuevo_estado,
                    doc,
                    int(nuevo_estado == EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA.value),
                    datetime.now().isoformat(timespec="seconds"),
                    fila["id"],
                ),
            )

        if version_objetivo > anterior:
            cx.execute(
                "INSERT OR IGNORE INTO esquema_version (version, aplicado) "
                "VALUES (?, ?)",
                (version_objetivo, datetime.now().isoformat(timespec="seconds")),
            )

    return InformeMigracion(
        version_anterior=anterior,
        version_nueva=max(anterior, version_objetivo),
        ciclos_revisados=revisados,
        ciclos_traducidos=traducidos,
        estados_encontrados=encontrados,
    )


def _traducir_ciclo(
    estado_columna: str, documento: str
) -> tuple[str, str, bool, dict[str, str]]:
    """Traduce la columna indexada y el historial de dentro del documento.

    Las dos cosas: si solo se tradujera la columna, el radar mostraria el
    estado nuevo y la linea de tiempo del paciente seguiria pintando los viejos.
    """
    vistos: dict[str, str] = {}
    cambio = False

    nuevo = estado_desde_persistido(estado_columna).value
    if nuevo != estado_columna:
        vistos[str(estado_columna)] = nuevo
        cambio = True

    doc: dict[str, Any] = json.loads(documento)
    for evento in doc.get("historial", []):
        crudo = str(evento.get("estado", ""))
        if not crudo:
            continue
        traducido = estado_desde_persistido(crudo).value
        if traducido != crudo:
            vistos[crudo] = traducido
            evento["estado"] = traducido
            cambio = True

    return nuevo, json.dumps(doc, ensure_ascii=False), cambio, vistos
