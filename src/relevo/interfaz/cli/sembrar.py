"""Siembra, reinicia y respalda la base de datos de demo.

    python -m relevo.interfaz.cli.sembrar                 # siembra si esta vacia
    python -m relevo.interfaz.cli.sembrar --reiniciar     # borra todo y vuelve a sembrar
    python -m relevo.interfaz.cli.sembrar --estado        # que hay en la base ahora
    python -m relevo.interfaz.cli.sembrar --exportar respaldo.sql
    python -m relevo.interfaz.cli.sembrar --importar respaldo.sql

POR QUE ASI Y NO UN VOLCADO SQL VERSIONADO
La demo se ensucia: se corrigen campos, se firman actas, se avanzan ciclos. Hace
falta poder volver al punto de partida en un comando, y que el punto de partida
sea SIEMPRE el mismo — si cada reinicio genera una cohorte distinta, el ensayo
del pitch no sirve para nada.

La semilla no se guarda como filas: se guarda como PARAMETROS en
`config/semilla_demo.yaml`, y la cohorte se regenera de forma determinista a
partir de ellos. Ventajas sobre un volcado:

  · Un YAML de veinte lineas se lee, se versiona y se revisa en un diff.
    Un .sql de tres mil filas, no.
  · Si el modelo de dominio cambia, la semilla sigue funcionando: se regenera.
    Un volcado quedaria desfasado del esquema.
  · La reproducibilidad es exacta: misma semilla, misma cohorte, hasta el
    ultimo digito del IUT.

`--exportar` existe igual, para cuando quieras congelar un estado concreto que
te gusto — por ejemplo el que usaste en el ensayo que salio bien.

NUNCA se siembra sobre datos reales: `--reiniciar` exige `--si-estoy-seguro`
cuando la base no esta marcada como de demo.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

import yaml

RUTA_BD = Path("data/relevo.db")
RUTA_SEMILLA = Path("config/semilla_demo.yaml")

SEMILLA_POR_DEFECTO = {
    "version": 1,
    "es_demo": True,
    "semilla_aleatoria": 20260815,
    "pacientes": 120,
    "fecha_referencia": "2026-08-15",
    "ciclos_abiertos": 18,
    "reparto_estados_ciclo": {
        "PASAPORTE_EMITIDO": 5,
        "REFERENCIA_REGISTRADA": 4,
        "REFERENCIA_ACEPTADA": 5,
        "CITA_PROGRAMADA": 3,
        "CITA_CUMPLIDA": 1,
    },
    "ciclos_vencidos_forzados": 3,
    "nota": (
        "Cohorte sintetica reproducible. Ningun dato corresponde a una persona "
        "real. Misma semilla_aleatoria = misma cohorte, hasta el ultimo digito "
        "del IUT."
    ),
}


def cargar_semilla(ruta: Path = RUTA_SEMILLA) -> dict:
    """Lee la semilla; si no existe la escribe con los valores por defecto."""
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            yaml.safe_dump(SEMILLA_POR_DEFECTO, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        print(f"Semilla creada en {ruta} con los valores por defecto.")
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def exportar(bd_ruta: Path, destino: Path) -> None:
    """Volcado SQL completo. Para congelar un estado concreto."""
    cx = sqlite3.connect(bd_ruta)
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8") as f:
            f.write("-- Respaldo Relevo. DATOS SINTETICOS DE DEMO.\n")
            f.write(f"-- Generado desde {bd_ruta}\n\n")
            for linea in cx.iterdump():
                f.write(f"{linea}\n")
    finally:
        cx.close()
    print(f"Respaldo escrito en {destino} ({destino.stat().st_size:,} bytes)")


def importar(bd_ruta: Path, origen: Path) -> None:
    """Restaura un volcado. Reemplaza lo que haya."""
    if not origen.exists():
        raise SystemExit(f"No existe {origen}")
    if bd_ruta.exists():
        bd_ruta.unlink()
    bd_ruta.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(bd_ruta)
    try:
        cx.executescript(origen.read_text(encoding="utf-8"))
        cx.commit()
    finally:
        cx.close()
    print(f"Base restaurada desde {origen}")


def main() -> int:
    p = argparse.ArgumentParser(description="Siembra y reinicia la base de demo")
    p.add_argument("--bd", type=Path, default=RUTA_BD)
    p.add_argument("--semilla", type=Path, default=RUTA_SEMILLA)
    p.add_argument("--reiniciar", action="store_true",
                   help="borra todo y vuelve a sembrar")
    p.add_argument("--si-estoy-seguro", action="store_true",
                   help="requerido para reiniciar una base NO marcada como demo")
    p.add_argument("--conservar-auditoria", action="store_true",
                   help="no borra el registro de auditoria al reiniciar")
    p.add_argument("--estado", action="store_true", help="que hay en la base")
    p.add_argument("--exportar", type=Path, default=None)
    p.add_argument("--importar", type=Path, default=None)
    a = p.parse_args()

    # Import diferido: este CLI se usa tambien para exportar/importar, y en ese
    # caso no hace falta arrastrar el dominio entero.
    from relevo.infraestructura.persistencia.repositorio_sqlite import BaseDatos

    if a.importar:
        importar(a.bd, a.importar)
        return 0
    if a.exportar:
        exportar(a.bd, a.exportar)
        return 0

    bd = BaseDatos(a.bd)

    if a.estado:
        conteo = bd.contar()
        info = bd.info_semilla()
        print(f"Base: {a.bd}")
        print(f"  pacientes  {conteo['paciente']:>6,}")
        print(f"  ciclos     {conteo['ciclo']:>6,}")
        print(f"  auditoria  {conteo['auditoria']:>6,}")
        if info:
            print("\nSembrada con:")
            for k, v in sorted(info.items()):
                print(f"  {k:22s} {v}")
        else:
            print("\nSin marca de semilla: la base NO fue sembrada por este CLI.")
        return 0

    semilla = cargar_semilla(a.semilla)
    conteo = bd.contar()

    if a.reiniciar:
        marca = bd.info_semilla()
        es_demo = marca.get("es_demo", "").lower() in {"true", "1", "si"}
        if conteo["paciente"] and not es_demo and not a.si_estoy_seguro:
            print(
                "ABORTADO. La base tiene datos y no esta marcada como demo.\n"
                "Si de verdad quieres borrarla, repite con --si-estoy-seguro.\n"
                "Si son datos reales: no lo hagas, exporta primero.",
                file=sys.stderr,
            )
            return 2
        bd.vaciar(conservar_auditoria=a.conservar_auditoria)
        print(f"Base vaciada{' (auditoria conservada)' if a.conservar_auditoria else ''}.")
    elif conteo["paciente"]:
        print(
            f"La base ya tiene {conteo['paciente']:,} pacientes. "
            "Usa --reiniciar para volver al punto de partida."
        )
        return 0

    # ── Siembra ──────────────────────────────────────────────────────────────
    # El generador de cohorte y los mapeadores los provee `arranque`, para que
    # este CLI no conozca adaptadores concretos.
    from relevo.interfaz.arranque import construir

    contenedor = construir()
    hoy = date.fromisoformat(str(semilla["fecha_referencia"]))
    creados = contenedor.sembrar_demo(
        n_pacientes=int(semilla["pacientes"]),
        semilla_aleatoria=int(semilla["semilla_aleatoria"]),
        hoy=hoy,
        ciclos_abiertos=int(semilla["ciclos_abiertos"]),
        reparto_estados=semilla.get("reparto_estados_ciclo", {}),
        vencidos_forzados=int(semilla.get("ciclos_vencidos_forzados", 0)),
    )

    bd.marcar_semilla({
        "es_demo": str(bool(semilla.get("es_demo", True))),
        "semilla_aleatoria": str(semilla["semilla_aleatoria"]),
        "fecha_referencia": str(semilla["fecha_referencia"]),
        "version_semilla": str(semilla.get("version", 1)),
        "sembrado_en": date.today().isoformat(),
    })

    final = bd.contar()
    print(
        f"Sembrado: {final['paciente']:,} pacientes · {final['ciclo']:,} ciclos "
        f"(semilla {semilla['semilla_aleatoria']}, fecha {semilla['fecha_referencia']})"
    )
    print(f"  de los cuales vencidos a proposito: {creados.get('vencidos', 0)}")
    print("\nMisma semilla = misma cohorte. El ensayo del pitch es reproducible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
