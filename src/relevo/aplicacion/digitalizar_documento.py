"""Casos de uso de digitalizacion de documentos.

Orquestan el paso completo y no saben quien esta del otro lado:

    imagen -> lector (puerto) -> texto -> extraccion -> campos -> revision

Antes esto vivia dentro de `app.py`, mezclado con el maquetado de Streamlit.
Eso tenia dos costes concretos: no se podia probar sin levantar un navegador, y
cambiar la interfaz obligaba a reescribir la orquestacion. Ahora la pantalla
pide `ejecutar()` y pinta el resultado.

Solo importa `dominio`. `tests/test_arquitectura.py` lo verifica.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from relevo.dominio.puertos.lectura_documento import LectorDocumento

# La instruccion que se le da al modelo. Deliberadamente NO le pide JSON:
# medido sobre el corpus, un modelo de OCR ignora el esquema pedido y devuelve
# su propia estructura, pero transcribe muy bien cuando se le pide transcribir.
INSTRUCCION_TRANSCRIPCION = (
    "Transcribe TODO el texto que veas en este documento clinico, respetando "
    "las etiquetas de cada campo tal como aparecen. No corrijas la ortografia, "
    "no completes abreviaturas y no calcules nada. Si un dato no es legible, "
    "escribe la etiqueta y dejalo vacio."
)


@dataclass(frozen=True, slots=True)
class CampoDigitalizado:
    """Un campo leido del documento, con por que se acepto o se rechazo.

    Es el objeto de transporte hacia la interfaz: lleva el valor, el texto
    crudo que produjo el modelo y el motivo del rechazo en castellano llano.
    Los tres hacen falta — mostrar un campo vacio sin decir por que obliga a la
    persona a adivinar si el sistema fallo o el documento no traia el dato.
    """

    nombre: str
    valor: str | None
    crudo: str = ""
    motivo: str = ""
    corregido_desde: str | None = None
    """Valor original cuando el catalogo corrigio la lectura.

    Se propaga hasta el acta: una correccion automatica sin constancia es
    indistinguible de una alucinacion.
    """

    @property
    def requiere_revision(self) -> bool:
        return self.valor is None

    @property
    def fue_corregido(self) -> bool:
        return self.corregido_desde is not None and self.valor is not None


@dataclass(frozen=True, slots=True)
class DocumentoDigitalizado:
    """El resultado completo de leer un documento."""

    documento_id: str
    texto: str
    campos: tuple[CampoDigitalizado, ...] = field(default_factory=tuple)
    lector: str = ""
    desde_cache: bool = False

    @property
    def valores(self) -> dict[str, str | None]:
        return {c.nombre: c.valor for c in self.campos}

    @property
    def requieren_revision(self) -> tuple[CampoDigitalizado, ...]:
        return tuple(c for c in self.campos if c.requiere_revision)

    @property
    def tasa_captura(self) -> float:
        if not self.campos:
            return 0.0
        return sum(1 for c in self.campos if c.valor is not None) / len(self.campos)


class DigitalizarDocumento:
    """Lee un documento escaneado y devuelve sus campos con su veredicto.

    `extraer` es la funcion que convierte texto en campos. Se recibe como
    dependencia y no se importa: asi el caso de uso no depende del modulo de
    reglas concreto, y se puede probar con una funcion trivial.
    """

    def __init__(
        self,
        lector: LectorDocumento,
        extraer: Callable[[str], Sequence[CampoDigitalizado]],
    ) -> None:
        self._lector = lector
        self._extraer = extraer

    @property
    def lector(self) -> str:
        return self._lector.nombre

    @property
    def requiere_red(self) -> bool:
        return self._lector.requiere_red

    def ejecutar(self, documento_id: str, imagen: bytes) -> DocumentoDigitalizado:
        """Lee la imagen con el modelo. Cualquier fallo del lector se propaga."""
        texto = self._lector.leer(imagen, INSTRUCCION_TRANSCRIPCION)
        return self.desde_texto(documento_id, texto, desde_cache=False)

    def desde_texto(
        self, documento_id: str, texto: str, desde_cache: bool = True
    ) -> DocumentoDigitalizado:
        """Extrae los campos de una transcripcion ya obtenida.

        Existe separado de `ejecutar` porque la transcripcion cuesta minutos en
        CPU y la extraccion es instantanea: separarlas permite guardar la
        primera y volver a correr la segunda cada vez que cambian las reglas,
        sin pagar el modelo de nuevo. Tambien es lo que hace que la pantalla
        abra al instante en una demo.
        """
        return DocumentoDigitalizado(
            documento_id=documento_id,
            texto=texto,
            campos=tuple(self._extraer(texto)),
            lector=self._lector.nombre,
            desde_cache=desde_cache,
        )


@dataclass(frozen=True, slots=True)
class CampoConfirmado:
    """Un campo tal como quedo tras la revision humana."""

    nombre: str
    valor_final: str
    valor_leido: str
    origen: str
    """AUTOMATICO, CORREGIDO o VACIO. Es el contenido real del acta: sin esta
    distincion, el documento seria indistinguible de una transcripcion sin
    revisar."""


@dataclass(frozen=True, slots=True)
class ActaDigitalizacion:
    documento_id: str
    revisor: str
    momento: datetime
    campos: tuple[CampoConfirmado, ...]

    @property
    def automaticos(self) -> int:
        return sum(1 for c in self.campos if c.origen == "AUTOMATICO")

    @property
    def corregidos(self) -> int:
        return sum(1 for c in self.campos if c.origen == "CORREGIDO")

    @property
    def vacios(self) -> int:
        return sum(1 for c in self.campos if c.origen == "VACIO")


class ConfirmarDigitalizacion:
    """Cierra la digitalizacion de un documento con la firma de quien reviso.

    `generar_pdf` se recibe como dependencia: el caso de uso decide QUE va en el
    acta, no como se dibuja. Cambiar reportlab por otra cosa no lo toca.
    """

    def __init__(
        self,
        generar_pdf: Callable[[str, list[dict[str, str]], str, datetime], bytes],
    ) -> None:
        self._generar_pdf = generar_pdf

    def ejecutar(
        self,
        documento_id: str,
        valores_finales: dict[str, str],
        valores_leidos: dict[str, str | None],
        revisor: str,
        momento: datetime | None = None,
    ) -> tuple[ActaDigitalizacion, bytes]:
        if not revisor.strip():
            raise ValueError(
                "No se puede emitir un acta sin quien la revisa: la trazabilidad "
                "es el contenido del documento, no un adorno."
            )
        momento = momento or datetime.now()

        campos: list[CampoConfirmado] = []
        for nombre, final in valores_finales.items():
            leido = valores_leidos.get(nombre) or ""
            limpio = final.strip()
            if not limpio:
                origen = "VACIO"
            elif limpio != leido:
                origen = "CORREGIDO"
            else:
                origen = "AUTOMATICO"
            campos.append(
                CampoConfirmado(
                    nombre=nombre,
                    valor_final=limpio,
                    valor_leido=leido,
                    origen=origen,
                )
            )

        acta = ActaDigitalizacion(
            documento_id=documento_id,
            revisor=revisor.strip(),
            momento=momento,
            campos=tuple(campos),
        )
        pdf = self._generar_pdf(
            documento_id,
            [
                {
                    "nombre": c.nombre,
                    "valor_final": c.valor_final,
                    "valor_leido": c.valor_leido,
                    "estado": c.origen,
                }
                for c in acta.campos
            ],
            acta.revisor,
            acta.momento,
        )
        return acta, pdf
