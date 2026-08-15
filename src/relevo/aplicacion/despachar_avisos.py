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

    def __init__(self, canal_equipo: CanalNotificacion) -> None:
        self._canal = canal_equipo

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
