"""Extraccion de campos SIN plantilla, desde cualquier documento de referencia.

POR QUE SIN PLANTILLA
La primera version recortaba cada campo por coordenadas conocidas. Se cayo por
una razon de campo: en el INSN **no llega un solo formulario**. Llegan Hojas de
Referencia de establecimientos distintos, informes medicos, ordenes, y cada uno
con su maquetado. Un mapa de coordenadas serviria para uno y fallaria con el
resto.

La salida es invertir la pregunta. En vez de:

    "que dice el rectangulo (1300, 470, 340, 55)"     ← depende del maquetado

se pregunta:

    "en este documento, cual es el DNI del paciente"   ← no depende de nada

El modelo localiza el campo; nosotros no le decimos donde esta. Lo que SI
hacemos es exigirle un esquema fijo de salida, decirle exactamente que formato
tiene cada campo, y prohibirle adivinar.

LO QUE NO CAMBIA
`VerificadorExtraccion` no se entera de nada de esto. Valida VALORES, no
posiciones: un DNI de siete digitos es invalido venga de donde venga, y un
CIE-10 fuera del catalogo tampoco existe aunque el documento sea otro. La capa
que impide el error silencioso es independiente del maquetado, y por eso
sobrevive intacta al cambio.

REGLA DE ORO DEL PROMPT
Se le pide al modelo que devuelva `null` cuando no puede leer, y se le prohibe
completar, corregir o inferir. Un `null` es un campo que va a revision humana:
molesto pero seguro. Un valor inventado con aspecto legitimo es exactamente el
error silencioso que este sistema existe para impedir.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


# ─────────────────────────────────────────────────────────────────────────────
# El puerto
# ─────────────────────────────────────────────────────────────────────────────


class LectorDocumento(Protocol):
    """Lo minimo que tiene que saber hacer un lector de documentos.

    Implementaciones previstas: Ollama con modelo de vision, una API gratuita, o
    `LectorNulo` para cuando no hay ninguna disponible. El resto del sistema
    habla con este protocolo y no sabe cual esta detras.
    """

    nombre: str

    def leer(self, imagen: bytes, instruccion: str) -> str:
        """Devuelve la respuesta cruda del modelo, sin interpretar."""
        ...


@dataclass(frozen=True, slots=True)
class CampoPedido:
    """Que campo se pide y como se le explica al modelo que es.

    `descripcion` y `formato` van dentro del prompt: cuanto mas concreto, menos
    margen de invencion. `sinonimos` ayuda cuando el mismo dato aparece con
    etiquetas distintas segun el establecimiento que emitio el documento.
    """

    nombre: str
    descripcion: str
    formato: str = ""
    sinonimos: tuple[str, ...] = ()
    ejemplo: str = ""

    def linea_prompt(self) -> str:
        partes = [f'"{self.nombre}": {self.descripcion}']
        if self.sinonimos:
            partes.append(f"puede aparecer como: {', '.join(self.sinonimos)}")
        if self.formato:
            partes.append(f"formato: {self.formato}")
        if self.ejemplo:
            partes.append(f"ejemplo: {self.ejemplo}")
        return "  - " + ". ".join(partes)


# ─────────────────────────────────────────────────────────────────────────────
# El prompt
# ─────────────────────────────────────────────────────────────────────────────

_INSTRUCCION_BASE = """Eres un asistente que transcribe documentos clinicos peruanos.

Este documento puede ser una Hoja de Referencia del MINSA, un informe medico, una
epicrisis o cualquier otro documento de derivacion. El maquetado varia entre
establecimientos: no asumas posiciones fijas. Busca cada dato por su etiqueta o
por su contexto.

CAMPOS A EXTRAER:
{campos}

REGLAS ABSOLUTAS — el incumplimiento de cualquiera invalida la respuesta:

1. Transcribe LITERALMENTE lo que esta escrito. No corrijas ortografia, no
   completes abreviaturas, no normalices formatos.
2. Si un campo NO aparece en el documento, o no lo puedes leer con seguridad,
   devuelve null. NUNCA inventes, deduzcas ni completes un valor.
3. Si dudas entre dos lecturas posibles, devuelve null. Un null se revisa; un
   valor equivocado con aspecto correcto no se detecta.
4. NO calcules nada. Si la edad no esta escrita, es null aunque este la fecha de
   nacimiento.
5. Las dosis de medicamentos se copian caracter por caracter tal como aparecen.
   Si un digito no es legible, el campo entero es null.

ABREVIATURAS CLINICAS FRECUENTES EN ESTE CONTEXTO:
{abreviaturas}

Responde UNICAMENTE con un objeto JSON, sin texto antes ni despues, sin bloques
de codigo. Las claves son exactamente los nombres de campo listados arriba."""


# Abreviaturas tomadas de la historia clinica del INSN San Borja
# (RD N° 000109-2021-DG-INSN-SB). Las ambiguas se declaran como ambiguas para
# que el modelo no elija por su cuenta.
ABREVIATURAS_INSN: Mapping[str, str] = {
    "PC": "AMBIGUO: perimetro cefalico (si aparece junto a peso y talla) o paralisis cerebral (si aparece como diagnostico). Si no puedes decidir por el contexto, no lo expandas",
    "SOMA": "sistema osteomuscular",
    "TCSC": "tejido celular subcutaneo",
    "MTD": "miembro toracico derecho",
    "MTI": "miembro toracico izquierdo",
    "LME": "lactancia materna exclusiva",
    "HGT": "hemoglucotest",
    "RAM": "reaccion adversa a medicamentos",
    "FUR": "fecha de ultima regla",
    "CPN": "control prenatal",
    "AREG": "aparente regular estado general",
    "TEC": "traumatismo encefalocraneano",
    "SatO2": "saturacion de oxigeno",
    "FR": "frecuencia respiratoria",
    "FC": "frecuencia cardiaca",
    "PA": "presion arterial",
    "EE.SS.": "establecimiento de salud",
    "UPS": "unidad productora de servicios",
}


def construir_instruccion(
    campos: Sequence[CampoPedido],
    abreviaturas: Mapping[str, str] | None = None,
) -> str:
    abrev = abreviaturas if abreviaturas is not None else ABREVIATURAS_INSN
    return _INSTRUCCION_BASE.format(
        campos="\n".join(c.linea_prompt() for c in campos),
        abreviaturas="\n".join(f"  {k} = {v}" for k, v in abrev.items()),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Parseo defensivo
# ─────────────────────────────────────────────────────────────────────────────

_BLOQUE_JSON = re.compile(r"\{.*\}", re.DOTALL)


def parsear_respuesta(
    crudo: str, campos: Sequence[CampoPedido]
) -> dict[str, str | None]:
    """Extrae el JSON de la respuesta del modelo, tolerando basura alrededor.

    Los modelos pequenos envuelven el JSON en explicaciones o en bloques de
    codigo por mucho que se les prohiba. Se busca el primer objeto balanceado en
    vez de exigir una respuesta limpia.

    Un campo que el modelo no devolvio se trata como None — igual que si hubiera
    dicho que no puede leerlo. Nunca se rellena con nada.
    """
    texto = crudo.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```[a-z]*\n?|\n?```$", "", texto, flags=re.MULTILINE)

    m = _BLOQUE_JSON.search(texto)
    datos: dict[str, object] = {}
    if m:
        try:
            cargado = json.loads(m.group(0))
            if isinstance(cargado, dict):
                datos = cargado
        except json.JSONDecodeError:
            datos = {}

    resultado: dict[str, str | None] = {}
    for campo in campos:
        valor = datos.get(campo.nombre)
        if valor is None or isinstance(valor, bool):
            resultado[campo.nombre] = None
        elif isinstance(valor, (int, float)):
            resultado[campo.nombre] = str(valor)
        else:
            limpio = str(valor).strip()
            # Los modelos escriben "null", "N/A", "no legible" en vez de null
            if limpio.lower() in {
                "null", "none", "n/a", "na", "-", "--", "", "no legible",
                "ilegible", "no aparece", "no especificado", "desconocido",
            }:
                resultado[campo.nombre] = None
            else:
                resultado[campo.nombre] = limpio
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# El extractor
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ResultadoLectura:
    """Lo que devuelve una pasada de lectura, antes de verificar."""

    valores: Mapping[str, str | None]
    lector: str
    crudo: str = ""

    @property
    def leidos(self) -> int:
        return sum(1 for v in self.valores.values() if v)


@dataclass(frozen=True, slots=True)
class ExtractorDocumento:
    """Lee un documento con uno o dos lectores y entrega valores crudos.

    Con DOS lectores distintos se obtiene una senal de confianza que los modelos
    locales no exponen: donde las dos lecturas coinciden, hay acuerdo
    independiente; donde discrepan, el campo va a revision. Es lo mismo que hace
    un servicio de transcripcion con doble digitador, y sale gratis porque los
    dos modelos son locales.
    """

    campos: tuple[CampoPedido, ...]
    lector_principal: LectorDocumento
    lector_contraste: LectorDocumento | None = None
    abreviaturas: Mapping[str, str] | None = None

    def leer_imagen(self, ruta: Path | bytes) -> tuple[ResultadoLectura, ResultadoLectura | None]:
        imagen = ruta.read_bytes() if isinstance(ruta, Path) else ruta
        instruccion = construir_instruccion(self.campos, self.abreviaturas)

        crudo = self.lector_principal.leer(imagen, instruccion)
        principal = ResultadoLectura(
            valores=parsear_respuesta(crudo, self.campos),
            lector=self.lector_principal.nombre,
            crudo=crudo,
        )

        contraste = None
        if self.lector_contraste is not None:
            crudo2 = self.lector_contraste.leer(imagen, instruccion)
            contraste = ResultadoLectura(
                valores=parsear_respuesta(crudo2, self.campos),
                lector=self.lector_contraste.nombre,
                crudo=crudo2,
            )
        return principal, contraste


def a_base64(imagen: bytes) -> str:
    return base64.b64encode(imagen).decode("ascii")
