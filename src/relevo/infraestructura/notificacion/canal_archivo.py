"""Canales de notificacion que no necesitan red.

POR QUE ESTE ADAPTADOR EXISTE
El puerto `CanalNotificacion` llevaba 107 lineas escritas y ningun adaptador
que lo implementara: el motor del cierre de ciclo estaba construido y
desconectado. Esto lo conecta.

POR QUE A ARCHIVO Y NO A SMTP
Porque el wifi del evento va a fallar, y porque un adaptador que escribe la
bandeja en disco demuestra el flujo completo sin credenciales de correo, sin
cuenta institucional y sin riesgo de mandarle un correo de verdad a nadie
durante una demo. Cambiarlo por SMTP es escribir otra clase que implemente el
mismo puerto — que es exactamente la promesa de la arquitectura.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from relevo.dominio.puertos.notificacion import (
    CanalNotificacion,
    Mensaje,
    ResultadoDespacho,
    TipoDestinatario,
)


@dataclass(frozen=True)
class CanalCorreoArchivo(CanalNotificacion):
    """Escribe el correo del equipo en disco, como si fuera una bandeja."""

    carpeta: Path = Path("salidas/avisos")

    @property
    def nombre(self) -> str:
        return "correo-archivo"

    @property
    def admite_datos_clinicos(self) -> bool:
        """True: es un canal cerrado hacia el equipo.

        Aun asi el mensaje declara si los lleva, y el registro lo deja escrito:
        que un canal PUEDA llevarlos no significa que deba hacerlo siempre.
        """
        return True

    @property
    def requiere_red(self) -> bool:
        return False

    def despachar(self, mensaje: Mensaje) -> ResultadoDespacho:
        if mensaje.tipo_destinatario is TipoDestinatario.FAMILIA:
            # Este canal es para el equipo. Un mensaje a la familia por aqui
            # seria un error de cableado, y se rechaza en el adaptador y no
            # solo en quien arma el mensaje: la regla tiene que sostenerse
            # aunque un caso de uso futuro se equivoque.
            return ResultadoDespacho(
                despachado=False,
                detalle=(
                    "Este canal solo sirve al equipo. Los avisos a la familia "
                    "van por el canal de WhatsApp, que no admite datos clinicos."
                ),
            )

        self.carpeta.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = self.carpeta / f"aviso_{marca}.txt"
        destino.write_text(
            f"Para: {mensaje.destinatario}\n"
            f"Asunto: {mensaje.asunto}\n"
            f"Etiquetas: {', '.join(mensaje.etiquetas)}\n"
            f"Contiene datos clinicos: {'si' if mensaje.contiene_datos_clinicos else 'no'}\n"
            f"{'-' * 60}\n"
            f"{mensaje.cuerpo}\n",
            encoding="utf-8",
        )
        return ResultadoDespacho(
            despachado=True, detalle=f"escrito en {destino}"
        )


@dataclass(frozen=True)
class CanalWhatsAppEnlace(CanalNotificacion):
    """Genera un enlace `wa.me` que una persona abre y despacha.

    NO envia nada, y eso es deliberado: `wa.me` abre conversaciones pero no
    recibe mensajes, y recibir exige la API de pago de Meta. Ademas mantiene a
    una persona en el circuito antes de que salga un mensaje a una familia.
    """

    carpeta: Path = Path("salidas/whatsapp")

    @property
    def nombre(self) -> str:
        return "whatsapp-enlace"

    @property
    def admite_datos_clinicos(self) -> bool:
        """Falso. Siempre.

        Un WhatsApp queda en la pantalla de bloqueo de un telefono que puede
        estar en manos de cualquiera, y se reenvia sin pensarlo.
        """
        return False

    @property
    def requiere_red(self) -> bool:
        """False: generar el enlace no necesita internet.

        Es lo que permite demostrar la capa de avisos con el wifi apagado.
        """
        return False

    def despachar(self, mensaje: Mensaje) -> ResultadoDespacho:
        if mensaje.contiene_datos_clinicos:
            # Se rechaza aunque el llamante insista. Es la regla de privacidad
            # verificada por test bloqueante.
            return ResultadoDespacho(
                despachado=False,
                detalle=(
                    "RECHAZADO: el mensaje declara datos clinicos y WhatsApp es "
                    "un canal abierto. El contenido clinico se lee en el papel "
                    "o en el sistema, no en un chat."
                ),
            )
        if mensaje.telefono is None:
            return ResultadoDespacho(
                despachado=False, detalle="No hay telefono de contacto vigente."
            )

        from urllib.parse import quote

        enlace = (
            f"https://wa.me/{mensaje.telefono.formato_internacional}"
            f"?text={quote(mensaje.cuerpo)}"
        )
        self.carpeta.mkdir(parents=True, exist_ok=True)
        registro = self.carpeta / "enlaces.jsonl"
        with registro.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "momento": datetime.now().isoformat(timespec="seconds"),
                        "destinatario": mensaje.destinatario,
                        "etiquetas": list(mensaje.etiquetas),
                        "enlace": enlace,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        return ResultadoDespacho(
            despachado=True,
            detalle="enlace generado; lo abre y envia una persona",
            enlace_generado=enlace,
        )
