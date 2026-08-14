"""La ventana de transicion: el tiempo que queda antes de que se acabe.

PLAN_TECNICO §1 — el hecho que define el sistema entero:

    El INSN no atiende a mayores de 18 anios bajo ninguna circunstancia.

No es una demora de atencion. Es una interrupcion total, en fecha exacta. Por
eso la ventana se cuenta HACIA ATRAS desde el cumpleanos 18, y por eso puede
cerrarse: cuando se cierra, no se reabre.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

# Edad a la que arranca la cohorte activa. Cuatro anios antes del corte:
# el mismo horizonte de 48 meses con que se normaliza x1 (PLAN_TECNICO §6.2).
EDAD_INICIO_COHORTE = 14

# El corte. No es un umbral configurable: es la regla institucional.
EDAD_CORTE = 18


class Cohorte(Enum):
    """Las dos poblaciones del sistema. No hay una tercera."""

    PREVIA = "previa"
    """Menor de 14. Todavia no entra: avisarle a los 12 no sirve de nada."""

    ACTIVA = "activa"
    """14 <= edad < 18. Se prioriza, se prepara, se emite Pasaporte."""

    SEGUIMIENTO = "seguimiento"
    """>= 18. Ya no es paciente del INSN, pero el ciclo sigue abierto hasta
    confirmar que llego al servicio de adultos.

    Esta es la cohorte que justifica el proyecto. Hoy no existe: al cumplir 18
    el paciente simplemente deja de aparecer, y nadie sabe si llego a algun
    lado. Es aqui donde el sistema aporta lo que no hay."""


def cumpleanos_18(fecha_nacimiento: date) -> date:
    """La fecha exacta del corte.

    Caso 29 de febrero: quien nacio en bisiesto cumple el 1 de marzo en los
    anios no bisiestos. Se resuelve asi y no al reves porque el corte es una
    restriccion de acceso: adelantarlo un dia le quita un dia de atencion a la
    que el paciente tiene derecho.
    """
    anio_corte = fecha_nacimiento.year + EDAD_CORTE
    try:
        return fecha_nacimiento.replace(year=anio_corte)
    except ValueError:
        # 29 de febrero en anio no bisiesto.
        return date(anio_corte, 3, 1)


def edad_en(fecha_nacimiento: date, hoy: date) -> int:
    """Edad en anios cumplidos."""
    anios = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        anios -= 1
    return anios


@dataclass(frozen=True, slots=True)
class VentanaTransicion:
    """Cuanto tiempo queda, y si todavia se puede hacer algo."""

    fecha_nacimiento: date
    hoy: date

    @property
    def fecha_corte(self) -> date:
        return cumpleanos_18(self.fecha_nacimiento)

    @property
    def edad(self) -> int:
        return edad_en(self.fecha_nacimiento, self.hoy)

    @property
    def dias_restantes(self) -> int:
        """Dias hasta el corte. Negativo si ya paso."""
        return (self.fecha_corte - self.hoy).days

    @property
    def meses_restantes(self) -> int:
        """Meses calendario completos hasta el corte. Negativo si ya paso.

        Meses calendario y no dias/30: el equipo razona en meses y las citas se
        programan en meses. Un redondeo de 30.44 dias confunde mas de lo que
        precisa.
        """
        meses = (self.fecha_corte.year - self.hoy.year) * 12 + (
            self.fecha_corte.month - self.hoy.month
        )
        if self.fecha_corte.day < self.hoy.day:
            meses -= 1
        return meses

    @property
    def cohorte(self) -> Cohorte:
        edad = self.edad
        if edad < EDAD_INICIO_COHORTE:
            return Cohorte.PREVIA
        if edad < EDAD_CORTE:
            return Cohorte.ACTIVA
        return Cohorte.SEGUIMIENTO

    @property
    def esta_cerrada(self) -> bool:
        """True si el paciente ya cumplio 18. No se reabre."""
        return self.dias_restantes <= 0

    @property
    def hitos_pendientes(self) -> tuple[int, ...]:
        """Edades de hito (14, 16, 17) que aun no se alcanzaron.

        Sirve para saber que version del Pasaporte toca emitir despues.
        """
        return tuple(edad for edad in (14, 16, 17) if edad > self.edad)

    @property
    def hito_actual(self) -> int | None:
        """El hito de Pasaporte que corresponde a la edad de hoy.

        14 y 15 -> v1 (hito 14) · 16 -> v2 (hito 16) · 17 -> v3 (hito 17).
        None fuera de la cohorte activa.
        """
        edad = self.edad
        if edad < 14 or edad >= EDAD_CORTE:
            return None
        if edad < 16:
            return 14
        if edad < 17:
            return 16
        return 17

    def __str__(self) -> str:
        if self.esta_cerrada:
            return f"ventana cerrada hace {-self.dias_restantes} dias (edad {self.edad})"
        return f"{self.meses_restantes} meses hasta el corte (edad {self.edad})"
