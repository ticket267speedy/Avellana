"""Validacion en vivo de los campos que una persona teclea o corrige.

POR QUE ESTO ES DISTINTO DE `extraccion_por_reglas`
Aquel modulo juzga lo que LEYO EL MODELO y en la duda devuelve `None`. Este
juzga lo que ESCRIBE UNA PERSONA, mientras lo escribe, y su trabajo no es
rechazar sino AVISAR: "llevas 6 de 8 digitos". Rechazar en silencio a quien
esta tecleando es la forma mas rapida de que deje de usar el sistema.

De ahi que devuelva tres estados y no dos: valido, incompleto y erroneo.
`INCOMPLETO` es el estado normal de un campo a medio escribir, y pintarlo en
rojo seria mentir sobre lo que esta pasando.

LAS REGLAS NO SE INVENTAN AQUI
El movil se valida construyendo `Telefono`, el objeto de valor del dominio, que
ya sabe tolerar +51, espacios y guiones. La edad se calcula con
`VentanaTransicion`, que ya sabe del corte a los 18 y del 29 de febrero.
Duplicar esas reglas aqui es garantizar que se separen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum

from relevo.dominio.excepciones import TelefonoInvalido
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.dominio.objetos_valor.ventana_transicion import (
    EDAD_CORTE,
    VentanaTransicion,
)


class Estado(Enum):
    VACIO = "vacio"
    INCOMPLETO = "incompleto"
    """A medio escribir. No es un error: es un campo en curso."""

    VALIDO = "valido"
    ERRONEO = "erroneo"

    @property
    def icono(self) -> str:
        return {
            Estado.VACIO: "",
            Estado.INCOMPLETO: "⏳",
            Estado.VALIDO: "✅",
            Estado.ERRONEO: "❌",
        }[self]


@dataclass(frozen=True, slots=True)
class Veredicto:
    estado: Estado
    mensaje: str = ""

    @property
    def bloquea_emision(self) -> bool:
        """Solo lo erroneo impide emitir. Un campo vacio se puede dejar vacio:
        el documento original puede no traer ese dato, y obligar a inventarlo
        seria peor que no tenerlo."""
        return self.estado is Estado.ERRONEO


# DNI peruano: 8 digitos. No lleva digito verificador propio (el que se usa en
# el RUC no aplica aqui), asi que la unica comprobacion posible es la longitud.
# TODO: confirmar con mentor — si el INSN registra tambien carnet de extranjeria
# o codigo de recien nacido para pacientes sin DNI.
LONGITUD_DNI = 8


def validar_dni(texto: str) -> Veredicto:
    limpio = re.sub(r"\D", "", texto or "")
    if not limpio:
        return Veredicto(Estado.VACIO)
    if len(limpio) > LONGITUD_DNI:
        return Veredicto(
            Estado.ERRONEO, f"{len(limpio)} dígitos: el DNI tiene {LONGITUD_DNI}"
        )
    if len(limpio) < LONGITUD_DNI:
        faltan = LONGITUD_DNI - len(limpio)
        return Veredicto(
            Estado.INCOMPLETO,
            f"{len(limpio)} de {LONGITUD_DNI} dígitos · faltan {faltan}",
        )
    return Veredicto(Estado.VALIDO, "8 dígitos")


def validar_celular(texto: str) -> Veredicto:
    """Delega en `Telefono`, que ya sabe la regla peruana y tolera formatos."""
    limpio = (texto or "").strip()
    if not limpio:
        return Veredicto(Estado.VACIO)

    solo_digitos = re.sub(r"\D", "", limpio)
    # Aviso temprano y util: en el Peru todo movil empieza en 9.
    if solo_digitos and not solo_digitos.startswith(("9", "5", "0")):
        return Veredicto(Estado.ERRONEO, "un móvil peruano empieza en 9")
    if len(solo_digitos) < 9:
        return Veredicto(
            Estado.INCOMPLETO, f"{len(solo_digitos)} de 9 dígitos"
        )
    try:
        Telefono(numero=limpio)
    except TelefonoInvalido as exc:
        return Veredicto(Estado.ERRONEO, str(exc)[:90])
    return Veredicto(Estado.VALIDO, "móvil peruano válido")


# TODO: confirmar con mentor — longitud y formato del numero de historia
# clinica del INSN. Se observaron 5 digitos en las muestras, pero no hay fuente
# que lo confirme, asi que NO se rechaza por longitud: solo se avisa.
LONGITUD_HC_OBSERVADA = 5


def validar_numero_hc(texto: str) -> Veredicto:
    limpio = (texto or "").strip()
    if not limpio:
        return Veredicto(Estado.VACIO)
    if not re.fullmatch(r"[0-9]{1,10}", limpio):
        return Veredicto(Estado.ERRONEO, "solo dígitos, sin puntos ni guiones")
    if len(limpio) != LONGITUD_HC_OBSERVADA:
        # Aviso, no error: no tenemos la regla oficial y rechazar seria inventarla.
        return Veredicto(
            Estado.VALIDO,
            f"{len(limpio)} dígitos · lo habitual son {LONGITUD_HC_OBSERVADA}, confirma con el original",
        )
    return Veredicto(Estado.VALIDO, f"{len(limpio)} dígitos")


def validar_fecha_nacimiento(nacimiento: date | None, hoy: date) -> Veredicto:
    """La regla que importa: el INSN no atiende a mayores de 18.

    Se calcula con `VentanaTransicion`, que es quien sabe del corte y del caso
    del 29 de febrero. Un paciente de 18 o mas NO invalida el documento —
    existe la cohorte de seguimiento— pero es una senial que quien revisa tiene
    que ver, porque casi siempre significa que la fecha se tecleo mal.
    """
    if nacimiento is None:
        return Veredicto(Estado.VACIO)
    if nacimiento > hoy:
        return Veredicto(Estado.ERRONEO, "la fecha es futura")

    ventana = VentanaTransicion(fecha_nacimiento=nacimiento, hoy=hoy)
    edad = ventana.edad
    if edad > 120:
        return Veredicto(Estado.ERRONEO, f"{edad} años: revisa el año")
    if edad >= EDAD_CORTE:
        return Veredicto(
            Estado.VALIDO,
            f"{edad} años — fuera del corte de {EDAD_CORTE}: entra como seguimiento, verifica la fecha",
        )
    return Veredicto(
        Estado.VALIDO,
        f"{edad} años · {ventana.meses_restantes} meses hasta el corte",
    )


ETIQUETA_OTRO = "Otro (no figura en el catálogo)"
"""Opcion de escape del catalogo de establecimientos.

Bloquear lo que no esta en el catalogo no limpia la base: hace que la persona
escriba el dato en cualquier otro sitio, o que abandone. Se permite, se pide el
nombre en texto libre, y el registro queda MARCADO como pendiente de conciliar
contra RENAES. Una cola de conciliacion es manejable; un campo abandonado no.
"""


def requiere_conciliacion(establecimiento: str, catalogo: tuple[str, ...]) -> bool:
    return bool(establecimiento) and establecimiento not in catalogo
