"""Como va un adolescente en su recorrido de Entrenate.

═══════════════════════════════════════════════════════════════════════════════
LA INVARIANTE QUE NO SE NEGOCIA
═══════════════════════════════════════════════════════════════════════════════

    La ruta de aprendizaje NUNCA bloquea, retrasa ni condiciona una transicion
    de la ruta de referencia. No existe un readiness score que autorice la
    transferencia.

Es la mejor decision de diseno que trajo el segundo MVP y hay que blindarla.
El motivo es clinico y es serio: si el sistema pudiera retener una derivacion
porque el adolescente no completo sus lecciones, habriamos convertido una
herramienta de acompanamiento en una barrera de acceso — y el paciente que
menos completa lecciones es exactamente el que mas riesgo tiene de quedarse sin
servicio a los 18.

Esta entidad no tiene ningun metodo que devuelva "listo para transferir", y no
debe tenerlo nunca. `tests/dominio/test_aprendizaje_no_bloquea_referencia.py`
lo vigila.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from relevo.dominio.objetos_valor.franja_etaria import FranjaEtaria
from relevo.dominio.objetos_valor.habilidad import EstadoHabilidad, Habilidad


@dataclass(frozen=True, slots=True)
class AvanceHabilidad:
    """Un cambio de estado en una habilidad, con fecha. Inmutable.

    Se guarda el historial y no solo el ultimo estado porque `NECESITA_REFUERZO`
    solo significa algo si se sabe que antes estuvo `LOGRADA`. Sin historial,
    un refuerzo es indistinguible de no haber empezado.
    """

    habilidad: Habilidad
    estado: EstadoHabilidad
    fecha: date
    nota: str = ""


@dataclass
class ProgresoAprendizaje:
    """El recorrido de un adolescente por las siete habilidades.

    Vive aparte del `Paciente` a proposito: lo alimenta el propio paciente,
    no el personal de salud (principio de cero doble digitacion). Mezclarlo con
    el expediente clinico invitaria a que alguien del INSN lo rellenara "para
    que quede completo", que es justo lo que no puede pasar — el dato pierde
    todo su valor si no lo puso quien esta aprendiendo.
    """

    paciente_id: str
    estados: dict[Habilidad, EstadoHabilidad] = field(default_factory=dict)
    historial: list[AvanceHabilidad] = field(default_factory=list)
    lecciones_vistas: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        # Toda habilidad no registrada esta POR_INICIAR. Se materializa para
        # que la interfaz pinte siempre las siete y nadie tenga que acordarse
        # de que las que faltan cuentan como cero.
        for habilidad in Habilidad:
            self.estados.setdefault(habilidad, EstadoHabilidad.POR_INICIAR)

    # ── Lecturas ─────────────────────────────────────────────────────────────

    def estado_de(self, habilidad: Habilidad) -> EstadoHabilidad:
        return self.estados.get(habilidad, EstadoHabilidad.POR_INICIAR)

    @property
    def logradas(self) -> tuple[Habilidad, ...]:
        return tuple(
            h for h in Habilidad if self.estado_de(h) is EstadoHabilidad.LOGRADA
        )

    @property
    def pendientes(self) -> tuple[Habilidad, ...]:
        """Las que todavia piden trabajo, en orden de leccion.

        Es lo que alimenta "¿que tengo que hacer yo?" en la vista del paciente.
        """
        return tuple(h for h in Habilidad if self.estado_de(h).pide_trabajo)

    @property
    def sin_empezar(self) -> tuple[Habilidad, ...]:
        return tuple(
            h for h in Habilidad if self.estado_de(h) is EstadoHabilidad.POR_INICIAR
        )

    @property
    def total_logradas(self) -> int:
        return len(self.logradas)

    def resumen(self) -> str:
        """Una linea para la cabecera de la vista. Sin porcentajes.

        Un porcentaje invita a compararse con otros y a leer el recorrido como
        una nota. "3 de 7 habilidades logradas" describe donde esta uno.
        """
        return f"{self.total_logradas} de {len(Habilidad)} habilidades logradas"

    # ── Escrituras ───────────────────────────────────────────────────────────

    def registrar(
        self,
        habilidad: Habilidad,
        estado: EstadoHabilidad,
        fecha: date,
        nota: str = "",
    ) -> AvanceHabilidad:
        """Anota un avance. Lo hace el paciente, no el personal de salud."""
        avance = AvanceHabilidad(
            habilidad=habilidad, estado=estado, fecha=fecha, nota=nota
        )
        self.estados[habilidad] = estado
        self.historial.append(avance)
        return avance

    def marcar_leccion_vista(self, numero: int) -> None:
        """Que el adolescente la abrio. No implica que la haya logrado.

        Se guardan por separado a proposito: abrir una leccion y adquirir la
        habilidad son cosas distintas, y confundirlas produciria una metrica
        que sube sola.
        """
        self.lecciones_vistas.add(numero)

    def franja(self, edad: int) -> FranjaEtaria | None:
        """La franja que le toca por edad. None fuera del recorrido."""
        return FranjaEtaria.para_edad(edad)

    def __str__(self) -> str:
        return f"{self.paciente_id} · {self.resumen()}"
