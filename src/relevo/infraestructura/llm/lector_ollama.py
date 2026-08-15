"""Lectores de documento sobre Ollama. Gratis, local, y los datos no salen.

POR QUE OLLAMA Y NO UNA API
No es solo el costo. Un escaneo de Hoja de Referencia trae DNI, partida de
nacimiento, afiliacion al SIS y el DNI del tutor. Mandar eso a un servicio
externo deja de ser una decision de arquitectura y pasa a ser un problema legal.
Corriendo local, el documento nunca sale de la maquina.

Y el volumen lo hace trivial: del orden de un paciente por dia habil, en proceso
por lotes. Aunque cada documento tomara dos minutos, son unas ocho horas de
computo AL ANIO.

QUE MODELO USAR
Ollama tiene modelos de vision especializados en documentos que no hace falta
afinar ni entrenar:

    glm-ocr           OCR multimodal para documentos complejos. Primera opcion.
    deepseek-ocr:3b   OCR eficiente en tokens. Rapido y liviano.
    qwen3-vl:4b       Vision-lenguaje general, bueno siguiendo esquemas JSON.
    qwen3-vl:8b       Lo mismo, mas preciso, mas VRAM.
    minicpm-v4.5:8b   Solido en documentos densos.
    minicpm-v4.6:1b   El ultimo recurso: corre en casi cualquier maquina.
    medgemma:4b       Especializado en texto e imagenes MEDICAS. Para los campos
                      clinicos de texto libre, donde el vocabulario importa.

ESTRATEGIA RECOMENDADA — dos lectores distintos, no dos pasadas del mismo:

    principal   glm-ocr o deepseek-ocr   (fuerte en transcripcion literal)
    contraste   qwen3-vl:4b              (fuerte siguiendo el esquema)

Donde los dos coinciden hay acuerdo independiente. Donde discrepan, el campo va
a revision humana. Es doble digitacion, gratis.

Y para los campos clinicos de texto libre (anamnesis, tratamiento), una tercera
pasada con `medgemma` aporta vocabulario medico que un modelo general no tiene.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from relevo.infraestructura.llm.extractor import a_base64

TIMEOUT_SEGUNDOS = 300  # un modelo de vision en CPU puede tardar minutos


# Sugerencias por VRAM disponible. No es una regla: es un punto de partida.
#
# OJO CON LA CLAVE `sin_gpu`: dice "sin GPU", no "maquina debil". En una CPU
# moderna con RAM libre suficiente, lo que limita no es que se pueda, es que
# tarda. Y aqui tardar no importa: el volumen es del orden de un paciente por
# dia habil, asi que un minuto por documento son unas ocho horas AL ANIO.
#
# Por eso, sin GPU pero con ~8 GB de RAM libre, la fila correcta a mirar es la
# de "8gb": `glm-ocr` son 0.9B de parametros y 2.2 GB en disco — pesa menos que
# muchos modelos de la fila "4gb" y esta especializado en documentos. Bajar a
# `minicpm-v4.6:1b` por no tener GPU es regalar calidad de lectura a cambio de
# una velocidad que no necesitamos.
RECOMENDACION_POR_VRAM: dict[str, tuple[str, str]] = {
    "sin_gpu": ("minicpm-v4.6:1b", "deepseek-ocr:3b"),
    "4gb": ("deepseek-ocr:3b", "qwen3-vl:2b"),
    "8gb": ("glm-ocr", "qwen3-vl:4b"),
    "12gb": ("glm-ocr", "qwen3-vl:8b"),
    "16gb+": ("qwen3-vl:8b", "minicpm-v4.5:8b"),
}

# Sugerencia cuando se corre en CPU, indexada por RAM LIBRE (no total: lo que
# de verdad queda despues del navegador y el editor).
RECOMENDACION_POR_RAM_LIBRE_CPU: dict[str, tuple[str, str]] = {
    "menos_de_4gb": ("glm-ocr", "minicpm-v4.6:1b"),
    "4gb": ("glm-ocr", "qwen3-vl:2b"),
    "8gb+": ("glm-ocr", "qwen3-vl:4b"),
}


@dataclass(frozen=True, slots=True)
class LectorOllama:
    """Un modelo de vision corriendo en Ollama."""

    modelo: str = "qwen3-vl:4b"
    host: str = "http://localhost:11434"
    temperatura: float = 0.0
    """Cero a proposito. Transcribir no es tarea creativa: se quiere que la
    misma imagen produzca siempre la misma lectura, para poder auditarla."""

    opciones_extra: dict[str, object] = field(default_factory=dict)

    @property
    def nombre(self) -> str:
        return f"ollama/{self.modelo}"

    def leer(self, imagen: bytes, instruccion: str) -> str:
        cuerpo = {
            "model": self.modelo,
            "prompt": instruccion,
            "images": [a_base64(imagen)],
            "stream": False,
            # Pide al modelo no razonar antes de responder.
            #
            # LO QUE SE MIDIO: los Qwen3 son modelos de razonamiento y Ollama
            # devuelve ese razonamiento en un campo `thinking` aparte de
            # `response`. Con un prompt corto de una linea, `qwen3-vl:4b`
            # devuelve el JSON pedido en ~15 s en esta maquina (CPU, sin GPU).
            #
            # LO QUE NO ARREGLA, Y HAY QUE DECIRLO: con el prompt largo de
            # `construir_instruccion` —catalogo de campos mas glosario de
            # abreviaturas— `qwen3-vl:4b` sigue devolviendo `response` VACIO
            # tras ~200 s, con este campo ya puesto. De modo que el
            # razonamiento no era la causa unica, o el flag no se honra en
            # esta version de Ollama. Queda sin diagnosticar.
            #
            # Se deja puesto porque no hace danio —los modelos que no razonan
            # lo ignoran— pero que nadie le atribuya una mejora que no se
            # midio. `glm-ocr` si responde con el prompt largo.
            #
            # Y NO se usa `thinking` como respuesta de repuesto aunque venga
            # lleno: es el borrador en voz alta del modelo, no su conclusion.
            # Sacar un dato clinico de ahi seria justo la clase de invencion
            # que este sistema existe para impedir.
            "think": False,
            "options": {
                "temperature": self.temperatura,
                "num_predict": 2048,
                **self.opciones_extra,
            },
        }
        peticion = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(peticion, timeout=TIMEOUT_SEGUNDOS) as r:
                return str(json.loads(r.read().decode("utf-8")).get("response", ""))
        except urllib.error.URLError as exc:
            raise OllamaNoDisponible(
                f"No se pudo hablar con Ollama en {self.host}. "
                f"Verifica que este corriendo (`ollama serve`) y que el modelo "
                f"'{self.modelo}' este descargado (`ollama pull {self.modelo}`). "
                f"Detalle: {exc}"
            ) from exc


class OllamaNoDisponible(RuntimeError):
    """Ollama no responde. Se propaga a proposito.

    NO se degrada en silencio a una lectura vacia: un documento sin leer y un
    documento leido como vacio son cosas distintas, y confundirlas es
    exactamente el tipo de fallo silencioso que este sistema evita.
    """


@dataclass(frozen=True, slots=True)
class LectorNulo:
    """No lee nada y lo dice. El respaldo honesto.

    Existe para que el sistema completo pueda correr sin Ollama, sin GPU y sin
    red — en la demo del hackathon, si el wifi falla o la maquina no da. Todos
    los campos salen null, van a revision humana, y la pantalla de verificacion
    se convierte en un formulario de captura manual.

    Suena a poco. Pero es la diferencia entre "el sistema no funciona" y "el
    sistema funciona en modo manual": el resto del flujo —validacion, catalogo,
    coherencia, priorizacion, Pasaporte, FHIR— sigue operando igual.
    """

    nombre: str = "sin-modelo"

    def leer(self, imagen: bytes, instruccion: str) -> str:  # noqa: ARG002
        return "{}"


def verificar_disponibilidad(host: str = "http://localhost:11434") -> list[str]:
    """Modelos descargados en Ollama. Lista vacia si no responde.

    Se usa al arrancar la interfaz para elegir el mejor lector disponible en vez
    de fallar a mitad de la demo.
    """
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as r:
            datos = json.loads(r.read().decode("utf-8"))
        return [m["name"] for m in datos.get("models", [])]
    except Exception:  # noqa: BLE001 — sondeo, cualquier fallo es "no hay"
        return []


PREFERENCIA = (
    "glm-ocr",
    "deepseek-ocr:3b",
    "qwen3-vl:8b",
    "qwen3-vl:4b",
    "minicpm-v4.5:8b",
    "qwen3-vl:2b",
    "minicpm-v4.6:1b",
    # Multimodales generales. No son especialistas en documentos, pero sirven
    # de contraste y de respaldo, y mucha gente ya los tiene descargados.
    "medgemma:4b",
    "gemma3:4b",
)


# A que familia pertenece cada modelo. Dos modelos de la MISMA familia son el
# mismo modelo en dos tamanios: comparten arquitectura y datos de entrenamiento,
# asi que se equivocan en los mismos sitios.
#
# Eso rompe la premisa de la doble lectura. El valor de leer dos veces no esta
# en leer dos veces: esta en que las dos lecturas sean INDEPENDIENTES, para que
# coincidir signifique algo. Dos modelos que comparten el mismo punto ciego
# coinciden en el error y le ponen sello verde a un campo mal leido — que es
# peor que no haber contrastado, porque produce confianza injustificada.
#
# `medgemma` va marcado como familia gemma a proposito: esta construido SOBRE
# Gemma, por mucho que el nombre y el dominio medico sugieran otra cosa.
FAMILIA: dict[str, str] = {
    "glm-ocr": "glm",
    "deepseek-ocr": "deepseek",
    "qwen3-vl": "qwen",
    "minicpm-v4.5": "minicpm",
    "minicpm-v4.6": "minicpm",
    "medgemma": "gemma",
    "medgemma1.5": "gemma",
    "gemma3": "gemma",
}


def familia_de(modelo: str) -> str:
    """La familia de un modelo instalado. El propio nombre si no se reconoce.

    Devolver el nombre completo ante lo desconocido es el respaldo prudente:
    dos modelos que no sabemos emparentar se tratan como independientes, que es
    el supuesto que no bloquea el contraste.
    """
    base = modelo.split(":")[0]
    return FAMILIA.get(base, base)


def elegir_lectores(
    host: str = "http://localhost:11434",
) -> tuple[object, object | None]:
    """Elige el mejor par (principal, contraste) entre lo que hay instalado.

    El contraste se busca en una familia DISTINTA a la del principal. Si lo
    unico instalado son dos tamanios del mismo modelo, se devuelve un solo
    lector y `None`: es preferible declarar que no hay segunda opinion a
    fabricar una que no lo es.

    Si no hay nada, devuelve `LectorNulo` y el sistema entra en modo manual en
    vez de romperse.
    """
    disponibles = verificar_disponibilidad(host)
    if not disponibles:
        return LectorNulo(), None

    def coincide(pref: str) -> str | None:
        for d in disponibles:
            if d == pref or d.startswith(pref.split(":")[0] + ":"):
                return d
        return None

    elegidos = [m for p in PREFERENCIA if (m := coincide(p))]
    # Sin duplicados y conservando el orden de preferencia
    unicos: list[str] = []
    for m in elegidos:
        if m not in unicos:
            unicos.append(m)

    if not unicos:
        # Hay modelos instalados pero ninguno conocido. Se usa el primero: puede
        # no ser multimodal y fallar, pero fallar es informativo y el respaldo
        # manual sigue detras.
        return LectorOllama(modelo=disponibles[0], host=host), None

    principal = unicos[0]
    familia_principal = familia_de(principal)
    contraste = next(
        (m for m in unicos[1:] if familia_de(m) != familia_principal),
        None,
    )

    if contraste is None:
        return LectorOllama(modelo=principal, host=host), None
    return (
        LectorOllama(modelo=principal, host=host),
        LectorOllama(modelo=contraste, host=host),
    )
