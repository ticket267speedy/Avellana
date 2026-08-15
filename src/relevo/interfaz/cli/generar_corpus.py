"""Genera el corpus sintetico de Hojas de Referencia, con su verdad.

    python -m relevo.interfaz.cli.generar_corpus --n 200 --salida data/corpus

Produce, por cada muestra:

    corpus/imagenes/hr_0001.jpg      la foto
    corpus/verdad/hr_0001.json       lo que dice cada campo, exacto
    corpus/manifiesto.json           indice + parametros de generacion

La verdad NO es una anotacion hecha por alguien: es el insumo con el que se
renderizo. Por eso el corpus se puede regenerar entero cambiando una semilla, y
por eso evaluar el pipeline es una funcion y no una tarde de trabajo.

Reparto por defecto — imita lo que llega al INSN segun su propio flujo
(documentos escaneados enviados por correo):

    60 %  foto de celular manuscrita   ← el caso real y el dificil
    20 %  escaneo limpio manuscrito
    15 %  tipeado (la direccion a la que va el hospital)
     5 %  fotocopia degradada          ← el peor caso

TODO: confirmar el reparto con el mentor. Hoy es una suposicion.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from relevo.infraestructura.corpus.degradacion import Degradacion, degradar
from relevo.infraestructura.corpus.plantilla import dibujar_plantilla_base
from relevo.infraestructura.corpus.renderizador import renderizar_formulario
from relevo.interfaz.cli.descargar_fuentes import de_maquina, manuscritas

REPARTO = (
    ("foto_manuscrita", 0.60),
    ("escaneo_manuscrito", 0.20),
    ("tipeado", 0.15),
    ("fotocopia", 0.05),
)


def _sortear_variante(rnd: random.Random) -> str:
    u, acumulado = rnd.random(), 0.0
    for nombre, peso in REPARTO:
        acumulado += peso
        if u <= acumulado:
            return nombre
    return REPARTO[-1][0]


def generar(
    n: int,
    salida: Path,
    semilla_base: int = 20260814,
    generador_valores=None,
) -> Path:
    """Genera `n` muestras.

    `generador_valores(rnd) -> dict[str, str]` produce los datos de un paciente.
    Se inyecta para poder alimentarlo desde `cohorte_sintetica.py` y que el
    corpus de documentos y la cohorte del Radar sean la MISMA poblacion — un
    formulario escaneado se convierte en un paciente priorizado sin costuras.
    """
    if generador_valores is None:
        from relevo.infraestructura.corpus.datos_ejemplo import valores_de_ejemplo

        generador_valores = valores_de_ejemplo

    manus, maquina = manuscritas(), de_maquina()
    if not manus:
        raise SystemExit(
            "No hay fuentes. Corre primero:\n"
            "    python -m relevo.interfaz.cli.descargar_fuentes"
        )

    (salida / "imagenes").mkdir(parents=True, exist_ok=True)
    (salida / "verdad").mkdir(parents=True, exist_ok=True)

    plantilla = dibujar_plantilla_base()  # se dibuja una vez y se reusa
    manifiesto = []

    for i in range(1, n + 1):
        semilla = semilla_base + i
        rnd = random.Random(semilla)
        variante = _sortear_variante(rnd)
        fuentes = maquina if variante == "tipeado" else manus

        valores = generador_valores(rnd)
        imagen, verdad = renderizar_formulario(
            valores, fuentes, semilla=semilla, plantilla=plantilla
        )

        if variante == "foto_manuscrita":
            cfg = Degradacion.foto_celular(rnd)
        elif variante == "fotocopia":
            cfg = Degradacion.fotocopia(rnd)
        elif variante == "tipeado":
            cfg = Degradacion.foto_celular(rnd) if rnd.random() < 0.5 else Degradacion.limpia()
        else:
            cfg = Degradacion.limpia()

        imagen = degradar(imagen, cfg, semilla)

        nombre = f"hr_{i:04d}"
        ruta_img = salida / "imagenes" / f"{nombre}.jpg"
        imagen.save(ruta_img, quality=cfg.calidad_jpeg)
        (salida / "verdad" / f"{nombre}.json").write_text(
            json.dumps(verdad, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        manifiesto.append(
            {"id": nombre, "variante": variante, "semilla": semilla, "campos": len(verdad)}
        )
        if i % 25 == 0:
            print(f"  {i}/{n}")

    (salida / "manifiesto.json").write_text(
        json.dumps(
            {
                "n": n,
                "semilla_base": semilla_base,
                "reparto": dict(REPARTO),
                "aviso": (
                    "Corpus SINTETICO. Ningun dato corresponde a una persona real. "
                    "La letra es renderizada con fuentes, mas regular que la humana: "
                    "la exactitud medida aqui es OPTIMISTA respecto de manuscrito real."
                ),
                "muestras": manifiesto,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n{n} muestras en {salida}")
    return salida


def main() -> None:
    p = argparse.ArgumentParser(description="Corpus sintetico de Hojas de Referencia")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--salida", type=Path, default=Path("data/corpus"))
    p.add_argument("--semilla", type=int, default=20260814)
    args = p.parse_args()
    generar(args.n, args.salida, args.semilla)


if __name__ == "__main__":
    main()
