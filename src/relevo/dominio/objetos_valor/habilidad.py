"""Las siete habilidades de Entrenate, una por leccion.

El INSN pidio, en su entregable 3, evaluar si el adolescente y su familia
conocen seis cosas concretas: **diagnostico, tratamiento, medicamentos, senales
de alerta, documentos y servicio de destino.** Esas seis estan cubiertas por las
habilidades 1, 2, 5 y 7; la 3 y la 4 salen del TRAQ y de las dos citas de
paciente que el propio INSN recogio.

POR QUE ESTO CIERRA EL DOLOR B3
Hasta ahora mediamos preparacion con el TRAQ y no interveniamos: el numero
entraba al indice como factor x5 y ahi se quedaba. Con Entrenate, el TRAQ deja
de ser un dato de reporte y pasa a ser el diagnostico que decide la
intervencion. Ese es el cierre del bucle medir -> intervenir -> volver a medir.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from enum import Enum


class Habilidad(Enum):
    """Las siete habilidades del recorrido. Una leccion por habilidad."""

    CONOZCO_MI_CONDICION = "conozco_mi_condicion"
    MANEJO_MI_TRATAMIENTO = "manejo_mi_tratamiento"
    HABLO_CON_MI_EQUIPO = "hablo_con_mi_equipo"
    NAVEGO_EL_SISTEMA = "navego_el_sistema"
    CUIDO_MIS_DOCUMENTOS = "cuido_mis_documentos"
    CONOZCO_MIS_DERECHOS = "conozco_mis_derechos"
    ENTIENDO_LA_TRANSICION = "entiendo_la_transicion"

    @property
    def numero(self) -> int:
        """1 a 7. Es el numero de la leccion asociada."""
        return _NUMEROS[self]

    @property
    def titulo(self) -> str:
        """Como se llama en pantalla, en primera persona.

        La primera persona no es un capricho de estilo: el sujeto de la
        transicion es el adolescente, y "Conozco mi condicion" le dice de quien
        es la tarea de una forma que "Conocimiento de la enfermedad" no.
        """
        return _TITULOS[self]

    @classmethod
    def por_numero(cls, numero: int) -> Habilidad | None:
        for habilidad, n in _NUMEROS.items():
            if n == numero:
                return habilidad
        return None

    def __str__(self) -> str:
        return self.titulo


_NUMEROS: dict[Habilidad, int] = {
    Habilidad.CONOZCO_MI_CONDICION: 1,
    Habilidad.MANEJO_MI_TRATAMIENTO: 2,
    Habilidad.HABLO_CON_MI_EQUIPO: 3,
    Habilidad.NAVEGO_EL_SISTEMA: 4,
    Habilidad.CUIDO_MIS_DOCUMENTOS: 5,
    Habilidad.CONOZCO_MIS_DERECHOS: 6,
    Habilidad.ENTIENDO_LA_TRANSICION: 7,
}

_TITULOS: dict[Habilidad, str] = {
    Habilidad.CONOZCO_MI_CONDICION: "Conozco mi condición",
    Habilidad.MANEJO_MI_TRATAMIENTO: "Manejo mi tratamiento",
    Habilidad.HABLO_CON_MI_EQUIPO: "Hablo con mi equipo de salud",
    Habilidad.NAVEGO_EL_SISTEMA: "Navego el sistema de salud",
    Habilidad.CUIDO_MIS_DOCUMENTOS: "Cuido mis documentos",
    Habilidad.CONOZCO_MIS_DERECHOS: "Conozco mis derechos",
    Habilidad.ENTIENDO_LA_TRANSICION: "Entiendo la transición",
}


class EstadoHabilidad(Enum):
    """Como va el adolescente en una habilidad.

    Cuatro estados y no un porcentaje. Un porcentaje invita a compararse con
    otros y a leer el recorrido como una nota; estos cuatro describen que hacer
    a continuacion, que es lo unico que le sirve a quien esta aprendiendo.
    """

    POR_INICIAR = "por_iniciar"
    EN_PRACTICA = "en_practica"
    LOGRADA = "lograda"
    NECESITA_REFUERZO = "necesita_refuerzo"
    """Se logro y despues se vio que no. No es un retroceso ni un castigo: en
    una condicion cronica de anios, olvidarse de algo es lo normal."""

    @property
    def etiqueta(self) -> str:
        return {
            EstadoHabilidad.POR_INICIAR: "Por iniciar",
            EstadoHabilidad.EN_PRACTICA: "En práctica",
            EstadoHabilidad.LOGRADA: "Lograda",
            EstadoHabilidad.NECESITA_REFUERZO: "Necesita refuerzo",
        }[self]

    @property
    def pide_trabajo(self) -> bool:
        """True si esta habilidad deberia aparecer en "lo siguiente que hacer"."""
        return self is not EstadoHabilidad.LOGRADA

    def __str__(self) -> str:
        return self.etiqueta


class EstadoContenido(Enum):
    """Si el contenido de una leccion se puede presentar como bueno.

    Existe porque escribir contenido clinico sin la firma de un medico del INSN
    violaria la regla 4 del proyecto. Un esqueleto honesto y sellado es mas
    fuerte ante un jurado clinico que siete lecciones que nadie del equipo
    puede defender.
    """

    COMPLETO = "completo"
    ESQUELETO_PENDIENTE_VALIDACION = "esqueleto_pendiente_validacion"

    @property
    def sello(self) -> str | None:
        """El texto que se muestra encima de la leccion. None si esta completa."""
        if self is EstadoContenido.ESQUELETO_PENDIENTE_VALIDACION:
            return "Contenido pendiente de validación clínica del INSN"
        return None

    @property
    def es_presentable(self) -> bool:
        return self is EstadoContenido.COMPLETO
