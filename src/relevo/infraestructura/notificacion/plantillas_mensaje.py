"""Las plantillas de los mensajes a la familia, en un solo sitio.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTAN AQUI Y NO EN LA PANTALLA
═══════════════════════════════════════════════════════════════════════════════

Estaban escritas dentro de `app.py`, junto a un `wa.me` construido a mano. Eso
significaba que el enlace que la gente usaba de verdad **no pasaba por
`CanalWhatsAppEnlace`, y por tanto no pasaba por la guarda de privacidad.**

No habia fuga —las tres plantillas estaban limpias— pero el test de privacidad
iba a certificar el adaptador, iba a pasar en verde, y el canal vivo iba a
seguir sin proteccion. **Un test que certifica el canal equivocado es peor que
no tener test:** da una seguridad que no existe.

Ahora hay una sola ruta. Todo WhatsApp pasa por el adaptador, y el adaptador
rechaza cualquier mensaje que declare datos clinicos aunque el llamante insista.

═══════════════════════════════════════════════════════════════════════════════
LA REGLA DE PRIVACIDAD
═══════════════════════════════════════════════════════════════════════════════

Ningun mensaje puede contener diagnosticos, codigos CIE-10, nombres de
medicamentos, dosis ni resultados. Un WhatsApp queda en la pantalla de bloqueo
de un telefono que puede estar en manos de cualquiera, y se reenvia sin
pensarlo.

Por eso los mensajes hablan del TRAMITE y nunca de la CONDICION: "su Pasaporte
esta listo" en vez de "su Pasaporte de fibrosis quistica esta listo".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TipoMensajeFamilia(Enum):
    """Los tres mensajes que el sistema sabe preparar para una familia."""

    VERIFICAR_CONTACTO = "verificar_contacto"
    CITAR_A_CONSULTA = "citar_a_consulta"
    PASAPORTE_LISTO = "pasaporte_listo"

    @property
    def etiqueta(self) -> str:
        return {
            TipoMensajeFamilia.VERIFICAR_CONTACTO: (
                "Actualizacion de telefono de contacto"
            ),
            TipoMensajeFamilia.CITAR_A_CONSULTA: (
                "Citacion a consulta de preparacion de transicion"
            ),
            TipoMensajeFamilia.PASAPORTE_LISTO: "Pasaporte listo para entrega",
        }[self]


@dataclass(frozen=True, slots=True)
class PlantillaMensaje:
    """Un texto para la familia, con su bandera de privacidad.

    `contiene_datos_clinicos` va en la plantilla y no lo decide quien la usa:
    si dependiera del llamante, bastaria un descuido en una pantalla para que
    un diagnostico saliera por un canal abierto. Aqui la bandera viaja con el
    texto, y el adaptador la comprueba antes de generar nada.
    """

    tipo: TipoMensajeFamilia
    asunto: str
    plantilla: str
    contiene_datos_clinicos: bool = False

    def componer(self, referencia_paciente: str) -> str:
        """El texto final.

        Se le pasa el IDENTIFICADOR del paciente, no su nombre ni su
        diagnostico. La familia sabe de quien se le habla; un tercero que lea
        la pantalla de bloqueo, no.
        """
        return self.plantilla.format(paciente=referencia_paciente).strip()


PLANTILLAS: dict[TipoMensajeFamilia, PlantillaMensaje] = {
    TipoMensajeFamilia.VERIFICAR_CONTACTO: PlantillaMensaje(
        tipo=TipoMensajeFamilia.VERIFICAR_CONTACTO,
        asunto="Verificacion de telefono de contacto",
        plantilla=(
            "Estimada familia de {paciente}, le saludamos del Instituto Nacional "
            "de Salud del Nino San Borja. Nos comunicamos para validar su numero "
            "telefonico de contacto y asegurar la continuidad de su atencion. "
            "Por favor, confirmenos si este sigue siendo su numero principal. "
            "Muchas gracias."
        ),
        contiene_datos_clinicos=False,
    ),
    TipoMensajeFamilia.CITAR_A_CONSULTA: PlantillaMensaje(
        tipo=TipoMensajeFamilia.CITAR_A_CONSULTA,
        asunto="Consulta de preparacion de transicion",
        plantilla=(
            "Estimada familia de {paciente}, le saludamos del INSN San Borja. "
            "Le recordamos su proxima consulta en el programa de preparacion de "
            "transicion a la atencion adulta. Es muy importante su asistencia "
            "para planificar su derivacion oportuna. Por favor confirmenos su "
            "recepcion."
        ),
        contiene_datos_clinicos=False,
    ),
    TipoMensajeFamilia.PASAPORTE_LISTO: PlantillaMensaje(
        tipo=TipoMensajeFamilia.PASAPORTE_LISTO,
        asunto="Pasaporte de Salud 18+ listo",
        plantilla=(
            "Estimada familia de {paciente}, le saludamos del INSN San Borja. "
            "Su Pasaporte de Salud 18+ se encuentra listo para entrega en su "
            "proxima consulta. Este documento facilitara su continuidad de "
            "atencion en el hospital de adultos. Los esperamos."
        ),
        contiene_datos_clinicos=False,
    ),
}


def plantilla_de(tipo: TipoMensajeFamilia) -> PlantillaMensaje:
    return PLANTILLAS[tipo]


# Una plantilla sin bandera declarada seria una que nadie reviso. Se comprueba
# al importar para que el fallo aparezca al arrancar y no cuando alguien
# recuerde correr la suite.
_faltantes = [t.name for t in TipoMensajeFamilia if t not in PLANTILLAS]
if _faltantes:  # pragma: no cover - red de seguridad de desarrollo
    raise RuntimeError(
        "Tipos de mensaje sin plantilla: " + ", ".join(_faltantes)
    )
