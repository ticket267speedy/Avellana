"""Puerto de acceso al corpus de documentos escaneados.

POR QUE EXISTE
La pantalla de digitalizacion necesita cuatro cosas de cada documento: la
imagen, la transcripcion previa si la hay, la verdad de referencia contra la
que medir, y la lista de lo disponible. Todo eso vivia como funciones sueltas
dentro de `app.py`, leyendo rutas a mano.

Eso tenia el coste de siempre: la orquestacion no se podia probar sin levantar
un navegador, y `tests/test_arquitectura.py::test_la_aplicacion_no_es_vestigial`
lo detecto cuando el adaptador de entrada crecio por encima de 3:1 respecto de
la capa de aplicacion.

QUE NO ES ESTE PUERTO
No es el repositorio de pacientes ni tiene nada que ver con la transicion. El
corpus es material de evaluacion: documentos SINTETICOS generados para medir
cuanto acierta el lector. Se declara aparte a proposito.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MuestraCorpus:
    """Un documento del corpus, sin su contenido.

    Lo suficiente para pintar un selector sin cargar imagenes de 1 MB.
    """

    id: str
    variante: str
    """Como se degrado el documento: foto_manuscrita, fotocopia, tipeado..."""


class RepositorioCorpus(ABC):
    """De donde salen los documentos escaneados y sus lecturas."""

    @abstractmethod
    def muestras(self) -> Sequence[MuestraCorpus]:
        """Lo que hay disponible. Vacio si no se ha generado ningun corpus."""

    @abstractmethod
    def imagen(self, documento_id: str) -> bytes:
        """Los bytes del escaneo."""

    @abstractmethod
    def verdad(self, documento_id: str) -> dict[str, str]:
        """Los valores correctos conocidos. Vacio si no se registraron.

        Es lo que convierte la pantalla en una medicion y no en una impresion:
        sin verdad de referencia, "el modelo leyo bien" es una opinion.
        """

    @abstractmethod
    def transcripcion_guardada(self, documento_id: str) -> str | None:
        """La lectura previa cacheada, o None si nunca se leyo."""

    @abstractmethod
    def guardar_transcripcion(self, documento_id: str, texto: str) -> None:
        """Cachea una lectura para que la pantalla abra instantanea."""

    @property
    @abstractmethod
    def es_muestra_parcial(self) -> bool:
        """True cuando esto es un subconjunto y no el corpus completo.

        La interfaz lo dice en voz alta. Presentar 4 documentos como si fueran
        los 12 seria exagerar la cobertura medida, y esa es exactamente la
        clase de afirmacion que este proyecto no se permite.
        """
