"""Codigo CIE-10 como objeto de valor inmutable."""

from __future__ import annotations

import re
from dataclasses import dataclass

from relevo.dominio.excepciones import CodigoCIE10Invalido

# Forma de un codigo CIE-10: una letra, dos digitos, y opcionalmente punto mas
# uno o dos caracteres de subdivision.
#   G80    G80.9    E10.2    Z94.0    D66
# La I y la O no se usan como primera letra en CIE-10 salvo el capitulo I
# (circulatorio), que si existe: I10, I27. Se aceptan ambas y no se filtra por
# capitulo, porque el listado autoritativo vive en los CSV de config/, no aqui.
_PATRON = re.compile(r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,2})?$")


@dataclass(frozen=True, slots=True)
class CodigoCIE10:
    """Codigo CIE-10 validado en construccion.

    Inmutable. Dos codigos con el mismo valor son el mismo objeto para efectos
    de comparacion y de conjunto.
    """

    valor: str

    def __post_init__(self) -> None:
        normalizado = self.valor.strip().upper()
        if not _PATRON.match(normalizado):
            raise CodigoCIE10Invalido(
                f"'{self.valor}' no tiene forma de codigo CIE-10 (ej: G80.9, E10, Z94.0)"
            )
        # frozen=True impide la asignacion normal; object.__setattr__ es la via
        # documentada para normalizar en __post_init__.
        object.__setattr__(self, "valor", normalizado)

    @property
    def capitulo(self) -> str:
        """La letra del capitulo. 'G80.9' -> 'G'."""
        return self.valor[0]

    @property
    def categoria(self) -> str:
        """Los tres primeros caracteres, sin subdivision. 'G80.9' -> 'G80'.

        Es el nivel al que se hacen las correspondencias del directorio de
        destinos: no se deriva a un servicio distinto por la subdivision.
        """
        return self.valor[:3]

    def coincide_con_prefijo(self, prefijo: str) -> bool:
        """True si este codigo cae bajo el prefijo dado.

        'G80.9'.coincide_con_prefijo('G80') -> True
        'G80.9'.coincide_con_prefijo('G8')  -> True
        'G40.9'.coincide_con_prefijo('G80') -> False
        """
        return self.valor.startswith(prefijo.strip().upper())

    def __str__(self) -> str:
        return self.valor
