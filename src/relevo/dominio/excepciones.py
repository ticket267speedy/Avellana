"""Excepciones del dominio.

Todas heredan de `ErrorDominio`. Ninguna capa externa debe lanzar estas: son
la forma en que el nucleo dice "esto viola una regla de negocio".
"""

from __future__ import annotations


class ErrorDominio(Exception):
    """Raiz de todos los errores de reglas de negocio."""


class CodigoCIE10Invalido(ErrorDominio):
    """El codigo no tiene la forma de un CIE-10."""


class TelefonoInvalido(ErrorDominio):
    """El numero no tiene forma de telefono peruano utilizable."""


class IndiceSinExplicacion(ErrorDominio):
    """Se intento construir un IndiceUrgencia sin su desglose de aportes.

    PLAN_TECNICO §5: un indice sin explicacion es un dato invalido en este
    dominio. El desglose no es un adorno de la interfaz — es parte de lo que
    hace al indice utilizable por un medico que tiene que decidir a quien ve
    primero.
    """


class TransicionInvalida(ErrorDominio):
    """Se intento un salto de estado que la maquina del ciclo no permite."""


class PacienteFueraDeCohorte(ErrorDominio):
    """Se intento una operacion de cohorte activa sobre un paciente que ya
    cumplio 18 anios.

    El INSN no atiende a mayores de 18 bajo ninguna circunstancia. El corte es
    duro y en fecha exacta, no una guia.
    """


class DosisNoVerificable(ErrorDominio):
    """Una dosis extraida no aparece literalmente en el texto fuente.

    Regla inviolable del proyecto: nunca inventar una dosis. Si no se puede
    verificar contra el original, se descarta y se marca para completar a mano.
    """


class ConfiguracionIncompleta(ErrorDominio):
    """Falta un parametro de politica clinica que nadie debe inventar."""
