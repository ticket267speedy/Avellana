"""Las cuatro franjas de la ruta de aprendizaje Entrenate.

NOTA DE VOCABULARIO, OBLIGATORIA EN TODO EL PROYECTO
Las unidades del recorrido educativo se llaman LECCIONES, nunca "modulos". En
software "modulo" significa otra cosa y ya causo confusion en el equipo.

POR QUE HAY FRANJAS Y NO SOLO EDADES
La segunda cita de paciente que el propio INSN recogio en su trabajo de campo:

    "Cuando fui al medico del servicio para adultos, no sabia como responder a
     sus preguntas porque mi mama siempre lo hacia por mi."

Por eso el recorrido empieza a los 11 y no a los 17. A los 18 ya es tarde para
aprender. La franja decide QUE se le pide al adolescente en cada momento, y se
mapea sobre el Pasaporte escalonado que ya existia — no lo duplica.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from enum import Enum

from relevo.dominio.entidades.pasaporte import VersionPasaporte


class FranjaEtaria(Enum):
    """La etapa del recorrido educativo segun la edad."""

    EXPLORA = "explora"
    """11-12. Previa a cualquier version del Pasaporte. Aqui no se pide
    autonomia: se pide curiosidad sobre la propia condicion."""

    PREPARADOS = "preparados"
    """13-14. Coincide con el Pasaporte v1: que tengo, que tomo, a que soy
    alergico."""

    LISTOS = "listos"
    """15-16. Coincide con el v2: como pido una cita, que hago si me siento
    mal, que pregunto en consulta."""

    YA = "ya"
    """17-18. Coincide con el v3, el completo. Es la ultima franja: despues de
    esto el paciente esta en el sistema de adultos."""

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    @property
    def rango(self) -> tuple[int, int]:
        """Edades que cubre, ambas inclusive."""
        return _RANGOS[self]

    @property
    def version_pasaporte(self) -> VersionPasaporte | None:
        """La version del Pasaporte que le corresponde. None en EXPLORA.

        MAPEO, no duplicado. El Pasaporte escalonado ya existia con sus tres
        versiones a los 14, 16 y 17: la ruta de aprendizaje se monta encima en
        vez de inventar un segundo calendario que se desincronice del primero.

        EXPLORA no tiene version porque a los 11 anios no hay Pasaporte que
        emitir todavia; hay aprendizaje que empezar.
        """
        return _VERSION_POR_FRANJA[self]

    @classmethod
    def para_edad(cls, edad: int) -> FranjaEtaria | None:
        """Que franja corresponde a una edad. None fuera del recorrido.

        Por debajo de 11 el recorrido no ha empezado; a partir de 19 el
        paciente lleva mas de un anio en el sistema de adultos y el material
        educativo de transicion ya no le habla a el.
        """
        for franja, (minimo, maximo) in _RANGOS.items():
            if minimo <= edad <= maximo:
                return franja
        return None

    def __str__(self) -> str:
        return self.etiqueta


_ETIQUETAS: dict[FranjaEtaria, str] = {
    FranjaEtaria.EXPLORA: "Explora (11-12)",
    FranjaEtaria.PREPARADOS: "Preparados (13-14)",
    FranjaEtaria.LISTOS: "Listos (15-16)",
    FranjaEtaria.YA: "Ya (17-18)",
}

_RANGOS: dict[FranjaEtaria, tuple[int, int]] = {
    FranjaEtaria.EXPLORA: (11, 12),
    FranjaEtaria.PREPARADOS: (13, 14),
    FranjaEtaria.LISTOS: (15, 16),
    FranjaEtaria.YA: (17, 18),
}

_VERSION_POR_FRANJA: dict[FranjaEtaria, VersionPasaporte | None] = {
    FranjaEtaria.EXPLORA: None,
    FranjaEtaria.PREPARADOS: VersionPasaporte.V1_14,
    FranjaEtaria.LISTOS: VersionPasaporte.V2_16,
    FranjaEtaria.YA: VersionPasaporte.V3_17,
}
