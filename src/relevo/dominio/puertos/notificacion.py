"""Puerto de avisos: correo al equipo, WhatsApp a la familia.

PLAN_TECNICO §10. Principio rector: el sistema busca a la persona; la persona
no busca al sistema. Ninguna pantalla es de revision obligatoria diaria.

REGLA DE PRIVACIDAD, VERIFICADA POR TEST BLOQUEANTE
(`tests/infraestructura/test_privacidad_whatsapp.py`): ningun mensaje de
WhatsApp puede contener diagnosticos, codigos CIE-10, nombres de medicamentos,
dosis ni resultados.

El motivo es concreto: un mensaje de WhatsApp queda en la pantalla de bloqueo
de un telefono que puede estar en manos de cualquiera, y se reenvia sin
pensarlo. El canal no es confidencial, asi que el contenido tampoco puede
serlo. Lo que el mensaje dice es "hay algo que atender y donde"; el que
contiene se lee en el papel o en el sistema.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from relevo.dominio.objetos_valor.telefono import Telefono


class TipoDestinatario(Enum):
    EQUIPO = "equipo"
    """Personal del INSN. Puede recibir contenido clinico."""

    FAMILIA = "familia"
    """Paciente o cuidador. NUNCA recibe contenido clinico por WhatsApp."""


@dataclass(frozen=True, slots=True)
class Mensaje:
    """Un aviso listo para despachar.

    `contiene_datos_clinicos` lo declara quien arma el mensaje y lo verifica el
    test bloqueante. Un mensaje con datos clinicos dirigido a FAMILIA por un
    canal abierto es un fallo de privacidad, no una decision editorial.
    """

    asunto: str
    cuerpo: str
    destinatario: str
    tipo_destinatario: TipoDestinatario
    contiene_datos_clinicos: bool = False
    telefono: Telefono | None = None
    """Solo para el canal de WhatsApp."""

    etiquetas: tuple[str, ...] = field(default_factory=tuple)
    """Para agrupar en el registro: 'semanal', 'vencimiento', 'hito_14'."""

    @property
    def es_seguro_por_canal_abierto(self) -> bool:
        return not self.contiene_datos_clinicos


@dataclass(frozen=True, slots=True)
class ResultadoDespacho:
    """Que paso al intentar despachar.

    `enlace_generado` es la forma que toma el resultado en WhatsApp: el
    adaptador NO envia nada — genera un enlace `wa.me` que un humano abre y
    despacha desde su propio telefono. `wa.me` abre conversaciones pero no
    recibe mensajes; recibir exige la API de pago de Meta (PLAN_TECNICO §13).
    """

    despachado: bool
    detalle: str = ""
    enlace_generado: str = ""


class CanalNotificacion(ABC):
    """Un medio por el que sale un aviso: SMTP, enlace wa.me, archivo."""

    @abstractmethod
    def despachar(self, mensaje: Mensaje) -> ResultadoDespacho:
        """Envia o prepara el mensaje.

        Toda implementacion que sirva a destinatarios de tipo FAMILIA debe
        rechazar los mensajes con `contiene_datos_clinicos=True`, aunque el
        llamante insista. La comprobacion vive en el adaptador y no solo en
        quien arma el mensaje, porque la regla tiene que sostenerse aunque un
        caso de uso futuro se equivoque.
        """

    @property
    @abstractmethod
    def nombre(self) -> str:
        ...

    @property
    @abstractmethod
    def admite_datos_clinicos(self) -> bool:
        """True solo en canales cerrados hacia el equipo (correo institucional).

        Falso en WhatsApp, siempre.
        """

    @property
    @abstractmethod
    def requiere_red(self) -> bool:
        """El canal de WhatsApp devuelve False: generar un enlace `wa.me` no
        necesita internet. Es lo que permite demostrar la capa de avisos con el
        wifi apagado."""
