"""Corre el pipeline completo sobre el corpus y reporta la metrica que importa.

    python -m relevo.interfaz.cli.evaluar_corpus --corpus data/corpus
    python -m relevo.interfaz.cli.evaluar_corpus --corpus data/corpus --ollama

Sin `--ollama` usa el lector simulado: no hace falta GPU ni modelo, y sirve para
calibrar umbrales y comprobar que la validacion detecta lo que dice detectar.

LO QUE SE REPORTA

    exactitud bruta          cuantos campos quedaron con el valor correcto
    error NO detectado       ← LA metrica. Campos mal leidos que quedaron VERDE
    carga de revision        que fraccion tiene que mirar una persona

Un sistema con 88% de exactitud y 0% de error no detectado es utilizable en un
hospital. Uno con 97% de exactitud y 3% de error no detectado, no: significa que
tres de cada cien datos entran mal al expediente sin que nadie se entere.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from relevo.dominio.objetos_valor.campo_extraido import EstadoCampo
from relevo.dominio.servicios.verificador_extraccion import (
    VerificadorExtraccion,
    medir,
)
from relevo.infraestructura.llm.catalogo_campos import (
    campos_pedidos,
    especificaciones,
    reglas_cruzadas,
)
from relevo.infraestructura.llm.extractor import ExtractorDocumento
from relevo.infraestructura.llm.lector_simulado import par_de_lectores_simulados


def evaluar(corpus: Path, usar_ollama: bool = False, limite: int | None = None) -> dict:
    manifiesto = json.loads((corpus / "manifiesto.json").read_text(encoding="utf-8"))
    muestras = manifiesto["muestras"][:limite] if limite else manifiesto["muestras"]

    specs = especificaciones()
    verificador = VerificadorExtraccion(
        especificaciones=specs,
        reglas_cruzadas=reglas_cruzadas(hoy=date(2026, 8, 14)),
    )
    pedidos = campos_pedidos()

    lector_ollama = contraste_ollama = None
    if usar_ollama:
        from relevo.infraestructura.llm.lector_ollama import elegir_lectores

        lector_ollama, contraste_ollama = elegir_lectores()
        print(f"Lectores: {lector_ollama.nombre} / {getattr(contraste_ollama, 'nombre', '—')}\n")

    tot = cor = rev = nodet = det = 0
    estados: Counter[str] = Counter()
    peores: Counter[str] = Counter()
    corregidos = 0

    for i, m in enumerate(muestras, start=1):
        verdad = json.loads(
            (corpus / "verdad" / f"{m['id']}.json").read_text(encoding="utf-8")
        )
        verdad_specs = {k: v for k, v in verdad.items() if k in specs}

        if usar_ollama:
            ex = ExtractorDocumento(
                campos=pedidos,
                lector_principal=lector_ollama,
                lector_contraste=contraste_ollama,
            )
            p, s = ex.leer_imagen(corpus / "imagenes" / f"{m['id']}.jpg")
            lecturas, segunda = dict(p.valores), (dict(s.valores) if s else None)
        else:
            la, lb = par_de_lectores_simulados(verdad_specs, semilla=m["semilla"])
            ex = ExtractorDocumento(campos=pedidos, lector_principal=la, lector_contraste=lb)
            p, s = ex.leer_imagen(b"")
            lecturas, segunda = dict(p.valores), (dict(s.valores) if s else None)

        rep = verificador.verificar(lecturas, segunda_lectura=segunda)
        met = medir(rep, verdad_specs)

        tot += met.total
        cor += met.correctos
        rev += met.revisados
        nodet += met.errores_no_detectados
        det += met.errores_detectados
        corregidos += len(rep.corregidos_por_catalogo)
        for c in rep.campos.values():
            estados[c.estado.value] += 1
            if c.estado is not EstadoCampo.VERDE:
                peores[c.nombre] += 1

        if i % 25 == 0:
            print(f"  {i}/{len(muestras)}")

    return {
        "muestras": len(muestras),
        "campos_totales": tot,
        "exactitud_bruta": cor / tot if tot else 0.0,
        "tasa_error_no_detectado": nodet / tot if tot else 0.0,
        "carga_revision": rev / tot if tot else 0.0,
        "errores_detectados": det,
        "errores_no_detectados": nodet,
        "corregidos_por_catalogo": corregidos,
        "estados": dict(estados),
        "campos_mas_problematicos": peores.most_common(8),
    }


def imprimir(r: dict) -> None:
    print("\n" + "=" * 68)
    print(f"  {r['muestras']} documentos · {r['campos_totales']} campos evaluados")
    print("=" * 68)
    print(f"  Exactitud bruta            {r['exactitud_bruta']:>8.1%}")
    print(f"  Carga de revision humana   {r['carga_revision']:>8.1%}")
    print(f"  Corregidos por catalogo    {r['corregidos_por_catalogo']:>8,}")
    print(f"  Errores DETECTADOS         {r['errores_detectados']:>8,}")
    print()
    print(f"  >> ERROR NO DETECTADO      {r['tasa_error_no_detectado']:>8.2%}   "
          f"({r['errores_no_detectados']} campos)")
    print()
    e = r["estados"]
    print(f"  verde {e.get('verde',0):>6,}   ambar {e.get('ambar',0):>6,}   "
          f"rojo {e.get('rojo',0):>6,}")
    if r["campos_mas_problematicos"]:
        print("\n  Campos que mas revision piden:")
        for nombre, n in r["campos_mas_problematicos"]:
            print(f"    {nombre:28s} {n:>5,}")
    print("=" * 68)


def main() -> None:
    p = argparse.ArgumentParser(description="Evalua el pipeline sobre el corpus")
    p.add_argument("--corpus", type=Path, default=Path("data/corpus"))
    p.add_argument("--ollama", action="store_true", help="usar modelos reales")
    p.add_argument("--limite", type=int, default=None)
    p.add_argument("--json", type=Path, default=None)
    a = p.parse_args()

    r = evaluar(a.corpus, a.ollama, a.limite)
    imprimir(r)
    if a.json:
        a.json.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGuardado en {a.json}")


if __name__ == "__main__":
    main()
