"""Quien entra al sistema, en que cohorte y con que version del Pasaporte.

PLAN_TECNICO §1 y §6.1. Dos preguntas distintas que conviene no mezclar:

    1. ¿Es un paciente cronico, raro o complejo?   -> elegibilidad, por clinica
    2. ¿En que momento de la ventana esta?         -> cohorte, por edad

Un paciente puede ser elegible y no estar todavia en la cohorte activa (tiene
12 anios), o estar en la ventana y no ser elegible (viene por una fractura).
El sistema solo trabaja con quien cumple las dos.

Las tres fuentes de elegibilidad (§6.1), ninguna inventada por nosotros:

    RM 478-2026-MINSA          -> 558 diagnosticos raros en CIE-10
    Complex Chronic Cond. v2   -> 10 categorias (Feudtner, BMC Pediatrics 2014)
    Codigos cronicos del INSN  -> los agrega el medico en reglas_transicion.yaml

El dominio no lee esas listas: las recibe. Quien las carga de `config/` es un
adaptador.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from relevo.dominio.entidades.diagnostico import CategoriaCCC
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import VersionPasaporte
from relevo.dominio.objetos_valor.ventana_transicion import Cohorte


class MotivoInclusion(Enum):
    """Por que este paciente le interesa al sistema.

    Se guardan todos los motivos, no solo el primero: en la interfaz el equipo
    filtra por motivo, y "raro" y "complejo" no llevan al mismo servicio de
    adultos.
    """

    ENFERMEDAD_RARA = "enfermedad_rara"
    CONDICION_CRONICA_COMPLEJA = "condicion_cronica_compleja"
    DEPENDENCIA_TECNOLOGICA = "dependencia_tecnologica"
    CRONICA_LOCAL = "cronica_local"
    POLIMEDICADO = "polimedicado"

    @property
    def etiqueta(self) -> str:
        return {
            MotivoInclusion.ENFERMEDAD_RARA: "Enfermedad rara (RM 478-2026-MINSA)",
            MotivoInclusion.CONDICION_CRONICA_COMPLEJA: "Condición crónica compleja (CCC v2)",
            MotivoInclusion.DEPENDENCIA_TECNOLOGICA: "Dependencia tecnológica o de dispositivos",
            MotivoInclusion.CRONICA_LOCAL: "Enfermedad crónica de seguimiento en INSN",
            MotivoInclusion.POLIMEDICADO: "Polimedicación crónica activa",
        }[self]


# Numero de medicamentos a partir del cual se considera polimedicacion.
# Cinco es el corte de uso mas extendido en la literatura de polifarmacia.
# PROVISIONAL — TODO: confirmar con mentor si aplica igual en pediatria.
UMBRAL_POLIMEDICACION = 5


@dataclass(frozen=True, slots=True)
class ResultadoClasificacion:
    """Que se decidio sobre un paciente y por que.

    `explicacion` no es decorativa: es lo que el equipo lee para entender por
    que alguien aparecio en su lista. Una lista sin motivo se deja de mirar.
    """

    paciente_id: str
    es_elegible: bool
    cohorte: Cohorte
    motivos: tuple[MotivoInclusion, ...] = field(default_factory=tuple)
    version_pasaporte: VersionPasaporte | None = None
    """La que toca por edad. None si no esta en la cohorte activa."""

    requiere_captura_contacto: bool = False
    """True si no hay ningun contacto con verificacion vigente.

    Pasa mas de lo que parece: la plantilla oficial del INSN no tiene campo de
    telefono, asi que el numero que hay se anoto informalmente hace anios.
    """

    @property
    def entra_al_sistema(self) -> bool:
        """Elegible Y dentro de la ventana o ya en seguimiento.

        La cohorte PREVIA queda registrada pero no se trabaja: avisarle a los
        12 anios no sirve de nada y satura la lista del equipo.
        """
        return self.es_elegible and self.cohorte in (Cohorte.ACTIVA, Cohorte.SEGUIMIENTO)

    @property
    def explicacion(self) -> str:
        if not self.es_elegible:
            return "No cumple criterio de cronicidad, rareza ni complejidad"
        motivos = " · ".join(m.etiqueta for m in self.motivos)
        return f"{self.cohorte.value}: {motivos}"

    def __str__(self) -> str:
        return f"{self.paciente_id} — {self.explicacion}"


@dataclass(frozen=True, slots=True)
class ClasificadorCohorte:
    """Aplica los criterios de elegibilidad y ubica al paciente en la ventana.

    `codigos_cronicos_locales` son prefijos CIE-10 que el medico del INSN
    agrega en `config/reglas_transicion.yaml`. Vacio por defecto: no inventamos
    la lista.
    """

    codigos_cronicos_locales: frozenset[str] = field(default_factory=frozenset)
    umbral_polimedicacion: int = UMBRAL_POLIMEDICACION

    def clasificar(self, paciente: Paciente, hoy: date) -> ResultadoClasificacion:
        motivos = self._motivos(paciente)
        ventana = paciente.ventana(hoy)
        cohorte = ventana.cohorte
        hito = ventana.hito_actual

        return ResultadoClasificacion(
            paciente_id=paciente.id,
            es_elegible=bool(motivos),
            cohorte=cohorte,
            motivos=motivos,
            version_pasaporte=(
                VersionPasaporte.para_edad(ventana.edad) if hito is not None else None
            ),
            requiere_captura_contacto=not paciente.tiene_contacto_vigente(hoy),
        )

    def _motivos(self, paciente: Paciente) -> tuple[MotivoInclusion, ...]:
        motivos: list[MotivoInclusion] = []

        if paciente.tiene_enfermedad_rara:
            motivos.append(MotivoInclusion.ENFERMEDAD_RARA)

        # Toda categoria de CCC v2 distinta de OTRA es, por definicion del
        # articulo, una condicion cronica compleja. La categoria la asigna el
        # adaptador que cruza el CIE-10 contra `ccc_v2_categorias.csv`.
        if any(
            dx.categoria is not CategoriaCCC.OTRA for dx in paciente.diagnosticos
        ):
            motivos.append(MotivoInclusion.CONDICION_CRONICA_COMPLEJA)

        if paciente.dispositivos:
            motivos.append(MotivoInclusion.DEPENDENCIA_TECNOLOGICA)

        if self._tiene_codigo_cronico_local(paciente):
            motivos.append(MotivoInclusion.CRONICA_LOCAL)

        if len(paciente.medicamentos) >= self.umbral_polimedicacion:
            motivos.append(MotivoInclusion.POLIMEDICADO)

        return tuple(motivos)

    def _tiene_codigo_cronico_local(self, paciente: Paciente) -> bool:
        if not self.codigos_cronicos_locales:
            return False
        return any(
            dx.codigo.coincide_con_prefijo(prefijo)
            for dx in paciente.diagnosticos
            for prefijo in self.codigos_cronicos_locales
        )


def contar_por_cohorte(
    resultados: Iterable[ResultadoClasificacion],
) -> dict[Cohorte, int]:
    """Cuantos elegibles hay en cada cohorte. Alimenta el tablero.

    Solo cuenta elegibles: el total de pacientes del hospital no es una cifra
    que este sistema deba mostrar.
    """
    conteo = {cohorte: 0 for cohorte in Cohorte}
    for r in resultados:
        if r.es_elegible:
            conteo[r.cohorte] += 1
    return conteo
