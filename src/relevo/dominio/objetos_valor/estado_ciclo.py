"""Los nueve estados del ciclo de transicion.

═══════════════════════════════════════════════════════════════════════════════
CORTE ETARIO Y REINGRESO — leer antes de tocar este archivo
═══════════════════════════════════════════════════════════════════════════════

Esto resuelve una confusion que ya costo tiempo al equipo.

**Cumplir 18 anios NO es el fracaso del sistema.** La primera cita en el
hospital de adultos ocurre, por definicion, despues de los 18. El corte etario
del INSN impide la ATENCION PEDIATRICA, no la continuidad del tramite. Un ciclo
que sigue avanzando con el paciente ya mayor de edad esta funcionando como debe.

**El fracaso es cumplir 18 sin destino asegurado**, es decir con el ciclo en un
estado anterior a `ACEPTADO_CON_SERVICIO`. Esa es la metrica estrella de
fracaso y va arriba de todo en el radar. Vive en `servicios/corte_etario.py`.

**REINGRESO es un estado del ciclo de transicion, no un reingreso al INSN.** El
ciclo es un artefacto administrativo que vive en Relevo, no una plaza de
hospitalizacion. Que se reabra no implica ninguna atencion clinica pediatrica.
Con el paciente >= 18 anios, un ciclo reabierto solo habilita acciones
administrativas — reenviar el Pasaporte, contactar al receptor, contactar a la
familia — y nunca acciones clinicas del INSN. Eso esta impedido por codigo en
`objetos_valor/reingreso.py`, no solo documentado aqui.

# TODO: confirmar con mentor — si el equipo de transicion del INSN esta
# facultado para gestion administrativa de un ex-paciente mayor de 18 anios.
# Provisional: se asume que si, porque la NT 018-MINSA obliga a la
# contrarreferencia y esa obligacion no caduca con la edad del paciente.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from enum import Enum


class EstadoCiclo(Enum):
    """Las nueve etapas de la derivacion.

    Sustituye a las seis originales de PLAN_TECNICO §7. Dos motivos:

    1. La rubrica del INSN nombra literalmente `perdida de seguimiento` y
       `reingreso`, y ninguno existia. `PERDIDA_DE_SEGUIMIENTO` es el desenlace
       que el proyecto entero existe para evitar: tenia que ser nombrable.
    2. `REFERENCIA_ACEPTADA` mezclaba tres hechos distintos del receptor —
       acusar recibo, evaluar y aceptar asignando servicio — y esa mezcla
       escondia justo el tramo donde el proceso se rompe.

    El valor es una cadena y no un entero: el orden de avance vive en `orden`,
    que es explicito y admite estados fuera de la linea recta. Comparar
    `estado.value` para saber quien va mas adelante dejo de tener sentido en
    cuanto aparecieron `PERDIDA_DE_SEGUIMIENTO` y `REINGRESO`.
    """

    PREPARACION = "preparacion"
    """El equipo del INSN arma el expediente: Pasaporte, epicrisis, destino
    propuesto. Nada ha salido todavia de la institucion."""

    REFERENCIA_ENVIADA = "referencia_enviada"
    """Salio hacia el establecimiento receptor. Nadie del otro lado ha dicho
    aun que la recibio."""

    RECEPCION_CONFIRMADA = "recepcion_confirmada"
    """El receptor acuso recibo. NO significa que la haya aceptado.

    La separacion respecto de EN_EVALUACION no es cosmetica: ahi exactamente
    vive el 0.55 % de contrarreferencia del estudio de DIRIS Lima Norte
    (110 contrarreferencias sobre 19 951 referencias, Rev Med Hered). Cuando un
    solo estado cubre "llego" y "lo estan viendo", un expediente que nadie
    abrio es indistinguible de uno en evaluacion, y el rechazo silencioso se
    vuelve invisible."""

    EN_EVALUACION = "en_evaluacion"
    """Un medico del receptor esta revisando el caso. Aqui es donde se pide
    informacion complementaria, y esa peticion es lo unico que convierte un
    rechazo silencioso en algo trazable."""

    ACEPTADO_CON_SERVICIO = "aceptado_con_servicio"
    """Aceptado Y con servicio/medico asignado. El primer estado con destino
    asegurado: a partir de aqui, cumplir 18 ya no es un fracaso.

    "Aceptado" a secas no bastaba. Una aceptacion sin servicio concreto es una
    carta amable que no le da cita a nadie."""

    CITA_PROGRAMADA = "cita_programada"
    """Hay fecha. El turno pasa al paciente: es quien tiene que presentarse."""

    PRIMERA_ATENCION_CONFIRMADA = "primera_atencion_confirmada"
    """El paciente llego y fue atendido. Terminal-exitoso, pero NO inmutable:
    puede pasar a REINGRESO si el seguimiento no continua."""

    PERDIDA_DE_SEGUIMIENTO = "perdida_de_seguimiento"
    """Se perdio el rastro. El desenlace que el sistema existe para evitar y
    que, hasta ahora, nadie podia contar porque no tenia nombre."""

    REINGRESO = "reingreso"
    """El ciclo se reabre. TRANSITORIO: un ciclo no puede quedarse aqui.

    Exige reclasificacion explicita a uno de los siete estados de tramite
    dentro del plazo definido en `servicios/maquina_ciclo.py`. Sin esa
    obligacion, REINGRESO seria un cajon de sastre donde los casos dificiles
    van a morir sin que nadie lo note.

    Recordatorio, porque es la confusion que costo tiempo: esto es el reingreso
    del CICLO ADMINISTRATIVO, no un reingreso del paciente al INSN."""

    # ── Lecturas ─────────────────────────────────────────────────────────────

    @property
    def etiqueta(self) -> str:
        """Como se nombra en pantalla, para personal de salud."""
        return _ETIQUETAS[self]

    @property
    def etiqueta_llana(self) -> str:
        """Como se le dice al paciente. Sin jerga administrativa.

        La vista del paciente no dice "EN_EVALUACION": dice "tu nuevo hospital
        esta revisando tu informacion". Es la misma verdad en un idioma que se
        entiende sin haber trabajado nunca en un hospital.
        """
        return _ETIQUETAS_LLANAS[self]

    @property
    def orden(self) -> int:
        """Posicion en la linea de tramite, para pintar la linea de tiempo.

        Los dos estados que no son tramite —perdida y reingreso— quedan fuera
        de la linea y devuelven -1: no van "mas adelante" ni "mas atras" que
        ningun otro, estan en otra dimension del proceso.
        """
        return _ORDEN.get(self, -1)

    @property
    def es_de_tramite(self) -> bool:
        """True para los siete estados de la linea de referencia."""
        return self.orden >= 0

    @property
    def es_final(self) -> bool:
        """True si no hay plazo que vigilar porque el ciclo termino bien.

        Se conserva el nombre que ya usaba `PoliticaPlazos`. Ojo: terminal no
        es inmutable — desde aqui todavia se puede caer a REINGRESO.
        """
        return self is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA

    @property
    def tiene_destino_asegurado(self) -> bool:
        """True si, al cumplir 18, este paciente NO es un fracaso del sistema.

        La definicion completa y la metrica agregada viven en
        `servicios/corte_etario.py`; esta propiedad esta aqui para que la
        pregunta se pueda hacer sobre un estado suelto.
        """
        return self in ESTADOS_CON_DESTINO_ASEGURADO

    def __str__(self) -> str:
        return self.etiqueta


_ETIQUETAS: dict[EstadoCiclo, str] = {
    EstadoCiclo.PREPARACION: "En preparación",
    EstadoCiclo.REFERENCIA_ENVIADA: "Referencia enviada",
    EstadoCiclo.RECEPCION_CONFIRMADA: "Recepción confirmada",
    EstadoCiclo.EN_EVALUACION: "En evaluación del receptor",
    EstadoCiclo.ACEPTADO_CON_SERVICIO: "Aceptado con servicio asignado",
    EstadoCiclo.CITA_PROGRAMADA: "Cita programada",
    EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA: "Primera atención confirmada",
    EstadoCiclo.PERDIDA_DE_SEGUIMIENTO: "Pérdida de seguimiento",
    EstadoCiclo.REINGRESO: "Reingreso al ciclo",
}

_ETIQUETAS_LLANAS: dict[EstadoCiclo, str] = {
    EstadoCiclo.PREPARACION: "Tu equipo del INSN está preparando tu traspaso",
    EstadoCiclo.REFERENCIA_ENVIADA: "Tus papeles ya salieron hacia tu nuevo hospital",
    EstadoCiclo.RECEPCION_CONFIRMADA: "Tu nuevo hospital confirmó que recibió tus papeles",
    EstadoCiclo.EN_EVALUACION: "Tu nuevo hospital está revisando tu información",
    EstadoCiclo.ACEPTADO_CON_SERVICIO: "Te aceptaron y ya tienes servicio asignado",
    EstadoCiclo.CITA_PROGRAMADA: "Ya tienes fecha de cita",
    EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA: "Ya te atendieron en tu nuevo hospital",
    EstadoCiclo.PERDIDA_DE_SEGUIMIENTO: "Perdimos el contacto contigo",
    EstadoCiclo.REINGRESO: "Retomamos tu caso",
}

# Posicion en la linea de tramite. Es lo que pinta la linea de tiempo de siete
# etapas de la vista del paciente.
_ORDEN: dict[EstadoCiclo, int] = {
    EstadoCiclo.PREPARACION: 0,
    EstadoCiclo.REFERENCIA_ENVIADA: 1,
    EstadoCiclo.RECEPCION_CONFIRMADA: 2,
    EstadoCiclo.EN_EVALUACION: 3,
    EstadoCiclo.ACEPTADO_CON_SERVICIO: 4,
    EstadoCiclo.CITA_PROGRAMADA: 5,
    EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA: 6,
}

ETAPAS_DE_TRAMITE: tuple[EstadoCiclo, ...] = tuple(
    sorted(_ORDEN, key=lambda e: _ORDEN[e])
)
"""Las siete etapas de la ruta de referencia, en orden."""


ESTADOS_CON_DESTINO_ASEGURADO: frozenset[EstadoCiclo] = frozenset(
    {
        EstadoCiclo.ACEPTADO_CON_SERVICIO,
        EstadoCiclo.CITA_PROGRAMADA,
        EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
    }
)
"""Los estados en los que cumplir 18 anios NO es un fracaso.

El corte esta en `ACEPTADO_CON_SERVICIO` y no en `CITA_PROGRAMADA` porque la
aceptacion con servicio asignado es el punto donde el paciente deja de poder
caerse del sistema: la cita es cuestion de agenda, y la mediana observada de
aceptacion a cita es de 80 a 85 dias (DIRIS Lima Norte, Rev Med Hered). Exigir
cita programada antes del cumpleanos marcaria como fracaso a pacientes cuyo
tramite va bien.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# El grafo de transiciones
#
# Vive aqui, junto al enum, y no en `servicios/maquina_ciclo.py`, porque tanto
# la entidad `CicloTransicion` (que valida cada avance) como el servicio de
# plazos lo necesitan, y `objetos_valor/` es la unica capa que las dos pueden
# importar sin invertir la direccion de las dependencias.
#
# `maquina_ciclo.py` tiene la otra mitad de la tabla —responsable y plazo por
# estado, cada uno con su fuente— y comprueba al importarse que las dos mitades
# cubran exactamente los mismos estados.
# ═══════════════════════════════════════════════════════════════════════════════

TRANSICIONES_PERMITIDAS: dict[EstadoCiclo, frozenset[EstadoCiclo]] = {
    # La linea de tramite avanza de uno en uno. Un salto significa que alguien
    # no registro un paso, y perder ese registro es perder justamente el dato
    # que el piloto viene a medir.
    #
    # Desde CUALQUIER estado de tramite se puede caer a PERDIDA_DE_SEGUIMIENTO:
    # un paciente se pierde cuando le da la gana, no cuando al proceso le
    # conviene.
    EstadoCiclo.PREPARACION: frozenset(
        {EstadoCiclo.REFERENCIA_ENVIADA, EstadoCiclo.PERDIDA_DE_SEGUIMIENTO}
    ),
    EstadoCiclo.REFERENCIA_ENVIADA: frozenset(
        {EstadoCiclo.RECEPCION_CONFIRMADA, EstadoCiclo.PERDIDA_DE_SEGUIMIENTO}
    ),
    EstadoCiclo.RECEPCION_CONFIRMADA: frozenset(
        {EstadoCiclo.EN_EVALUACION, EstadoCiclo.PERDIDA_DE_SEGUIMIENTO}
    ),
    EstadoCiclo.EN_EVALUACION: frozenset(
        {EstadoCiclo.ACEPTADO_CON_SERVICIO, EstadoCiclo.PERDIDA_DE_SEGUIMIENTO}
    ),
    EstadoCiclo.ACEPTADO_CON_SERVICIO: frozenset(
        {EstadoCiclo.CITA_PROGRAMADA, EstadoCiclo.PERDIDA_DE_SEGUIMIENTO}
    ),
    # Desde la cita hay tres desenlaces reales: se presento, no se presento
    # (reingreso con motivo NO_ASISTIO_A_PRIMERA_CITA) o se perdio el rastro.
    EstadoCiclo.CITA_PROGRAMADA: frozenset(
        {
            EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
            EstadoCiclo.REINGRESO,
            EstadoCiclo.PERDIDA_DE_SEGUIMIENTO,
        }
    ),
    # Terminal-exitoso pero no inmutable: "lo atendieron una vez y ahi se
    # acabo" es un desenlace frecuente y hay que poder nombrarlo.
    EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA: frozenset({EstadoCiclo.REINGRESO}),
    # De la perdida solo se sale reapareciendo. No se salta directo a un estado
    # de tramite: el reingreso queda registrado con su motivo, y esa cuenta es
    # un hallazgo del piloto.
    EstadoCiclo.PERDIDA_DE_SEGUIMIENTO: frozenset({EstadoCiclo.REINGRESO}),
    # REINGRESO es transitorio: sale hacia cualquiera de los siete estados de
    # tramite, segun donde se retome el caso. Lo que NO puede es quedarse.
    EstadoCiclo.REINGRESO: frozenset(ETAPAS_DE_TRAMITE),
}


def transiciones_desde(estado: EstadoCiclo) -> frozenset[EstadoCiclo]:
    """A donde se puede ir desde aqui. Vacio nunca: todo estado tiene salida.

    Que no haya callejones sin salida es lo que garantiza el test de grafo:
    desde cualquier estado se alcanza PRIMERA_ATENCION_CONFIRMADA.
    """
    return TRANSICIONES_PERMITIDAS[estado]


_sin_salida = [e.name for e in EstadoCiclo if not TRANSICIONES_PERMITIDAS.get(e)]
if _sin_salida:  # pragma: no cover - red de seguridad de desarrollo
    raise RuntimeError(
        "Estados sin transicion de salida: "
        + ", ".join(_sin_salida)
        + ". Un estado del que no se sale es un expediente enterrado."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Migracion de los seis estados originales
# ═══════════════════════════════════════════════════════════════════════════════

ESTADOS_LEGADO: dict[str, EstadoCiclo] = {
    # Nombres del enum original (PLAN_TECNICO §7).
    "PASAPORTE_EMITIDO": EstadoCiclo.PREPARACION,
    "REFERENCIA_REGISTRADA": EstadoCiclo.REFERENCIA_ENVIADA,
    # El estado viejo agrupaba acuse, evaluacion y aceptacion. Se migra al mas
    # avanzado de los tres porque es el que el dato viejo garantizaba: si estaba
    # en REFERENCIA_ACEPTADA, el receptor si habia aceptado. Migrarlo hacia
    # atras inventaria un retroceso que nunca ocurrio.
    "REFERENCIA_ACEPTADA": EstadoCiclo.ACEPTADO_CON_SERVICIO,
    "CITA_PROGRAMADA": EstadoCiclo.CITA_PROGRAMADA,
    "CITA_CUMPLIDA": EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
    # La contrarreferencia era el terminal burocratico. En el modelo nuevo el
    # hecho que importa es que el paciente fue atendido; la contrarreferencia
    # es la via por la que nos enteramos, y eso ya lo guarda
    # `FuenteConfirmacion` en el evento.
    "CONTRARREFERENCIA": EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
    # Los valores enteros con que el enum viejo se serializaba a SQLite.
    "1": EstadoCiclo.PREPARACION,
    "2": EstadoCiclo.REFERENCIA_ENVIADA,
    "3": EstadoCiclo.ACEPTADO_CON_SERVICIO,
    "4": EstadoCiclo.CITA_PROGRAMADA,
    "5": EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
    "6": EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
}
"""Todo valor viejo persistido tiene destino. Ninguno se borra.

Borrar filas para simplificar una migracion es perder justamente el historico
que el piloto viene a medir. Se traduce, no se descarta.
"""


def estado_desde_persistido(valor: str) -> EstadoCiclo:
    """Lee un estado guardado, sea del modelo nuevo o del viejo.

    Se prueba en este orden —valor nuevo, nombre nuevo, tabla de legado— para
    que un dato nuevo nunca pase por la tabla de migracion.
    """
    texto = str(valor).strip()
    for candidato in EstadoCiclo:
        if candidato.value == texto:
            return candidato
    if texto.upper() in EstadoCiclo.__members__:
        return EstadoCiclo[texto.upper()]
    if texto.upper() in ESTADOS_LEGADO:
        return ESTADOS_LEGADO[texto.upper()]
    if texto in ESTADOS_LEGADO:
        return ESTADOS_LEGADO[texto]
    raise ValueError(
        f"Estado de ciclo desconocido: {valor!r}. Ni del modelo actual ni de "
        "la tabla de legado. Antes de inventar una traduccion, revisar de que "
        "version de la base salio el dato."
    )
