"""Puerto de lectura de documentos escaneados.

POR QUE ESTE PUERTO VIVE AQUI Y NO EN INFRAESTRUCTURA
La revision de arquitectura del 15-ago-2026 encontro dos abstracciones
compitiendo para lo mismo: `GeneradorResumen` en el dominio, sin ningun
adaptador, y un `LectorDocumento` declarado dentro de
`infraestructura/llm/extractor.py` — es decir, la capa externa definiendo su
propia abstraccion e implementandosela a si misma. El dominio no sabia que
existia un lector de documentos.

Este archivo cierra ese hueco: el puerto lo declara el dominio, que es quien
dice QUE necesita, y la infraestructura decide COMO. Ollama, una API, o el
lector nulo son intercambiables sin que el nucleo se entere.

QUE NO HACE ESTE PUERTO
No devuelve campos: devuelve TEXTO CRUDO. Medido sobre el corpus, un modelo de
OCR obedece mal los esquemas JSON y muy bien la instruccion de transcribir. La
extraccion de campos es un paso aparte, determinista, y no le corresponde al
modelo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LectorDocumento(ABC):
    """Convierte la imagen de un documento en texto.

    Toda implementacion debe cumplir dos cosas:

    1. Si no puede leer, LO DICE — lanza excepcion. Nunca devuelve texto vacio
       haciendose pasar por una lectura correcta. Un documento sin leer y un
       documento leido como vacio son cosas distintas, y confundirlas es el
       fallo silencioso que este sistema existe para impedir.
    2. No interpreta ni corrige. Transcribe.
    """

    @abstractmethod
    def leer(self, imagen: bytes, instruccion: str) -> str:
        """Texto crudo del documento, sin interpretar."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Identificador legible: 'ollama/glm-ocr', 'sin-modelo'.

        Se muestra en la interfaz y se guarda en el acta: quien revisa tiene
        derecho a saber que leyo el documento.
        """

    @property
    @abstractmethod
    def requiere_red(self) -> bool:
        """False en los lectores locales.

        Es lo que permite prometer que el sistema corre con el wifi apagado, y
        verificarlo en vez de afirmarlo.
        """
