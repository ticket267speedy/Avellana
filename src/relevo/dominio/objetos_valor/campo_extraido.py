"""Un campo leido de un documento, con todo lo que hace falta para no confiar en el a ciegas.

PLAN_TECNICO — modulo de digitalizacion.

La promesa del sistema NO es "leemos sin error". Eso no existe con escritura
manuscrita, ni con el mejor modelo. La promesa es:

    NINGUN ERROR PASA SIN SER DETECTADO.

Para poder afirmar eso, un valor leido nunca viaja solo: viaja con su estado,
con los motivos que lo llevaron a ese estado, y con el rastro de si fue ajustado
contra un catalogo. Un `str` suelto no sirve — no se puede auditar.

Este modulo no importa nada externo. Solo libreria estandar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EstadoCampo(Enum):
    """Que se puede hacer con este valor."""

    VERDE = "verde"
    """Leido y validado. Se puede usar sin intervencion."""

    AMBAR = "ambar"
    """Requiere revision humana antes de usarse. El sistema NO lo descarta ni
    lo acepta: lo pone delante de una persona."""

    ROJO = "rojo"
    """No utilizable. Ilegible, ausente o incompatible con lo que el campo
    admite. Tampoco se adivina."""

    @property
    def etiqueta(self) -> str:
        return {
            EstadoCampo.VERDE: "Validado",
            EstadoCampo.AMBAR: "Revisar",
            EstadoCampo.ROJO: "No legible",
        }[self]

    @property
    def requiere_persona(self) -> bool:
        return self is not EstadoCampo.VERDE


class Motivo(Enum):
    """Por que un campo quedo en el estado en que quedo.

    Los motivos se muestran en la pantalla de verificacion. Decirle a alguien
    "revisa este campo" sin decirle por que lo obliga a revisar todo de nuevo.
    """

    VACIO = "el campo vino vacio"
    NO_LEGIBLE = "el modelo no pudo leerlo"
    FORMATO_INVALIDO = "no cumple el formato esperado del campo"
    FUERA_DE_CATALOGO = "el valor no existe en el catalogo oficial"
    AJUSTADO_A_CATALOGO = "se corrigio al valor mas cercano del catalogo"
    CATALOGO_AMBIGUO = "hay mas de un valor de catalogo igual de cercano"
    CONFIANZA_BAJA = "el modelo reporto poca certeza"
    DESACUERDO_ENTRE_MODELOS = "dos lecturas independientes no coinciden"
    INCONSISTENTE_CON_OTRO_CAMPO = "contradice a otro campo del documento"
    VALIDADO = "leido y validado sin observaciones"


@dataclass(frozen=True, slots=True)
class AjusteCatalogo:
    """Rastro de una correccion contra vocabulario cerrado.

    Es la pieza que convierte "el modelo leyo mal" en "el sistema lo corrigio y
    dejo constancia". Sin este rastro, una correccion automatica es
    indistinguible de una alucinacion.
    """

    valor_leido: str
    valor_catalogo: str
    distancia: float
    segundo_candidato: str | None = None
    distancia_segundo: float | None = None

    @property
    def ambiguo(self) -> bool:
        """Dos candidatos igual de cerca = el catalogo no desempata.

        Cuando pasa, la correccion automatica seria una moneda al aire. Va a
        revision humana.
        """
        if self.distancia_segundo is None:
            return False
        # Margen: si el segundo candidato esta a menos de 0.5 de diferencia, el
        # catalogo no desempata con confianza y decide una persona.
        return (self.distancia_segundo - self.distancia) < 0.5


@dataclass(frozen=True, slots=True)
class CampoExtraido:
    """Un campo leido de un documento, con su estado y su justificacion."""

    nombre: str
    valor_crudo: str | None
    """Lo que el modelo devolvio, literal, sin tocar. Se conserva SIEMPRE:
    es la unica forma de auditar una correccion despues."""

    valor: str | None
    """El valor utilizable tras normalizar y ajustar. None si no hay ninguno."""

    estado: EstadoCampo
    motivos: tuple[Motivo, ...] = field(default_factory=tuple)
    confianza_modelo: float | None = None
    ajuste: AjusteCatalogo | None = None
    obligatorio: bool = True

    def __post_init__(self) -> None:
        if not self.motivos:
            raise ValueError(
                f"El campo '{self.nombre}' no declara motivo. Un estado sin "
                "motivo no es auditable: quien revisa no sabe que mirar."
            )
        if self.estado is EstadoCampo.VERDE and self.valor is None:
            raise ValueError(
                f"El campo '{self.nombre}' esta en verde sin valor. "
                "Verde significa utilizable."
            )
        if self.confianza_modelo is not None and not 0.0 <= self.confianza_modelo <= 1.0:
            raise ValueError(
                f"Confianza fuera de rango en '{self.nombre}': {self.confianza_modelo}"
            )

    @property
    def fue_corregido(self) -> bool:
        return self.ajuste is not None and self.ajuste.valor_leido != self.valor

    def explicacion(self) -> str:
        """Una linea para la pantalla de verificacion."""
        base = ", ".join(m.value for m in self.motivos)
        if self.fue_corregido and self.ajuste is not None:
            return f"{base} (se leyo '{self.ajuste.valor_leido}')"
        return base
