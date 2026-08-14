"""Puertos de generacion de texto y de documentos.

PLAN_TECNICO §8.1. Cuatro adaptadores implementan `GeneradorResumen`: `SinLLM`,
`Groq`, `Gemini` y `Ollama`, elegidos por la variable `RELEVO_LLM_PROVIDER`.

`SinLLM` se construye PRIMERO y funciona sin red. No es un respaldo de segunda:
es lo que se demuestra si el wifi del evento falla, que es lo que va a pasar.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from relevo.dominio.entidades.diagnostico import Medicamento
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import Pasaporte


@dataclass(frozen=True, slots=True)
class DatosExtraidos:
    """Lo que se logro sacar del texto libre de la historia.

    Todo campo es opcional a proposito: extraer de menos es aceptable, inventar
    no lo es.
    """

    diagnosticos_texto: tuple[str, ...] = field(default_factory=tuple)
    medicamentos: tuple[Medicamento, ...] = field(default_factory=tuple)
    alergias: tuple[str, ...] = field(default_factory=tuple)
    dispositivos_texto: tuple[str, ...] = field(default_factory=tuple)
    descartados: tuple[str, ...] = field(default_factory=tuple)
    """Lo que el modelo produjo y la verificacion rechazo, con su motivo.

    Se conserva y se muestra: que el modelo haya alucinado una dosis es
    informacion util para quien revisa, no basura que convenga esconder.
    """

    @property
    def hay_descartes(self) -> bool:
        return bool(self.descartados)


class GeneradorResumen(ABC):
    """Las tres tareas de lenguaje del sistema (PLAN_TECNICO §8.2).

    VERIFICACION ANTIFABULACION, OBLIGATORIA EN TODA IMPLEMENTACION: toda dosis
    extraida debe aparecer LITERALMENTE en el texto fuente. Si no aparece, se
    descarta y el medicamento queda marcado para completar a mano.

    No es una recomendacion. Inventar una dosis es el peor fallo posible de
    este sistema: el medico firma rapido, la familia lee el Pasaporte como si
    fuera cierto, y nadie se entera hasta que alguien toma mal un farmaco.
    """

    @abstractmethod
    def extraer_estructurado(self, texto: str, seccion: str = "") -> DatosExtraidos:
        """Tolerancia BAJA: lo que no valide se descarta.

        `seccion` importa: 'PC' en examen fisico es perimetro cefalico y en
        diagnosticos es paralisis cerebral. Sin la seccion no se puede
        resolver, y adivinar esta prohibido (PLAN_TECNICO §8.3).
        """

    @abstractmethod
    def resumir_clinico(self, paciente: Paciente) -> str:
        """Una pagina en lenguaje tecnico, para el medico que va a recibir al
        paciente. Tolerancia media: el medico firma."""

    @abstractmethod
    def traducir_ciudadano(self, resumen: str, edad: int) -> str:
        """El mismo contenido en las palabras del paciente, segun tenga 14, 16
        o 17 anios. Tolerancia media: el medico firma."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """'SinLLM', 'Groq (llama-3.3-70b)'. Se muestra en la interfaz y se
        registra junto al documento: saber que motor escribio un texto que un
        medico firmo es parte de la trazabilidad."""

    @property
    @abstractmethod
    def requiere_red(self) -> bool:
        """False solo en `SinLLM` y en `Ollama` local.

        El sistema comprueba esto antes de la demo: si el wifi cayo, se cambia
        de adaptador sin tocar nada mas.
        """


class GeneradorDocumento(ABC):
    """Convierte un Pasaporte en un archivo imprimible.

    Toda implementacion llama a `pasaporte.exigir_firma()` antes de producir el
    documento definitivo. El borrador se puede previsualizar; el entregable no
    existe sin firma.
    """

    @abstractmethod
    def generar(self, pasaporte: Pasaporte, ruta_destino: str) -> str:
        """Escribe el documento y devuelve la ruta final.

        Debe salir legible impreso en blanco y negro: en el INSN se imprime en
        laser monocroma, no en pantalla.
        """

    @abstractmethod
    def generar_borrador(self, pasaporte: Pasaporte, ruta_destino: str) -> str:
        """Previsualizacion para la pantalla de revision del medico.

        Sale marcado como BORRADOR de forma inequivoca, para que no se
        confunda con el documento firmado si alguien lo imprime.
        """


class GeneradorCodigoQR(ABC):
    """El QR que lleva a la version digital del Pasaporte.

    Obligatorio en las tres versiones (PLAN_TECNICO §9) y verificado a mano:
    tiene que escanear desde un telefono real, no solo generarse sin error.
    """

    @abstractmethod
    def generar(self, contenido: str, ruta_destino: str) -> str:
        ...
