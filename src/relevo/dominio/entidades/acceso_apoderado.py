"""El acceso del apoderado, y el dia exacto en que se corta.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTO ES UN MECANISMO Y NO UNA PANTALLA
═══════════════════════════════════════════════════════════════════════════════

Antes de los 18, el padre, la madre o el tutor acceden por patria potestad
(Codigo Civil peruano, arts. 418 y ss.). Desde el dia del cumpleanos 18, esa
base legal desaparece: el paciente adquiere capacidad de ejercicio y sus datos
de salud son datos sensibles suyos (Ley 29733 de Proteccion de Datos
Personales, art. 2.5).

El acceso se corta AUTOMATICAMENTE en esa fecha, y solo continua si el propio
paciente lo otorga con un consentimiento explicito que queda fechado y asentado
en la cadena de auditoria.

Esto convierte una pantalla en un mecanismo, y es lo que un jurado de salud
reconoce como serio. Tambien es el codigo que la Leccion 6 de Entrenate
—"Que cambia cuando cumplo 18"— le explica al adolescente: contenido y
mecanismo cuentan la misma historia, que es lo que hace que ninguno de los dos
suene a discurso.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from relevo.dominio.excepciones import ErrorDominio
from relevo.dominio.objetos_valor.ventana_transicion import EDAD_CORTE, cumpleanos_18


class AccesoDenegado(ErrorDominio):
    """Se intento leer algo del paciente sin base legal para hacerlo."""


class BaseLegalAcceso(Enum):
    """Por que este apoderado puede ver algo. Nunca "porque siempre pudo"."""

    PATRIA_POTESTAD = "patria_potestad"
    """Menor de 18. Codigo Civil peruano, arts. 418 y ss."""

    CONSENTIMIENTO_DEL_PACIENTE = "consentimiento_del_paciente"
    """El paciente, ya mayor, lo autorizo expresamente. Ley 29733."""

    SIN_BASE = "sin_base"
    """Cumplio 18 y no hay consentimiento. El acceso esta cortado."""

    @property
    def permite_acceso(self) -> bool:
        return self is not BaseLegalAcceso.SIN_BASE

    @property
    def etiqueta(self) -> str:
        return {
            BaseLegalAcceso.PATRIA_POTESTAD: "Patria potestad (paciente menor de edad)",
            BaseLegalAcceso.CONSENTIMIENTO_DEL_PACIENTE: (
                "Consentimiento explicito del paciente"
            ),
            BaseLegalAcceso.SIN_BASE: "Sin base legal — acceso cortado a los 18",
        }[self]

    @property
    def norma(self) -> str:
        return {
            BaseLegalAcceso.PATRIA_POTESTAD: "Codigo Civil, arts. 418 y ss.",
            BaseLegalAcceso.CONSENTIMIENTO_DEL_PACIENTE: (
                "Ley 29733, art. 2.5 — datos sensibles de salud"
            ),
            BaseLegalAcceso.SIN_BASE: "Ley 29733, art. 2.5",
        }[self]


@dataclass(frozen=True, slots=True)
class ConsentimientoExplicito:
    """El permiso que el paciente mayor de edad le da a su apoderado.

    Inmutable y fechado. Revocarlo no borra este registro: se anota la
    revocacion aparte (`AccesoApoderado.revocado_en`). Un consentimiento que se
    puede borrar no sirve como prueba de nada, y aqui la prueba es el punto.
    """

    otorgado_por_paciente: str
    fecha: date
    alcance: str = "estado del ciclo de transicion"
    """Que se autoriza a ver. Por defecto lo minimo util: en que punto va el
    tramite. NO incluye el Pasaporte completo salvo que se diga expresamente —
    el consentimiento es especifico, no una llave maestra."""

    medio: str = ""
    """Como se recogio: en persona, por la aplicacion, por escrito. Se guarda
    porque un consentimiento sin constancia de como se obtuvo es una casilla
    marcada, no un consentimiento."""

    def __post_init__(self) -> None:
        if not self.otorgado_por_paciente.strip():
            raise ValueError(
                "Un consentimiento sin decir quien lo otorgo no es un "
                "consentimiento."
            )


@dataclass
class AccesoApoderado:
    """El vinculo entre un apoderado y un paciente, con su base legal.

    La base legal se CALCULA en cada consulta a partir de la fecha; no se
    guarda como un booleano. Un `tiene_acceso: bool` guardado en base de datos
    seguiria valiendo True el dia despues del cumpleanos 18, y ese es
    exactamente el fallo que este modulo existe para hacer imposible.
    """

    paciente_id: str
    fecha_nacimiento_paciente: date
    nombre_apoderado: str
    parentesco: str = ""
    consentimiento: ConsentimientoExplicito | None = None
    revocado_en: date | None = None
    historial: list[tuple[str, date]] = field(default_factory=list)
    """Otorgamientos y revocaciones, en orden. Va a la cadena de auditoria."""

    # ── La regla ─────────────────────────────────────────────────────────────

    @property
    def fecha_de_corte(self) -> date:
        """El dia en que caduca el acceso por patria potestad."""
        return cumpleanos_18(self.fecha_nacimiento_paciente)

    def base_legal(self, hoy: date) -> BaseLegalAcceso:
        """Por que —o por que no— este apoderado puede ver algo hoy."""
        if hoy < self.fecha_de_corte:
            return BaseLegalAcceso.PATRIA_POTESTAD
        if self.consentimiento is None:
            return BaseLegalAcceso.SIN_BASE
        if self.revocado_en is not None and hoy >= self.revocado_en:
            return BaseLegalAcceso.SIN_BASE
        if self.consentimiento.fecha > hoy:
            # Un consentimiento con fecha futura no vale todavia.
            return BaseLegalAcceso.SIN_BASE
        return BaseLegalAcceso.CONSENTIMIENTO_DEL_PACIENTE

    def tiene_acceso(self, hoy: date) -> bool:
        return self.base_legal(hoy).permite_acceso

    def exigir_acceso(self, hoy: date) -> None:
        """Puerta que atraviesa toda lectura del apoderado.

        La llama la capa de aplicacion antes de devolver nada. Lanza en vez de
        devolver False para que olvidarse de comprobar el resultado no sea un
        camino posible.
        """
        base = self.base_legal(hoy)
        if base.permite_acceso:
            return
        raise AccesoDenegado(
            f"{self.nombre_apoderado} no puede acceder a los datos de "
            f"{self.paciente_id}: el paciente cumplio {EDAD_CORTE} anios el "
            f"{self.fecha_de_corte.isoformat()} y no hay consentimiento "
            "explicito vigente. Sus datos de salud son datos sensibles suyos "
            "(Ley 29733, art. 2.5)."
        )

    def dias_restantes(self, hoy: date) -> int:
        """Dias hasta el corte. Negativo si ya ocurrio.

        Alimenta el aviso anticipado de la vista del apoderado. El aviso existe
        porque el corte no puede ser una sorpresa: la familia tiene que poder
        hablarlo antes, no descubrirlo el dia que deja de funcionar.
        """
        return (self.fecha_de_corte - hoy).days

    def aviso_de_caducidad(self, hoy: date) -> str | None:
        """El texto que la vista del apoderado muestra. None si no toca.

        Se avisa a partir de 90 dias antes: es tiempo suficiente para que la
        conversacion ocurra sin prisa, y coincide con el horizonte de riesgo
        del corte etario, de modo que las dos cuentas atras del sistema hablan
        de la misma ventana.
        """
        restantes = self.dias_restantes(hoy)
        if restantes < 0:
            if self.tiene_acceso(hoy):
                return (
                    f"{self.paciente_id} ya es mayor de edad. Usted mantiene "
                    "acceso porque el paciente lo autorizo expresamente, y "
                    "puede retirarlo cuando quiera."
                )
            return (
                f"{self.paciente_id} cumplio 18 anios el "
                f"{self.fecha_de_corte.isoformat()}. Su acceso termino ese dia. "
                "Solo el paciente puede volver a autorizarlo."
            )
        if restantes <= 90:
            return (
                f"En {restantes} dias {self.paciente_id} cumple 18 anios y su "
                "acceso a esta informacion terminara automaticamente. A partir "
                "de esa fecha solo continuara si el paciente lo autoriza."
            )
        return None

    # ── Consentimiento ───────────────────────────────────────────────────────

    def otorgar(self, consentimiento: ConsentimientoExplicito) -> None:
        """El paciente autoriza. Solo el puede.

        No se comprueba que el paciente sea mayor de edad: otorgarlo antes de
        los 18 es valido y util —deja el acceso preparado para el dia del
        corte— y es justamente lo que la Leccion 6 le propone hacer.
        """
        self.consentimiento = consentimiento
        self.revocado_en = None
        self.historial.append(("otorgado", consentimiento.fecha))

    def revocar(self, fecha: date) -> None:
        """El paciente retira el permiso. Efecto inmediato desde esa fecha.

        No borra el consentimiento anterior: se anota la revocacion. Borrarlo
        haria imposible responder despues a "¿quien pudo ver esto y cuando?".
        """
        if self.consentimiento is None:
            raise AccesoDenegado(
                "No hay consentimiento que revocar. El acceso por patria "
                "potestad caduca solo, en la fecha del cumpleanos 18."
            )
        self.revocado_en = fecha
        self.historial.append(("revocado", fecha))

    def __str__(self) -> str:
        return (
            f"{self.nombre_apoderado} ({self.parentesco or 'apoderado'}) de "
            f"{self.paciente_id} — corte el {self.fecha_de_corte.isoformat()}"
        )
