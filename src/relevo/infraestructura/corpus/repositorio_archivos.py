"""Corpus leido del sistema de archivos.

Implementa `RepositorioCorpus` sobre el arbol que deja
`relevo.interfaz.cli.generar_corpus`:

    data/corpus/
      manifiesto.json
      imagenes/         hr_0001.jpg
      transcripciones/  hr_0001.txt    (cache; puede faltar)
      verdad/           hr_0001.json

POR QUE HAY DOS CORPUS POSIBLES
El completo (12 documentos, ~9 MB) se genera en local y no se versiona: son
datos generados, y el repositorio no es sitio para 9 MB reconstruibles con un
comando.

Pero en Streamlit Cloud nadie puede correr ese comando, y sin documentos la
pantalla de digitalizacion sale vacia justo en el despliegue que mira el resto
del equipo. Por eso `data/corpus_demo/` —4 de esos documentos, con sus
transcripciones ya producidas por el modelo— si esta versionado.

Se prefiere el completo cuando existe: quien trabaja en local debe ver todo lo
que genero, no la muestra.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from relevo.dominio.puertos.corpus import MuestraCorpus, RepositorioCorpus

NOMBRE_CORPUS_COMPLETO = "corpus"
NOMBRE_CORPUS_DEMO = "corpus_demo"


def elegir_ruta_corpus(raiz_datos: Path) -> tuple[Path, bool]:
    """(ruta, es_muestra_parcial) segun que corpus haya generado o versionado."""
    completo = raiz_datos / NOMBRE_CORPUS_COMPLETO
    if (completo / "manifiesto.json").exists():
        return completo, False
    return raiz_datos / NOMBRE_CORPUS_DEMO, True


class CorpusEnArchivos(RepositorioCorpus):
    """El corpus tal como quedo en disco."""

    def __init__(self, raiz: Path, es_muestra_parcial: bool = False) -> None:
        self._raiz = raiz
        self._parcial = es_muestra_parcial

    @classmethod
    def descubrir(cls, raiz_datos: Path) -> CorpusEnArchivos:
        """Elige entre el corpus completo y la muestra versionada."""
        ruta, parcial = elegir_ruta_corpus(raiz_datos)
        return cls(ruta, es_muestra_parcial=parcial)

    @property
    def disponible(self) -> bool:
        """False cuando no se ha generado ningun corpus todavia."""
        return (self._raiz / "manifiesto.json").exists()

    @property
    def es_muestra_parcial(self) -> bool:
        # Solo tiene sentido avisar de que es parcial si de hecho hay algo.
        return self._parcial and self.disponible

    def muestras(self) -> Sequence[MuestraCorpus]:
        if not self.disponible:
            return ()
        datos = json.loads(
            (self._raiz / "manifiesto.json").read_text(encoding="utf-8")
        )
        return tuple(
            MuestraCorpus(
                id=str(m.get("id", "")), variante=str(m.get("variante", ""))
            )
            for m in datos.get("muestras", [])
        )

    def imagen(self, documento_id: str) -> bytes:
        return (self._raiz / "imagenes" / f"{documento_id}.jpg").read_bytes()

    def ruta_imagen(self, documento_id: str) -> Path | None:
        """La ruta del escaneo, para que Streamlit lo pinte sin releerlo.

        No esta en el puerto a proposito: es una comodidad de este adaptador
        concreto, y el puerto no tiene por que saber que existen los archivos.
        """
        ruta = self._raiz / "imagenes" / f"{documento_id}.jpg"
        return ruta if ruta.exists() else None

    def verdad(self, documento_id: str) -> dict[str, str]:
        ruta = self._raiz / "verdad" / f"{documento_id}.json"
        if not ruta.exists():
            return {}
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in dict(crudo).items()}

    def transcripcion_guardada(self, documento_id: str) -> str | None:
        ruta = self._raiz / "transcripciones" / f"{documento_id}.txt"
        if ruta.exists():
            return ruta.read_text(encoding="utf-8")
        return None

    def guardar_transcripcion(self, documento_id: str, texto: str) -> None:
        destino = self._raiz / "transcripciones"
        destino.mkdir(parents=True, exist_ok=True)
        (destino / f"{documento_id}.txt").write_text(texto, encoding="utf-8")
