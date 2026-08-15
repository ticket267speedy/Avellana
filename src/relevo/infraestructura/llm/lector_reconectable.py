"""Lector que vuelve a buscar el modelo cada cierto tiempo.

EL PROBLEMA QUE RESUELVE
`elegir_lectores()` sondea Ollama UNA vez y devuelve el lector que encontro.
Eso basta para un proceso de linea de comandos, pero no para una pantalla que
queda abierta: `construir()` corre una sola vez al arrancar el servidor, asi que
el resultado de ese unico sondeo quedaba congelado para siempre.

Consecuencias reales, las dos observadas:

- La aplicacion desplegada arranca cuando el portatil del equipo esta apagado.
  Encender Ollama despues no servia de nada: la pantalla seguia diciendo que no
  habia modelo hasta reiniciar el servidor entero.
- Al reves, si el portatil se suspende a mitad de una demo, la pantalla seguia
  anunciando un modelo activo que ya no contestaba, y el fallo solo aparecia
  cuando alguien pulsaba leer y esperaba dos minutos para nada.

Este adaptador cierra las dos: implementa el mismo puerto `LectorDocumento`,
pero resuelve el lector concreto en cada uso, cacheando el resultado unos pocos
segundos para no sondear en cada pulsacion de tecla.

Nada por encima se entera. `DigitalizarDocumento` recibe esto y sigue creyendo
que tiene un lector normal.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from relevo.dominio.puertos.lectura_documento import LectorDocumento
from relevo.infraestructura.llm.lector_ollama import (
    OllamaNoDisponible,
    elegir_lectores,
)

# Cuanto se reutiliza un sondeo antes de repetirlo.
#
# 8 segundos es un compromiso medido contra dos costes opuestos: por debajo, la
# pantalla castiga a Ollama con peticiones constantes; por encima, tarda
# demasiado en notar que el portatil volvio. El semaforo de la interfaz se
# refresca cada 10 s, asi que a efectos practicos cada refresco trae un sondeo
# nuevo.
TTL_SONDEO_SEGUNDOS = 8.0

# Espera maxima del sondeo periodico. Corta a proposito: este sondeo corre
# dentro del ciclo de repintado de la pantalla, y bloquearlo 15 segundos
# congelaria la interfaz entera cada vez que el host no responde.
TIMEOUT_SONDEO_SEGUNDOS = 4.0


@dataclass(frozen=True, slots=True)
class EstadoLector:
    """Lo que la pantalla necesita saber del modelo, ahora mismo."""

    activo: bool
    modelo: str
    host: str

    @property
    def es_remoto(self) -> bool:
        return "localhost" not in self.host and "127.0.0.1" not in self.host


class LectorReconectable(LectorDocumento):
    """Un `LectorDocumento` que redescubre a Ollama por su cuenta."""

    def __init__(
        self,
        host: str,
        ttl_segundos: float = TTL_SONDEO_SEGUNDOS,
        timeout_sondeo: float = TIMEOUT_SONDEO_SEGUNDOS,
    ) -> None:
        self._host = host
        self._ttl = ttl_segundos
        self._timeout = timeout_sondeo
        self._resuelto: LectorDocumento | None = None
        self._visto_en: float = 0.0

    @property
    def host(self) -> str:
        return self._host

    def _resolver(self, forzar: bool = False) -> LectorDocumento | None:
        """El lector concreto, o None si Ollama no contesta.

        `forzar` salta la cache. Se usa antes de una lectura de verdad: ahi la
        peticion va a tardar minutos de todas formas, y arrancarla contra un
        lector que ya no existe seria el peor momento para descubrirlo.
        """
        ahora = time.monotonic()
        if not forzar and (ahora - self._visto_en) < self._ttl:
            return self._resuelto

        principal, _contraste = elegir_lectores(
            host=self._host, timeout=self._timeout
        )
        nombre = str(getattr(principal, "nombre", "sin-modelo"))
        # `LectorNulo` se descarta aqui: para esta clase "no hay modelo" es
        # None, y asi el resto no tiene que distinguir dos formas de nada.
        self._resuelto = None if nombre == "sin-modelo" else principal  # type: ignore[assignment]
        self._visto_en = ahora
        return self._resuelto

    def estado(self, forzar: bool = False) -> EstadoLector:
        """Para el semaforo de la interfaz."""
        lector = self._resolver(forzar=forzar)
        return EstadoLector(
            activo=lector is not None,
            modelo=str(getattr(lector, "nombre", "sin-modelo")),
            host=self._host,
        )

    def leer(self, imagen: bytes, instruccion: str) -> str:
        lector = self._resolver(forzar=True)
        if lector is None:
            raise OllamaNoDisponible(
                f"No hay ningun modelo alcanzable en {self._host}. "
                "Si es un equipo del propio equipo de trabajo, comprueba que "
                "este encendido, que `ollama serve` siga corriendo y que el "
                "tunel no se haya caido."
            )
        return lector.leer(imagen, instruccion)

    @property
    def nombre(self) -> str:
        lector = self._resolver()
        return str(getattr(lector, "nombre", "sin-modelo"))

    @property
    def requiere_red(self) -> bool:
        """True solo cuando el modelo esta en otra maquina.

        Contra el Ollama local sigue siendo False, que es lo que sostiene la
        promesa de funcionar con el wifi apagado. Apuntar a un host remoto es
        una decision explicita del despliegue, y entonces si hay red de por
        medio y este puerto debe admitirlo.
        """
        return "localhost" not in self._host and "127.0.0.1" not in self._host
