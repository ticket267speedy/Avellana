"""Que leccion le toca ahora a este adolescente.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTA FUNCION ES LA FRASE DEL PITCH
═══════════════════════════════════════════════════════════════════════════════

Hasta ahora el TRAQ era un numero de reporte: entraba al indice como factor x5,
sumaba puntos de urgencia, y ahi se acababa. Mediamos preparacion y no
interveniamos — ese es el dolor B3, y estaba en un 10 %.

Con esto el TRAQ deja de ser un dato y pasa a ser el diagnostico que decide la
intervencion:

    medir (TRAQ) -> intervenir (leccion) -> volver a medir

FUNCION PURA, SIN MODELO DE LENGUAJE. No hace falta y seria peor: la
recomendacion tiene que ser explicable a un medico del INSN en una frase, y
"el modelo lo sugirio" no es una frase. Ademas la regla 3 del proyecto exige
que todo corra sin internet, y esto tiene que funcionar con el wifi caido.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from collections.abc import Mapping

from relevo.dominio.entidades.diagnostico import ResultadoTRAQ
from relevo.dominio.entidades.leccion import Leccion
from relevo.dominio.entidades.progreso_aprendizaje import ProgresoAprendizaje
from relevo.dominio.objetos_valor.franja_etaria import FranjaEtaria
from relevo.dominio.objetos_valor.habilidad import EstadoHabilidad, Habilidad

# Por debajo de este puntaje TRAQ, la prioridad se invierte: en vez de seguir
# el orden natural del recorrido, se empieza por lo mas basico que este sin
# hacer. Un adolescente con TRAQ 2 no necesita aprender a navegar el sistema:
# necesita saber que tiene y que toma.
#
# El 3.0 es el punto medio del rango [1.0, 5.0] del instrumento.
# TODO: confirmar con mentor — si el equipo del INSN usa algun punto de corte
# propio para el TRAQ. Provisional: el punto medio del rango.
TRAQ_BAJO = 3.0

# El orden en que se recomiendan las habilidades cuando el TRAQ es bajo o no
# existe. No es el orden de los numeros de leccion: es de lo mas concreto a lo
# mas abstracto. Saber que enfermedad tengo antes que saber que derechos me
# asisten no es una opinion pedagogica, es la secuencia con la que un
# adolescente puede sostener una conversacion en una consulta.
_ORDEN_POR_FUNDAMENTO: tuple[Habilidad, ...] = (
    Habilidad.CONOZCO_MI_CONDICION,
    Habilidad.MANEJO_MI_TRATAMIENTO,
    Habilidad.CUIDO_MIS_DOCUMENTOS,
    Habilidad.HABLO_CON_MI_EQUIPO,
    Habilidad.NAVEGO_EL_SISTEMA,
    Habilidad.ENTIENDO_LA_TRANSICION,
    Habilidad.CONOZCO_MIS_DERECHOS,
)

# Lo que cada franja pide primero. En EXPLORA no se pide autonomia: se pide
# curiosidad. En YA, con el corte encima, lo urgente es lo que cambia el dia
# del cumpleanos.
_PRIORIDAD_POR_FRANJA: dict[FranjaEtaria, tuple[Habilidad, ...]] = {
    FranjaEtaria.EXPLORA: (
        Habilidad.CONOZCO_MI_CONDICION,
        Habilidad.MANEJO_MI_TRATAMIENTO,
    ),
    FranjaEtaria.PREPARADOS: (
        Habilidad.MANEJO_MI_TRATAMIENTO,
        Habilidad.HABLO_CON_MI_EQUIPO,
        Habilidad.CONOZCO_MI_CONDICION,
    ),
    FranjaEtaria.LISTOS: (
        Habilidad.NAVEGO_EL_SISTEMA,
        Habilidad.CUIDO_MIS_DOCUMENTOS,
        Habilidad.HABLO_CON_MI_EQUIPO,
    ),
    FranjaEtaria.YA: (
        # A los 17 lo urgente es lo que cambia el dia del cumpleanos: quien
        # firma sus consentimientos, quien puede pedir sus resultados, que pasa
        # con su seguro. Es tambien la unica leccion COMPLETA que tenemos.
        Habilidad.CONOZCO_MIS_DERECHOS,
        Habilidad.ENTIENDO_LA_TRANSICION,
        Habilidad.CUIDO_MIS_DOCUMENTOS,
    ),
}


def _candidatas(progreso: ProgresoAprendizaje) -> tuple[Habilidad, ...]:
    """Las que piden trabajo, con el refuerzo primero.

    `NECESITA_REFUERZO` va delante de `POR_INICIAR` porque una habilidad que se
    perdio es una que el adolescente ya sabe que le importa: recuperarla cuesta
    menos y le devuelve la sensacion de que el recorrido sirve.
    """
    refuerzo = [
        h
        for h in Habilidad
        if progreso.estado_de(h) is EstadoHabilidad.NECESITA_REFUERZO
    ]
    resto = [
        h
        for h in Habilidad
        if progreso.estado_de(h).pide_trabajo
        and progreso.estado_de(h) is not EstadoHabilidad.NECESITA_REFUERZO
    ]
    return tuple(refuerzo + resto)


def recomendar_habilidad(
    traq: ResultadoTRAQ | None,
    edad_anios: int,
    progreso: ProgresoAprendizaje,
) -> Habilidad | None:
    """La siguiente habilidad a trabajar. None si estan las siete logradas.

    Tres criterios, en este orden:

    1. Lo que necesita refuerzo va primero.
    2. Con TRAQ bajo o ausente, se sigue el orden de fundamento: primero lo
       concreto. Sin TRAQ se asume lo mismo que hace el indice — imputar y
       tratar el dato como faltante — porque no medir preparacion no es senal
       de estar preparado.
    3. Con TRAQ suficiente, manda la franja etaria: lo que toca a esta edad.
    """
    candidatas = _candidatas(progreso)
    if not candidatas:
        return None

    if candidatas[0] is not None and (
        progreso.estado_de(candidatas[0]) is EstadoHabilidad.NECESITA_REFUERZO
    ):
        return candidatas[0]

    pendientes = set(candidatas)
    traq_bajo = traq is None or traq.puntaje < TRAQ_BAJO

    if not traq_bajo:
        franja = FranjaEtaria.para_edad(edad_anios)
        if franja is not None:
            for habilidad in _PRIORIDAD_POR_FRANJA[franja]:
                if habilidad in pendientes:
                    return habilidad

    for habilidad in _ORDEN_POR_FUNDAMENTO:
        if habilidad in pendientes:
            return habilidad

    return candidatas[0]


def recomendar_leccion(
    traq: ResultadoTRAQ | None,
    edad_anios: int,
    progreso: ProgresoAprendizaje,
    catalogo: Mapping[Habilidad, Leccion] | None = None,
) -> Leccion | None:
    """La leccion que le toca ahora. None si no queda nada que trabajar.

    `catalogo` se inyecta: el contenido de las lecciones lo carga un adaptador
    desde `config/`, y el dominio no toca el disco. Sin catalogo devuelve None
    en vez de fabricar una leccion vacia — una recomendacion sin contenido
    detras es peor que ninguna.
    """
    if not catalogo:
        return None
    habilidad = recomendar_habilidad(traq, edad_anios, progreso)
    if habilidad is None:
        return None
    return catalogo.get(habilidad)


def motivo_de_la_recomendacion(
    traq: ResultadoTRAQ | None, habilidad: Habilidad | None
) -> str:
    """Por que se recomienda esa y no otra, en una linea para el adolescente.

    Ninguna recomendacion sale sin motivo. Un sistema que dice "haz esto" sin
    decir por que se ignora a la segunda vez.
    """
    if habilidad is None:
        return "Ya trabajaste las siete habilidades. Repasa la que quieras."
    if traq is None:
        return (
            f"Todavia no respondiste el cuestionario de preparacion, asi que "
            f"empezamos por lo basico: {habilidad.titulo.lower()}."
        )
    if traq.puntaje < TRAQ_BAJO:
        return (
            f"Tu cuestionario de preparacion salio en {traq.puntaje:.1f} sobre "
            f"5, asi que conviene empezar por lo mas concreto: "
            f"{habilidad.titulo.lower()}."
        )
    return f"Por tu edad, lo siguiente que toca es: {habilidad.titulo.lower()}."
