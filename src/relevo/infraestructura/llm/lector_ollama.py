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
from typing import Any

from relevo.dominio.puertos.lectura_documento import LectorDocumento
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


@dataclass(frozen=True)
class LectorOllama(LectorDocumento):
    """Un modelo de vision corriendo en Ollama.

    Implementa el puerto `LectorDocumento` del dominio. Antes era una clase
    suelta que casualmente tenia los metodos correctos; ahora la relacion es
    explicita y el sustituirla por otro adaptador esta garantizado por el tipo.
    """

    modelo: str = "qwen3-vl:4b"
    host: str = "http://localhost:11434"
    temperatura: float = 0.0
    """Cero a proposito. Transcribir no es tarea creativa: se quiere que la
    misma imagen produzca siempre la misma lectura, para poder auditarla."""

    opciones_extra: dict[str, object] = field(default_factory=dict)

    @property
    def nombre(self) -> str:
        return f"ollama/{self.modelo}"

    @property
    def requiere_red(self) -> bool:
        """False: Ollama corre en la misma maquina.

        Es lo que permite prometer que la lectura funciona con el wifi apagado.
        """
        return False

    def leer(self, imagen: bytes, instruccion: str) -> str:
        cuerpo = {
            "model": self.modelo,
            "prompt": instruccion,
            "images": [a_base64(imagen)],
            # ── POR QUE STREAMING SI EL RESULTADO SE QUIERE ENTERO ─────────
            # Con `stream: False`, Ollama calla durante toda la inferencia y
            # suelta el texto de golpe al final. En local da igual. Detras de
            # un tunel NO: Cloudflare corta con **HTTP 524** cualquier peticion
            # cuyo origen tarde mas de ~100 s en empezar a responder, y una
            # lectura de vision en CPU tarda ~150 s. La lectura en vivo desde
            # la aplicacion desplegada moria siempre, y el error que llegaba
            # era `OllamaNoDisponible`, que hacia pensar en Ollama caido cuando
            # Ollama estaba perfectamente y a medio trabajo.
            #
            # El limite de Cloudflare es al PRIMER BYTE, no al total. En
            # streaming Ollama emite el primer fragmento en un par de segundos
            # y sigue emitiendo, asi que la conexion nunca queda muda y la
            # peticion completa cuanto haga falta.
            #
            # Los fragmentos se reensamblan abajo: hacia fuera esta funcion
            # sigue devolviendo el texto completo de una pieza.
            "stream": True,
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
                return _reensamblar(r)
        except urllib.error.URLError as exc:
            raise OllamaNoDisponible(
                f"No se pudo hablar con Ollama en {self.host}. "
                f"Verifica que este corriendo (`ollama serve`) y que el modelo "
                f"'{self.modelo}' este descargado (`ollama pull {self.modelo}`). "
                f"Detalle: {exc}"
            ) from exc


def _reensamblar(respuesta: Any) -> str:
    """Junta los fragmentos de una respuesta en streaming de Ollama.

    En streaming, Ollama devuelve una linea de JSON por fragmento; cada una
    trae un trozo del texto en `response`, y la ultima `done: true`.

    Una linea ilegible se salta en vez de tumbar la lectura entera: perder un
    fragmento degrada la transcripcion, y la transcripcion la revisa una
    persona de todas formas. Abortar por eso desperdiciaria los dos minutos de
    trabajo que ya se hicieron.
    """
    trozos: list[str] = []
    for linea in respuesta:
        # Las lineas en blanco son el latido de `compuerta.py`: relleno emitido
        # mientras el modelo piensa, para que Cloudflare no corte la conexion.
        if not linea.strip():
            continue
        try:
            dato = json.loads(linea.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        # Un fallo que llega DENTRO del flujo, no como codigo HTTP: la
        # compuerta ya envio el 200 antes de saber como acabaria. Se convierte
        # en excepcion aqui mismo, porque devolver "" seria presentar un
        # documento no leido como un documento leido y vacio — precisamente el
        # fallo silencioso que este sistema existe para impedir.
        if dato.get("error"):
            raise OllamaNoDisponible(f"El modelo fallo a mitad: {dato['error']}")
        trozos.append(str(dato.get("response", "")))
        if dato.get("done"):
            break
    return "".join(trozos)


class OllamaNoDisponible(RuntimeError):
    """Ollama no responde. Se propaga a proposito.

    NO se degrada en silencio a una lectura vacia: un documento sin leer y un
    documento leido como vacio son cosas distintas, y confundirlas es
    exactamente el tipo de fallo silencioso que este sistema evita.
    """


@dataclass(frozen=True)
class LectorNulo(LectorDocumento):
    """No lee nada y lo dice. El respaldo honesto.

    Existe para que el sistema completo pueda correr sin Ollama, sin GPU y sin
    red — en la demo del hackathon, si el wifi falla o la maquina no da. Todos
    los campos salen null, van a revision humana, y la pantalla de verificacion
    se convierte en un formulario de captura manual.

    Suena a poco. Pero es la diferencia entre "el sistema no funciona" y "el
    sistema funciona en modo manual": el resto del flujo —validacion, catalogo,
    coherencia, priorizacion, Pasaporte, FHIR— sigue operando igual.
    """

    @property
    def nombre(self) -> str:
        return "sin-modelo"

    @property
    def requiere_red(self) -> bool:
        return False

    def leer(self, imagen: bytes, instruccion: str) -> str:  # noqa: ARG002
        """Devuelve texto vacio, y la diferencia con un fallo esta en el nombre.

        No lanza excepcion porque no ha fallado nada: es que no hay modelo. La
        interfaz consulta `nombre` y avisa que se entra en captura manual.
        """
        return ""


def _timeout_sondeo(host: str) -> int:
    """Cuanto esperar al sondeo segun donde este Ollama.

    Contra la propia maquina, 5 segundos sobran: o responde de inmediato o no
    esta. Contra un Ollama remoto —el caso del tunel en el despliegue— hay que
    dar mas margen: el primer viaje levanta la conexion del tunel y se ha visto
    tardar varios segundos. Con 5 se descartaria un Ollama que si estaba, y la
    pantalla diria "sin modelo" por impaciencia.
    """
    es_local = "localhost" in host or "127.0.0.1" in host
    return 5 if es_local else 15


def verificar_disponibilidad(
    host: str = "http://localhost:11434", timeout: float | None = None
) -> list[str]:
    """Modelos descargados en Ollama. Lista vacia si no responde.

    Se usa al arrancar la interfaz para elegir el mejor lector disponible en vez
    de fallar a mitad de la demo.

    `timeout` se pasa explicito cuando el sondeo es periodico: la pantalla
    consulta el estado cada pocos segundos y no puede permitirse bloquearse el
    tiempo largo que si tiene sentido antes de una lectura.
    """
    espera = _timeout_sondeo(host) if timeout is None else timeout
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=espera) as r:
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
    host: str = "http://localhost:11434", timeout: float | None = None
) -> tuple[object, object | None]:
    """Elige el mejor par (principal, contraste) entre lo que hay instalado.

    El contraste se busca en una familia DISTINTA a la del principal. Si lo
    unico instalado son dos tamanios del mismo modelo, se devuelve un solo
    lector y `None`: es preferible declarar que no hay segunda opinion a
    fabricar una que no lo es.

    Si no hay nada, devuelve `LectorNulo` y el sistema entra en modo manual en
    vez de romperse.
    """
    disponibles = verificar_disponibilidad(host, timeout=timeout)
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
