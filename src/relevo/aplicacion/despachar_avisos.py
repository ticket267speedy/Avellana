"""Caso de uso: convertir eventos en avisos y mandarlos por su canal.

Aqui vive la regla de privacidad, y vive en la capa de aplicacion a proposito:
es una decision de negocio sobre QUE se cuenta a quien, no un detalle del
transporte.

    equipo   -> correo institucional -> puede llevar contenido clinico
    familia  -> WhatsApp             -> NUNCA lleva contenido clinico

El motivo es concreto: un WhatsApp queda en la pantalla de bloqueo de un
telefono que puede estar en manos de cualquiera, y se reenvia sin pensarlo. El
mensaje dice "hay algo que atender y donde"; el que se lee en el papel.

Solo importa `dominio`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from relevo.dominio.eventos import EventoDominio, PlazoPorVencer, PlazoVencido
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.dominio.puertos.notificacion import (
    CanalNotificacion,
    Mensaje,
    ResultadoDespacho,
    TipoDestinatario,
)


@dataclass(frozen=True, slots=True)
class ResumenDespacho:
    despachados: int = 0
    rechazados: int = 0
    detalles: tuple[str, ...] = field(default_factory=tuple)

    @property
    def hubo_rechazos(self) -> bool:
        return self.rechazados > 0


class DespacharAvisos:
    """Arma los mensajes desde los eventos y los manda por el canal que toque.

    No se manda un mensaje por evento: se agrupa. Un coordinador con quince
    pacientes vencidos necesita UN correo con quince lineas, no quince correos
    — que es la forma mas rapida de que deje de leerlos.
    """

    def __init__(
        self,
        canal_equipo: CanalNotificacion,
        canal_familia: CanalNotificacion | None = None,
    ) -> None:
        self._canal = canal_equipo
        self._canal_familia = canal_familia

    # ── La unica ruta legitima a un enlace de WhatsApp ──────────────────────

    def preparar_para_familia(
        self,
        cuerpo: str,
        asunto: str,
        telefono: Telefono | None,
        referencia_paciente: str,
        contiene_datos_clinicos: bool = False,
    ) -> ResultadoDespacho:
        """Prepara un mensaje para la familia y devuelve el enlace.

        ═══════════════════════════════════════════════════════════════════════
        POR QUE ESTE METODO EXISTE
        ═══════════════════════════════════════════════════════════════════════

        La pantalla construia el enlace `wa.me` a mano, saltandose la guarda de
        privacidad del adaptador. No habia fuga —las plantillas estaban
        limpias— pero el test de privacidad iba a certificar un canal que nadie
        usaba, y el canal vivo iba a seguir sin proteccion.

        Ahora hay una sola ruta: la pantalla pide, la aplicacion arma el
        `Mensaje` con su bandera, y el adaptador decide. Si el mensaje declara
        datos clinicos, el adaptador lo rechaza y aqui vuelve
        `despachado=False` — la pantalla muestra el error y NO ofrece el boton.

        `contiene_datos_clinicos` se acepta como parametro a proposito, aunque
        hoy todas las plantillas sean False: es lo que permite comprobar en un
        test que la guarda funciona de verdad cuando alguien pone True.
        """
        if self._canal_familia is None:
            return ResultadoDespacho(
                despachado=False,
                detalle=(
                    "No hay canal de familia configurado. Se compone en "
                    "interfaz/arranque.py, que es el unico sitio donde se "
                    "nombran adaptadores."
                ),
            )

        mensaje = Mensaje(
            asunto=asunto,
            cuerpo=cuerpo,
            destinatario=referencia_paciente,
            tipo_destinatario=TipoDestinatario.FAMILIA,
            contiene_datos_clinicos=contiene_datos_clinicos,
            telefono=telefono,
            etiquetas=("familia", "whatsapp"),
        )
        return self._canal_familia.despachar(mensaje)

    def ejecutar(
        self, eventos: Sequence[EventoDominio], destinatario: str
    ) -> ResumenDespacho:
        """Si no hay eventos NO se manda nada.

        PLAN_TECNICO §10: un aviso que llega siempre deja de leerse. No mandar
        correo cuando no pasa nada es parte del diseno, no un olvido.
        """
        if not eventos:
            return ResumenDespacho(detalles=("sin novedades: no se envia correo",))

        vencidos = [e for e in eventos if isinstance(e, PlazoVencido)]
        por_vencer = [e for e in eventos if isinstance(e, PlazoPorVencer)]

        lineas: list[str] = []
        if vencidos:
            lineas.append(f"VENCIDOS ({len(vencidos)}):")
            lineas.extend(f"  · {e.descripcion}" for e in vencidos)
        if por_vencer:
            if lineas:
                lineas.append("")
            lineas.append(f"POR VENCER ({len(por_vencer)}):")
            lineas.extend(f"  · {e.descripcion}" for e in por_vencer)

        mensaje = Mensaje(
            asunto=f"Relevo · {len(vencidos)} vencidos y {len(por_vencer)} por vencer",
            cuerpo="\n".join(lineas),
            destinatario=destinatario,
            tipo_destinatario=TipoDestinatario.EQUIPO,
            # Identificadores internos y etapas del ciclo. NI diagnosticos, ni
            # CIE-10, ni medicamentos: `EventoDominio.descripcion` esta escrito
            # para poder viajar por un canal que no controlamos.
            contiene_datos_clinicos=False,
            etiquetas=("semanal", "vencimiento"),
        )

        resultado: ResultadoDespacho = self._canal.despachar(mensaje)
        if resultado.despachado:
            return ResumenDespacho(despachados=1, detalles=(resultado.detalle,))
        return ResumenDespacho(rechazados=1, detalles=(resultado.detalle,))
