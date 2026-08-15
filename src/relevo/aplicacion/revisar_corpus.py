"""Caso de uso: revisar los documentos del corpus y su lectura.

Es la orquestacion detras de la pantalla de digitalizacion:

    corpus -> imagen -> transcripcion (cacheada o en vivo) -> campos -> verdad

Antes vivia como funciones sueltas dentro de `app.py`, leyendo rutas a mano y
decidiendo alli mismo cuando cachear. Se movio aqui cuando
`test_la_aplicacion_no_es_vestigial` detecto que el adaptador de entrada se
estaba comiendo la orquestacion.

Solo importa `dominio`. `tests/test_arquitectura.py` lo verifica.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from relevo.aplicacion.digitalizar_documento import (
    DigitalizarDocumento,
    DocumentoDigitalizado,
)
from relevo.dominio.puertos.corpus import MuestraCorpus, RepositorioCorpus

ORIGEN_CACHE = "lectura previa guardada en disco"
ORIGEN_VIVO = "lectura en vivo del modelo"


@dataclass(frozen=True, slots=True)
class LecturaDeCorpus:
    """Un documento leido, con constancia de de donde salio el texto."""

    documento: DocumentoDigitalizado
    verdad: dict[str, str]
    origen: str
    """`ORIGEN_CACHE` u `ORIGEN_VIVO`.

    Se muestra en pantalla porque no es un detalle: una demo que presenta texto
    cacheado como si acabara de salir del modelo esta exagerando lo que el
    sistema hace en ese momento.
    """

    @property
    def fue_en_vivo(self) -> bool:
        return self.origen == ORIGEN_VIVO


class RevisarCorpus:
    """Sirve documentos del corpus ya leidos y listos para revisar."""

    def __init__(
        self, corpus: RepositorioCorpus, digitalizar: DigitalizarDocumento
    ) -> None:
        self._corpus = corpus
        self._digitalizar = digitalizar

    def muestras(self) -> Sequence[MuestraCorpus]:
        return self._corpus.muestras()

    @property
    def hay_documentos(self) -> bool:
        return len(self._corpus.muestras()) > 0

    @property
    def es_muestra_parcial(self) -> bool:
        return self._corpus.es_muestra_parcial

    def variante_de(self, documento_id: str) -> str:
        for m in self._corpus.muestras():
            if m.id == documento_id:
                return m.variante
        return ""

    def leer_cacheado(self, documento_id: str) -> LecturaDeCorpus | None:
        """El documento a partir de su transcripcion guardada.

        None cuando nunca se leyo: es informacion, no un fallo. La pantalla
        ofrece leerlo con el modelo en ese caso.
        """
        texto = self._corpus.transcripcion_guardada(documento_id)
        if texto is None:
            return None
        return self._componer(documento_id, texto, ORIGEN_CACHE)

    def leer_en_vivo(
        self, documento_id: str, cachear: bool = True
    ) -> LecturaDeCorpus:
        """Ejecuta el modelo sobre la imagen ahora mismo.

        `cachear=False` para las relecturas sobre un documento que ya tenia
        transcripcion. Esa cache es lo que mantiene la pantalla en pie cuando
        no hay ningun modelo alcanzable, y una relectura no debe destruir el
        unico respaldo si el modelo falla a mitad de una demo.
        """
        imagen = self._corpus.imagen(documento_id)
        documento = self._digitalizar.ejecutar(documento_id, imagen)
        if cachear:
            self._corpus.guardar_transcripcion(documento_id, documento.texto)
        return LecturaDeCorpus(
            documento=documento,
            verdad=self._corpus.verdad(documento_id),
            origen=ORIGEN_VIVO,
        )

    def releer_texto(self, documento_id: str, texto: str) -> LecturaDeCorpus:
        """Recompone la lectura a partir de un texto ya obtenido en vivo.

        Streamlit vuelve a ejecutar el script entero en cada interaccion. Sin
        esto habria que llamar al modelo otra vez —dos minutos— cada vez que
        alguien corrige una casilla.
        """
        return self._componer(documento_id, texto, ORIGEN_VIVO)

    def _componer(
        self, documento_id: str, texto: str, origen: str
    ) -> LecturaDeCorpus:
        return LecturaDeCorpus(
            documento=self._digitalizar.desde_texto(documento_id, texto),
            verdad=self._corpus.verdad(documento_id),
            origen=origen,
        )
