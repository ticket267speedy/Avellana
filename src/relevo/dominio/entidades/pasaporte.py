"""El Pasaporte de Salud 18+.

PLAN_TECNICO §9. Documento informativo que el paciente se lleva, escalonado en
tres versiones segun la edad: a los 14 media pagina, a los 16 una, a los 17 dos.

Esta entidad es el CONTENIDO del pasaporte, no su forma impresa. Quien lo
convierte en PDF es un adaptador (`GeneradorDocumento`); el dominio solo dice
que va adentro, en que version y si esta firmado.

Regla que atraviesa todo el archivo: **el medico siempre firma**. Un pasaporte
sin firma es un borrador, y un borrador no se entrega.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from relevo.dominio.excepciones import ErrorDominio

# Texto exigido al pie de las tres versiones. PLAN_TECNICO §9: va textual, no
# parafraseado. Es lo que separa un documento informativo de complemento de
# algo que pretenda sustituir el resumen de historia clinica normado.
AVISO_NORMATIVO = (
    "Documento informativo complementario para la transicion asistencial. "
    "No reemplaza la historia clinica ni el resumen de historia clinica "
    "normado (RM 214-2018-MINSA). Elaborado con apoyo automatizado, revisado "
    "y firmado por el medico tratante."
)

# Mientras dure el hackathon, todo documento sale marcado. No negociable:
# un PDF con aspecto clinico y sin marca puede terminar en manos de alguien
# que lo tome por real.
MARCA_AGUA_DEMO = "DATOS SINTETICOS — DEMO"


class VersionPasaporte(Enum):
    """Las tres versiones. La edad de emision decide cual toca.

    El escalonamiento no es cosmetico: a los 14 el paciente no necesita saber
    como pedir una cita — necesita saber que tiene y que toma. Darle las dos
    paginas de la v3 a los 14 garantiza que no lea ninguna.
    """

    V1_14 = "v1"
    V2_16 = "v2"
    V3_17 = "v3"

    @property
    def edad_hito(self) -> int:
        return {
            VersionPasaporte.V1_14: 14,
            VersionPasaporte.V2_16: 16,
            VersionPasaporte.V3_17: 17,
        }[self]

    @property
    def extension(self) -> str:
        return {
            VersionPasaporte.V1_14: "media pagina",
            VersionPasaporte.V2_16: "1 pagina",
            VersionPasaporte.V3_17: "2 paginas",
        }[self]

    @property
    def captura_telefono_propio(self) -> bool:
        """Desde la v2 se pide el telefono DEL PACIENTE, no solo el del cuidador.

        A los 18 el vinculo con el cuidador puede haberse roto, y el paciente
        es quien tiene que poder ser contactado.
        """
        return self is not VersionPasaporte.V1_14

    @classmethod
    def para_edad(cls, edad: int) -> VersionPasaporte | None:
        """Que version corresponde a una edad. None fuera de la cohorte activa.

        14 y 15 -> v1 · 16 -> v2 · 17 -> v3.
        """
        if edad < 14 or edad >= 18:
            return None
        if edad < 16:
            return cls.V1_14
        if edad < 17:
            return cls.V2_16
        return cls.V3_17


class EstadoPasaporte(Enum):
    BORRADOR = "borrador"
    """Generado por el sistema, sin revisar. No se entrega ni se imprime como
    definitivo."""

    FIRMADO = "firmado"
    """Un medico lo reviso y lo firmo. Solo asi se entrega."""

    ANULADO = "anulado"
    """Se emitio una version posterior o se detecto un error."""


class PasaporteSinFirma(ErrorDominio):
    """Se intento entregar o exportar un pasaporte que nadie firmo."""


@dataclass(frozen=True, slots=True)
class SeccionPasaporte:
    """Un bloque de contenido del documento.

    `requiere_completar_a_mano` marca las secciones que salen con huecos —
    tipicamente dosis no verificadas en la fuente. El hueco es deliberado: un
    hueco visible obliga al medico a llenarlo; una dosis plausible pero
    inventada no obliga a nada.
    """

    titulo: str
    contenido: str
    requiere_completar_a_mano: bool = False
    generada_por_modelo: bool = False
    """True si el texto salio de un modelo de lenguaje. Se muestra en la
    interfaz de revision para que el medico sepa que mirar con mas cuidado."""


@dataclass(frozen=True, slots=True)
class Firma:
    """La firma del medico tratante. Sin esto el pasaporte no se entrega."""

    nombre_medico: str
    colegiatura: str
    fecha: date

    def __post_init__(self) -> None:
        if not self.nombre_medico.strip() or not self.colegiatura.strip():
            raise PasaporteSinFirma(
                "Una firma sin nombre o sin numero de colegiatura no es una firma."
            )


@dataclass
class Pasaporte:
    """El Pasaporte de Salud 18+ de un paciente, en una version concreta."""

    paciente_id: str
    version: VersionPasaporte
    fecha_emision: date
    secciones: list[SeccionPasaporte] = field(default_factory=list)
    estado: EstadoPasaporte = EstadoPasaporte.BORRADOR
    firma: Firma | None = None
    url_version_digital: str = ""
    """Destino del codigo QR. Vacio mientras no haya publicacion digital."""

    es_demo: bool = True
    """Mientras dure el hackathon, siempre True: el documento sale con marca
    de agua. PLAN_TECNICO §9."""

    @property
    def aviso_normativo(self) -> str:
        return AVISO_NORMATIVO

    @property
    def marca_agua(self) -> str | None:
        return MARCA_AGUA_DEMO if self.es_demo else None

    @property
    def esta_firmado(self) -> bool:
        return self.estado is EstadoPasaporte.FIRMADO and self.firma is not None

    @property
    def secciones_por_completar(self) -> tuple[SeccionPasaporte, ...]:
        """Las que salen con huecos. La interfaz de revision las muestra arriba."""
        return tuple(s for s in self.secciones if s.requiere_completar_a_mano)

    @property
    def secciones_generadas_por_modelo(self) -> tuple[SeccionPasaporte, ...]:
        return tuple(s for s in self.secciones if s.generada_por_modelo)

    def firmar(self, firma: Firma) -> None:
        """El medico revisa y firma. Es el unico camino a FIRMADO.

        No se comprueba que las secciones con huecos esten llenas: llenarlas es
        justamente lo que el medico hace con el papel en la mano. Lo que si se
        impide es firmar dos veces o firmar algo anulado.
        """
        if self.estado is EstadoPasaporte.ANULADO:
            raise PasaporteSinFirma("Un pasaporte anulado no se firma: se emite otro.")
        if self.esta_firmado:
            raise PasaporteSinFirma(
                f"El pasaporte de {self.paciente_id} ya lo firmo "
                f"{self.firma.nombre_medico if self.firma else ''}."
            )
        self.firma = firma
        self.estado = EstadoPasaporte.FIRMADO

    def anular(self) -> None:
        """Se emitio una version posterior o se detecto un error."""
        self.estado = EstadoPasaporte.ANULADO

    def exigir_firma(self) -> None:
        """Puerta que atraviesa toda salida clinica.

        La llaman el generador de PDF definitivo, el exportador FHIR y el
        despachador de avisos. Regla inviolable 4 del proyecto: ninguna salida
        clinica se emite sin revision humana explicita.
        """
        if not self.esta_firmado:
            raise PasaporteSinFirma(
                f"El pasaporte de {self.paciente_id} ({self.version.value}) esta en "
                f"estado {self.estado.value}. Ninguna salida clinica se emite sin "
                "firma del medico tratante."
            )

    def __str__(self) -> str:
        return (
            f"Pasaporte {self.version.value} de {self.paciente_id} "
            f"({self.fecha_emision.isoformat()}) — {self.estado.value}"
        )
