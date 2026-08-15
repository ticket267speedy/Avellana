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


def elegir_ruta_corpus(raiz_datos: Path) -> Path:
    """El corpus completo si esta generado; si no, el versionado."""
    completo = raiz_datos / NOMBRE_CORPUS_COMPLETO
    if (completo / "manifiesto.json").exists():
        return completo
    return raiz_datos / NOMBRE_CORPUS_DEMO


class CorpusEnArchivos(RepositorioCorpus):
    """El corpus tal como quedo en disco."""

    def __init__(self, raiz: Path) -> None:
        self._raiz = raiz

    @classmethod
    def descubrir(cls, raiz_datos: Path) -> CorpusEnArchivos:
        """Elige entre el corpus completo y el versionado."""
        return cls(elegir_ruta_corpus(raiz_datos))

    @property
    def disponible(self) -> bool:
        """False cuando no se ha generado ningun corpus todavia."""
        return (self._raiz / "manifiesto.json").exists()

    def _manifiesto(self) -> dict[str, object]:
        if not self.disponible:
            return {}
        crudo = json.loads(
            (self._raiz / "manifiesto.json").read_text(encoding="utf-8")
        )
        return dict(crudo)

    @property
    def es_muestra_parcial(self) -> bool:
        """Lo declara el propio manifiesto.

        No se deduce de la carpeta: el corpus versionado empezo siendo 4 de 12
        documentos y luego paso a llevarlos todos. Deducirlo del nombre del
        directorio habria dejado a la pantalla avisando de una muestra parcial
        que ya no lo era.
        """
        return bool(self._manifiesto().get("parcial", False))

    def muestras(self) -> Sequence[MuestraCorpus]:
        datos = self._manifiesto()
        if not datos:
            return ()
        return tuple(
            MuestraCorpus(
                id=str(m.get("id", "")), variante=str(m.get("variante", ""))
            )
            for m in list(datos.get("muestras", []) or [])
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
