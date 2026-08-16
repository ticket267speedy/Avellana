"""Quien tiene el turno ahora.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTE ARCHIVO EXISTE
═══════════════════════════════════════════════════════════════════════════════

El INSN lo pidio dos veces en su propio documento: en el entregable 1 ("un
modelo que establezca roles, etapas, RESPONSABLES, hitos") y otra vez en su
Insight 5 ("la solucion debe incorporar RESPONSABLES, criterios, alertas,
flujo de derivacion y seguimiento").

Hasta ahora, en nuestro modelo, nadie era dueno de nada. Un paciente con el
plazo vencido no tenia a quien le tocara. Un estado sin responsable es un
estado donde todos suponen que lo esta haciendo otro, y eso es exactamente el
mecanismo por el que un expediente se queda cinco meses en un cajon.

**"¿Quien tiene el turno ahora?"** — usar esa pregunta literal en la interfaz.
Es la mejor pieza de comunicacion del proyecto: cabe en una linea, no necesita
explicacion y le sirve igual al paciente que a la trabajadora social.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from enum import Enum

from relevo.dominio.objetos_valor.estado_ciclo import EstadoCiclo


class Responsable(Enum):
    """A quien le toca mover el ciclo desde donde esta."""

    EQUIPO_INSN = "equipo_insn"
    """El equipo de transicion del INSN. Ojo: tener el turno NO implica atender
    clinicamente al paciente. Con el paciente >= 18 el turno sigue siendo suyo,
    pero solo para gestion administrativa (ver `reingreso.py`)."""

    HOSPITAL_RECEPTOR = "hospital_receptor"
    """El establecimiento de adultos al que se refirio el caso."""

    PACIENTE = "paciente"
    """El propio paciente. Tiene el turno cuando lo unico que falta es que se
    presente a su cita: nadie puede hacer eso por el."""

    APODERADO = "apoderado"
    """Padre, madre o tutor. Solo antes de los 18, o despues con consentimiento
    explicito del paciente (ver `entidades/acceso_apoderado.py`)."""

    NADIE = "nadie"
    """Solo para PRIMERA_ATENCION_CONFIRMADA. No hay nada pendiente.

    Un valor explicito y no `None`: "nadie tiene el turno porque esto termino
    bien" y "no sabemos de quien es el turno" son cosas distintas, y confundir
    las dos es como se pierde un paciente."""

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    @property
    def es_del_insn(self) -> bool:
        return self is Responsable.EQUIPO_INSN

    @property
    def es_externo_al_insn(self) -> bool:
        """True si el INSN no puede desatascar esto por si solo.

        Sirve para el filtro del radar: separar "requiere accion del INSN" de
        "esperando al receptor" es lo que evita que el equipo pierda la manana
        revisando expedientes en los que no puede hacer nada.
        """
        return self in (Responsable.HOSPITAL_RECEPTOR, Responsable.PACIENTE)

    def __str__(self) -> str:
        return self.etiqueta


_ETIQUETAS: dict[Responsable, str] = {
    Responsable.EQUIPO_INSN: "Equipo de transición del INSN",
    Responsable.HOSPITAL_RECEPTOR: "Hospital receptor",
    Responsable.PACIENTE: "El paciente",
    Responsable.APODERADO: "El apoderado",
    Responsable.NADIE: "Nadie — el ciclo terminó bien",
}


# A quien le toca en cada estado. Funcion pura escrita como tabla para que se
# pueda leer de un vistazo y discutir con un medico sin abrir un depurador.
_RESPONSABLE_POR_ESTADO: dict[EstadoCiclo, Responsable] = {
    # El expediente lo arma el INSN. Nadie mas puede.
    EstadoCiclo.PREPARACION: Responsable.EQUIPO_INSN,
    # Enviada: la pelota esta del otro lado, esperando acuse de recibo.
    EstadoCiclo.REFERENCIA_ENVIADA: Responsable.HOSPITAL_RECEPTOR,
    EstadoCiclo.RECEPCION_CONFIRMADA: Responsable.HOSPITAL_RECEPTOR,
    EstadoCiclo.EN_EVALUACION: Responsable.HOSPITAL_RECEPTOR,
    # Aceptado pero sin cita: programarla es del receptor, no del paciente.
    EstadoCiclo.ACEPTADO_CON_SERVICIO: Responsable.HOSPITAL_RECEPTOR,
    # Con fecha en la mano, lo unico que falta es presentarse.
    EstadoCiclo.CITA_PROGRAMADA: Responsable.PACIENTE,
    EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA: Responsable.NADIE,
    # Buscar a quien se perdio le toca a quien lo tenia: el INSN.
    EstadoCiclo.PERDIDA_DE_SEGUIMIENTO: Responsable.EQUIPO_INSN,
    # Reclasificar un ciclo reabierto es trabajo del INSN, y es administrativo.
    EstadoCiclo.REINGRESO: Responsable.EQUIPO_INSN,
}


def responsable_de(estado: EstadoCiclo) -> Responsable:
    """¿Quien tiene el turno ahora?

    Funcion pura, sin estado y sin excepciones: todos los estados tienen
    responsable. Que un estado se quedara sin entrada aqui seria justamente el
    agujero que este modulo viene a tapar, asi que la tabla se valida al
    importarse (ver abajo).
    """
    return _RESPONSABLE_POR_ESTADO[estado]


# Un estado sin responsable es un estado donde el expediente se queda quieto y
# nadie se entera. Se comprueba al importar el modulo y no en un test para que
# el fallo aparezca en cuanto alguien anada un estado, no cuando alguien
# recuerde correr la suite.
_faltantes = [e.name for e in EstadoCiclo if e not in _RESPONSABLE_POR_ESTADO]
if _faltantes:  # pragma: no cover - red de seguridad de desarrollo
    raise RuntimeError(
        "Estados sin responsable asignado: "
        + ", ".join(_faltantes)
        + ". Un estado sin dueno es un expediente parado que nadie reclama."
    )
