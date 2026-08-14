"""Telefono peruano como objeto de valor.

Por que esto existe con tanto detalle: la plantilla oficial de historia
clinica del INSN (RD N° 000109-2021-DG-INSN-SB) NO TIENE campo de telefono ni
de correo en ninguna de sus seis paginas. Verificado.

Consecuencia: el unico telefono que el hospital tiene de un paciente es el que
alguien anoto en algun lado cuando el paciente tenia tres anios. Para un
paciente de 17 ese numero probablemente ya no funciona. Por eso el telefono
lleva `verificado_en`: un numero sin fecha de verificacion no es un canal de
contacto, es una esperanza.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from relevo.dominio.excepciones import TelefonoInvalido

# Un movil peruano tiene 9 digitos y empieza en 9. Los fijos de Lima tienen 7
# digitos (y 8 con el codigo de area 1). Solo los moviles sirven para WhatsApp,
# que es el canal que usamos.
_SOLO_DIGITOS = re.compile(r"\D")
_MOVIL_PERU = re.compile(r"^9[0-9]{8}$")

CODIGO_PAIS_PERU = "51"

# Un contacto verificado hace mas de esto se considera dudoso y se vuelve a
# pedir en el siguiente hito. Un anio: si no se hablo con la familia en un anio,
# el numero puede haber cambiado.
# TODO: confirmar con mentor — cada cuanto exige el INSN reverificar contacto.
DIAS_VIGENCIA_VERIFICACION = 365


@dataclass(frozen=True, slots=True)
class Telefono:
    """Numero movil peruano normalizado, con su trazabilidad de verificacion."""

    numero: str
    verificado_en: date | None = None
    es_del_paciente: bool = False
    """True si el numero es del propio paciente, no del cuidador.

    A partir de los 16 (Pasaporte v2) capturar el telefono PROPIO del paciente
    es funcionalidad central: a los 18 el vinculo con el cuidador puede
    haberse roto, y el paciente es quien tiene que poder ser contactado.
    """

    def __post_init__(self) -> None:
        digitos = _SOLO_DIGITOS.sub("", self.numero)

        # Tolerar las formas en que la gente escribe su numero:
        #   +51 987 654 321 / 51987654321 / 987654321 / 0051987654321
        if digitos.startswith("00" + CODIGO_PAIS_PERU):
            digitos = digitos[len("00" + CODIGO_PAIS_PERU):]
        elif digitos.startswith(CODIGO_PAIS_PERU) and len(digitos) == 11:
            digitos = digitos[len(CODIGO_PAIS_PERU):]

        if not _MOVIL_PERU.match(digitos):
            raise TelefonoInvalido(
                f"'{self.numero}' no es un movil peruano valido "
                "(9 digitos empezando en 9). Solo los moviles sirven para WhatsApp."
            )
        object.__setattr__(self, "numero", digitos)

    @property
    def formato_internacional(self) -> str:
        """'51987654321' — la forma que exige wa.me, sin '+' ni espacios."""
        return f"{CODIGO_PAIS_PERU}{self.numero}"

    @property
    def formato_legible(self) -> str:
        """'+51 987 654 321' — para mostrar en pantalla y en el Pasaporte."""
        n = self.numero
        return f"+{CODIGO_PAIS_PERU} {n[0:3]} {n[3:6]} {n[6:9]}"

    def esta_vigente(self, hoy: date) -> bool:
        """False si nunca se verifico o si la verificacion ya caduco.

        Un telefono no vigente no se usa para decidir nada: se marca para
        recapturar en el proximo hito.
        """
        if self.verificado_en is None:
            return False
        return (hoy - self.verificado_en).days <= DIAS_VIGENCIA_VERIFICACION

    def enmascarado(self) -> str:
        """'+51 9** *** *21' — para registros y pantallas de auditoria.

        Nunca se escribe un numero completo en un log.
        """
        n = self.numero
        return f"+{CODIGO_PAIS_PERU} {n[0]}** *** *{n[7:9]}"

    def __str__(self) -> str:
        return self.formato_legible
