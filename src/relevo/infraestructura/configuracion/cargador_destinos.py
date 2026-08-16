"""Carga el directorio de destinos desde `config/destinos.csv`.

ESTE ARCHIVO PRODUCE EL ENTREGABLE DE B1, Y LO PRODUCE AUNQUE EL CSV ESTE VACIO

Hoy ninguna fila del CSV esta confirmada: todas dicen `confirmado=no` y
`institucion_sugerida=PENDIENTE`. Eso significa que `DirectorioDestinos.buscar`
va a devolver `SinDestinoIdentificado` practicamente siempre, y el radar va a
mostrar algo como *"10 de 10 sin destino identificado (100 %)"*.

**Esa cifra no se esconde: es el entregable.** El propio INSN lo escribio en su
rubrica — *"la falta de datos tambien es un hallazgo: si una institucion no
cuenta con la informacion necesaria, se evidencia una brecha estructural"*. El
sistema no inventa destinos: mide su ausencia, que es un numero que hoy no
tiene nadie.

Un destino sin confirmar se carga igualmente, pero `Destino.esta_confirmado`
devuelve False y `buscar` lo rechaza. Un directorio lleno de hipotesis sin
confirmar es peor que uno vacio: da falsa seguridad.
"""

from __future__ import annotations

import csv
from pathlib import Path

from relevo.dominio.entidades.destino import Destino, DirectorioDestinos

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
CONFIG = RAIZ_PROYECTO / "config"

# Valores de la columna `confirmado` que cuentan como si. Cualquier otra cosa
# —incluido el vacio— se lee como no confirmado. La ambiguedad se resuelve
# siempre hacia el lado prudente.
_AFIRMATIVOS = frozenset({"si", "sí", "yes", "true", "1", "x"})


def cargar_directorio(ruta: Path | None = None) -> DirectorioDestinos:
    """Lee el CSV. Devuelve un directorio vacio si el archivo no esta.

    Vacio y no una excepcion, a diferencia de los plazos o los betas: aqui la
    ausencia de datos ES el estado esperado del proyecto hoy, y el sistema
    tiene que poder arrancar y contar cuantas veces se consulto sin encontrar
    nada. Detenerse impediria producir justamente la evidencia de B1.
    """
    ruta = ruta or CONFIG / "destinos.csv"
    if not ruta.exists():
        return DirectorioDestinos(destinos=())

    destinos: list[Destino] = []
    with ruta.open(encoding="utf-8", newline="") as archivo:
        # Las lineas de comentario del CSV empiezan por '#': el encabezado real
        # esta despues del bloque de aviso.
        utiles = (linea for linea in archivo if not linea.lstrip().startswith("#"))
        for fila in csv.DictReader(utiles):
            prefijo = (fila.get("prefijo_cie10") or "").strip()
            if not prefijo:
                continue
            confirmado = (fila.get("confirmado") or "").strip().lower()
            nombre = (fila.get("institucion_sugerida") or "").strip()
            destinos.append(
                Destino(
                    # El CSV no trae codigo RENAES todavia: se usa el prefijo
                    # como clave provisional y se deja constancia de que no es
                    # el identificador real.
                    codigo_renaes=f"PENDIENTE-{prefijo}",
                    nombre=nombre or "PENDIENTE",
                    especialidad=(fila.get("especialidad_adulto") or "").strip(),
                    cie10_que_atiende=(prefijo,),
                    confirmado_por=(
                        (fila.get("nota") or "confirmado en CSV").strip()
                        if confirmado in _AFIRMATIVOS
                        else None
                    ),
                )
            )
    return DirectorioDestinos(destinos=tuple(destinos))


def resumen_del_directorio(directorio: DirectorioDestinos) -> str:
    """Una linea honesta sobre el estado del directorio, para la interfaz.

    Se muestra al lado de la cifra de cobertura. Sin esta linea, un "100 % sin
    destino" se lee como un fallo del software en vez de como lo que es.
    """
    total = len(directorio.destinos)
    confirmados = sum(1 for d in directorio.destinos if d.esta_confirmado)
    if total == 0:
        return (
            "El directorio de destinos esta vacio. Se construye con el mentor "
            "del INSN, entrada por entrada."
        )
    return (
        f"{confirmados} de {total} entradas del directorio estan confirmadas. "
        "Una entrada sin confirmar es una hipotesis, no un destino: el sistema "
        "no la propone."
    )
