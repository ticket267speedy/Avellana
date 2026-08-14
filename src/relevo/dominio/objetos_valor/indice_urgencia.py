"""Indice de Urgencia de Transicion (IUT) y su desglose.

PLAN_TECNICO §6.2:

    IUT = sigmoide(beta_0 + suma_i beta_i * x_i)

REQUISITO DE ACEPTACION (§5): `IndiceUrgencia` NO PUEDE CONSTRUIRSE SIN SUS
APORTES. Un indice sin explicacion es un dato invalido en este dominio.

La razon no es estetica. Un medico que ve "0.87" no puede hacer nada con eso.
Un medico que ve "0.87 — pesa sobre todo que le quedan 10 meses (2.38) y que
cambia de regimen de seguro (0.90)" sabe a quien llamar y para que. El desglose
es el producto; el numero es solo el orden.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from relevo.dominio.excepciones import IndiceSinExplicacion


class EstadoSemaforo(Enum):
    """Bandas de priorizacion.

    El umbral rojo NO deberia ser un numero fijo: se deriva de la capacidad
    mensual real del equipo (ver `calibrar_umbral_rojo`). Marcar en rojo mas
    pacientes de los que el equipo puede atender no prioriza nada.
    """

    ROJO = "rojo"
    AMBAR = "ambar"
    VERDE = "verde"

    @property
    def etiqueta(self) -> str:
        return {
            EstadoSemaforo.ROJO: "Prioridad alta",
            EstadoSemaforo.AMBAR: "Prioridad media",
            EstadoSemaforo.VERDE: "Seguimiento estándar",
        }[self]


def sigmoide(z: float) -> float:
    """sigma(z) = 1 / (1 + e^-z).

    Implementada por ramas para no desbordar en los extremos: `math.exp(800)`
    lanza OverflowError, y aunque el rango real de z aqui es [-4, +6], el
    dominio no debe romperse por una calibracion futura mas agresiva.
    """
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    expz = math.exp(z)
    return expz / (1.0 + expz)


@dataclass(frozen=True, slots=True)
class AporteFactor:
    """Lo que un factor aporta al log-odds del indice."""

    nombre: str
    x: float
    """Valor normalizado en [0, 1]."""

    beta: float
    dato_faltante: bool = False
    """True si `x` se imputo porque el dato no existia.

    Se propaga hasta la interfaz. Un factor imputado que empuja a un paciente a
    rojo tiene que ser visible: la decision se toma sobre un supuesto, no sobre
    un dato, y quien firma tiene derecho a saberlo.
    """

    explicacion: str = ""
    """Frase corta en castellano llano, para mostrar al usuario."""

    def __post_init__(self) -> None:
        if not 0.0 <= self.x <= 1.0:
            raise ValueError(
                f"El factor '{self.nombre}' vale {self.x}; los x_i van normalizados en [0,1]."
            )

    @property
    def aporte(self) -> float:
        """beta_i * x_i — lo que este factor suma al log-odds."""
        return self.beta * self.x


@dataclass(frozen=True, slots=True)
class IndiceUrgencia:
    """El IUT con su desglose completo. Inmutable e inseparable de su explicacion."""

    valor: float
    """IUT en [0, 1]."""

    z: float
    """El log-odds: beta_0 + suma de aportes. Se guarda para poder auditar."""

    beta_0: float
    aportes: tuple[AporteFactor, ...]
    """Ordenados de mayor a menor aporte. El orden es parte del contrato:
    quien lee el desglose lee primero lo que mas pesa."""

    estado: EstadoSemaforo
    umbral_rojo: float
    umbral_ambar: float

    confianza_minima: float = 0.70
    """Debajo de esto el indice se declara poco fiable.

    PROVISIONAL. TODO: confirmar con mentor — a partir de que fraccion de dato
    imputado un puntaje deja de ser accionable.
    """

    def __post_init__(self) -> None:
        if self.umbral_ambar > self.umbral_rojo:
            raise ValueError(
                f"Umbrales invertidos: ambar={self.umbral_ambar} > rojo={self.umbral_rojo}."
            )
        if not self.aportes:
            raise IndiceSinExplicacion(
                "Un IndiceUrgencia sin aportes no es un indice: es un numero suelto. "
                "PLAN_TECNICO §5 lo declara dato invalido."
            )
        if not 0.0 <= self.valor <= 1.0:
            raise ValueError(f"IUT fuera de rango: {self.valor}")

        orden_actual = [a.aporte for a in self.aportes]
        if orden_actual != sorted(orden_actual, reverse=True):
            raise IndiceSinExplicacion(
                "Los aportes deben venir ordenados de mayor a menor. "
                "El orden es la explicacion."
            )

    @property
    def hay_datos_faltantes(self) -> bool:
        return any(a.dato_faltante for a in self.aportes)

    @property
    def factores_imputados(self) -> tuple[str, ...]:
        return tuple(a.nombre for a in self.aportes if a.dato_faltante)

    @property
    def confianza(self) -> float:
        """Fraccion del peso total del modelo que se apoya en datos reales.

        1.0 = ningun factor imputado. 0.67 = un tercio del indice es supuesto.

        `hay_datos_faltantes` es un booleano y no distingue entre un supuesto
        que pesa 0.6 y tres que pesan 3.3 de 10. Esa diferencia es la que le
        importa a quien firma: no es lo mismo decidir sobre un dato con un
        hueco que decidir sobre un tercio de suposiciones.
        """
        total = sum(abs(a.beta) for a in self.aportes)
        if total == 0.0:
            return 0.0
        imputado = sum(abs(a.beta) for a in self.aportes if a.dato_faltante)
        return 1.0 - imputado / total

    @property
    def datos_insuficientes(self) -> bool:
        """True si demasiado peso del modelo esta imputado.

        No cambia la priorizacion: cambia lo que el sistema afirma saber. En
        la interfaz la insignia pasa de 'Prioridad alta' a 'Prioridad alta ·
        datos insuficientes'.
        """
        return self.confianza < self.confianza_minima

    @property
    def bandas_colapsadas(self) -> bool:
        """True si el umbral rojo calibrado quedo en el ambar o por debajo.

        Pasa cuando la capacidad del equipo alcanza para casi toda la cohorte:
        la banda intermedia desaparece. Es informacion util —el equipo va
        holgado— pero tiene que verse, no ocurrir en silencio.
        """
        return self.umbral_rojo <= self.umbral_ambar

    def principales(self, n: int = 3) -> tuple[AporteFactor, ...]:
        """Los n factores que mas empujan. Lo que se muestra en la tarjeta."""
        return self.aportes[:n]

    def explicacion_breve(self, n: int = 3) -> str:
        """Una linea legible por un humano apurado.

        Ejemplo: 'urgencia temporal (2.38), severidad (1.13), seguro (0.90)'
        """
        partes = [
            f"{a.explicacion or a.nombre} ({a.aporte:.2f})"
            for a in self.principales(n)
            if a.aporte > 0.0
        ]
        return ", ".join(partes) if partes else "sin factores de riesgo activos"

    def __str__(self) -> str:
        aviso = " · datos insuficientes" if self.datos_insuficientes else ""
        return (
            f"IUT {self.valor:.3f} [{self.estado.value}{aviso}] — "
            f"{self.explicacion_breve()}"
        )
