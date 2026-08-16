"""Caso de uso: el recorrido Entrenate de un adolescente.

Quien alimenta esto es el PACIENTE, no el personal de salud. No es doble
digitacion: nadie mas tenia este dato. Es la tercera de las tres puertas
legitimas por las que entra informacion al sistema.

La invariante que este caso de uso no puede romper nunca: **el aprendizaje no
bloquea ninguna transicion de la ruta de referencia.** Por eso aqui no hay —ni
puede haber— ninguna funcion que devuelva "listo para transferir".

Importa solo `dominio`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from relevo.dominio.entidades.diagnostico import ResultadoTRAQ
from relevo.dominio.entidades.leccion import Leccion
from relevo.dominio.entidades.progreso_aprendizaje import ProgresoAprendizaje
from relevo.dominio.objetos_valor.franja_etaria import FranjaEtaria
from relevo.dominio.objetos_valor.habilidad import EstadoHabilidad, Habilidad
from relevo.dominio.servicios.recomendador_leccion import (
    motivo_de_la_recomendacion,
    recomendar_habilidad,
    recomendar_leccion,
)


@dataclass(frozen=True, slots=True)
class VistaAprendizaje:
    """Todo lo que la pantalla de Entrenate necesita, en un solo objeto.

    Se devuelve completo en vez de por partes para que la vista no tenga que
    hacer cinco llamadas y decidir en que orden: decidir es trabajo de esta
    capa.
    """

    paciente_id: str
    franja: FranjaEtaria | None
    estados: Mapping[Habilidad, EstadoHabilidad]
    resumen: str
    siguiente: Leccion | None
    motivo: str
    lecciones: tuple[Leccion, ...]

    @property
    def total_logradas(self) -> int:
        return sum(1 for e in self.estados.values() if e is EstadoHabilidad.LOGRADA)

    @property
    def lecciones_completas(self) -> tuple[Leccion, ...]:
        """Las validadas clinicamente. Hoy es una sola, y se dice."""
        return tuple(le for le in self.lecciones if le.esta_completa)

    @property
    def lecciones_en_esqueleto(self) -> tuple[Leccion, ...]:
        return tuple(le for le in self.lecciones if not le.esta_completa)


@dataclass(frozen=True, slots=True)
class AvanzarAprendizaje:
    """Lee el recorrido, recomienda y registra avances.

    `catalogo` se inyecta: el contenido de las lecciones lo carga un adaptador
    desde `config/`, y ni el dominio ni este caso de uso tocan el disco.
    """

    catalogo: Mapping[Habilidad, Leccion]

    def ver(
        self,
        progreso: ProgresoAprendizaje,
        edad_anios: int,
        traq: ResultadoTRAQ | None,
    ) -> VistaAprendizaje:
        habilidad = recomendar_habilidad(traq, edad_anios, progreso)
        return VistaAprendizaje(
            paciente_id=progreso.paciente_id,
            franja=FranjaEtaria.para_edad(edad_anios),
            estados=dict(progreso.estados),
            resumen=progreso.resumen(),
            siguiente=recomendar_leccion(traq, edad_anios, progreso, self.catalogo),
            motivo=motivo_de_la_recomendacion(traq, habilidad),
            lecciones=tuple(
                self.catalogo[h] for h in Habilidad if h in self.catalogo
            ),
        )

    def registrar_avance(
        self,
        progreso: ProgresoAprendizaje,
        habilidad: Habilidad,
        estado: EstadoHabilidad,
        hoy: date,
        nota: str = "",
    ) -> ProgresoAprendizaje:
        """Lo marca el adolescente sobre si mismo."""
        progreso.registrar(habilidad, estado, hoy, nota=nota)
        return progreso

    def abrir_leccion(
        self, progreso: ProgresoAprendizaje, numero: int
    ) -> Leccion | None:
        """Devuelve la leccion y anota que la vio.

        Ver una leccion y lograr la habilidad son cosas distintas: si se
        confundieran, tendriamos una metrica que sube sola con solo abrir
        pantallas.
        """
        habilidad = Habilidad.por_numero(numero)
        if habilidad is None:
            return None
        leccion = self.catalogo.get(habilidad)
        if leccion is None:
            return None
        progreso.marcar_leccion_vista(numero)
        return leccion
