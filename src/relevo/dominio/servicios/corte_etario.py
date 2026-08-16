"""El corte etario: la unica metrica de fracaso que importa de verdad.

═══════════════════════════════════════════════════════════════════════════════
QUE ES FRACASO Y QUE NO
═══════════════════════════════════════════════════════════════════════════════

**Cumplir 18 anios NO es el fracaso del sistema.** La primera cita en el
hospital de adultos ocurre, por definicion, despues de los 18. El corte etario
del INSN impide la atencion pediatrica, no la continuidad del tramite.

**El fracaso es cumplir 18 SIN DESTINO ASEGURADO**, es decir con el ciclo en un
estado anterior a `ACEPTADO_CON_SERVICIO`. Ese paciente se queda sin ningun
servicio: no es una demora, es una interrupcion total, en fecha exacta y sin
red de seguridad.

Esa cifra va arriba de todo en el radar. Cualquier otra metrica del sistema
—cuantos Pasaportes se emitieron, cuantas referencias se enviaron— mide
actividad. Esta mide el dano que el proyecto existe para evitar.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.dominio.objetos_valor.estado_ciclo import (
    ESTADOS_CON_DESTINO_ASEGURADO,
    EstadoCiclo,
)
from relevo.dominio.objetos_valor.ventana_transicion import cumpleanos_18, edad_en

# Horizonte de la alerta temprana. Noventa dias es la ultima ventana en la que
# una referencia iniciada de cero todavia puede llegar a ACEPTADO_CON_SERVICIO:
# 7 dias de acuse + 15 de recepcion + 30 de evaluacion suman 52 en el mejor
# caso, y el margen restante absorbe la peticion de informacion complementaria,
# que ocurre en el 13.6 % de las referencias (DIRIS Lima Norte, Rev Med Hered).
#
# Pasados esos 90 dias sin destino asegurado, el sistema deja de avisar
# "conviene apurarse" y empieza a avisar "esto no va a llegar".
DIAS_HORIZONTE_RIESGO = 90


@dataclass(frozen=True, slots=True)
class CumplioDieciochoSinDestino:
    """Evento de dominio. El unico fracaso que el sistema existe para evitar.

    Se guarda `dias_en_ese_estado` y no solo el estado porque las dos lecturas
    dicen cosas distintas: un paciente que cumplio 18 en PREPARACION habiendo
    entrado ayer es un caso detectado tarde; uno que llevaba 200 dias ahi es un
    expediente que el sistema vio y nadie movio. La segunda es la unica de las
    dos que Relevo puede corregir, y por eso hay que poder distinguirlas.
    """

    id_paciente: str
    fecha_cumpleanios: date
    estado_al_cumplir: EstadoCiclo
    dias_en_ese_estado: int

    @property
    def descripcion(self) -> str:
        return (
            f"{self.id_paciente} cumplio 18 el "
            f"{self.fecha_cumpleanios.isoformat()} en estado "
            f"'{self.estado_al_cumplir.etiqueta}' tras "
            f"{self.dias_en_ese_estado} dias sin movimiento"
        )

    def __str__(self) -> str:
        return self.descripcion


@dataclass(frozen=True, slots=True)
class MetricaCorteEtario:
    """La cifra que va arriba de todo en el radar.

    Tres numeros y no uno: el primero es la cola de trabajo de esta semana, el
    segundo es el dano ya hecho, el tercero es el denominador sin el cual los
    otros dos no significan nada. Un "12" suelto no dice si el sistema va bien
    o mal.
    """

    en_riesgo_90_dias: int
    """Cumplen 18 en menos de 90 dias y todavia no tienen destino asegurado.
    Es la lista sobre la que se puede actuar HOY."""

    ya_cumplieron_sin_destino: int
    """Ya cumplieron 18 sin destino asegurado. El dano consumado. No se
    esconde: se cuenta, porque es la linea basal contra la que el piloto va a
    medir si el sistema sirvio para algo."""

    total_cohorte: int

    @property
    def proporcion_sin_destino(self) -> float:
        """Fracasos consumados sobre el total. 0.0 si no hay cohorte."""
        if self.total_cohorte == 0:
            return 0.0
        return self.ya_cumplieron_sin_destino / self.total_cohorte

    @property
    def hay_algo_que_hacer(self) -> bool:
        return self.en_riesgo_90_dias > 0 or self.ya_cumplieron_sin_destino > 0

    def titular(self) -> str:
        """Una linea para la cabecera del radar."""
        return (
            f"{self.en_riesgo_90_dias} cumplen 18 en menos de "
            f"{DIAS_HORIZONTE_RIESGO} dias sin destino asegurado · "
            f"{self.ya_cumplieron_sin_destino} ya cumplieron sin destino "
            f"(de {self.total_cohorte})"
        )

    def __str__(self) -> str:
        return self.titular()


def _fecha_nacimiento_de(ciclo: object) -> date:
    """La fecha de nacimiento del paciente del ciclo, o se detiene.

    No se imputa nada. Todo este modulo depende de una fecha exacta: sin ella
    no hay corte que evaluar, y suponer una edad para poder devolver un numero
    es como se fabrican metricas que mienten.
    """
    fecha = getattr(ciclo, "fecha_nacimiento", None)
    if not isinstance(fecha, date):
        raise ConfiguracionIncompleta(
            f"El ciclo de {getattr(ciclo, 'paciente_id', '?')} no lleva fecha "
            "de nacimiento y el corte etario no se puede evaluar sin ella. "
            "No se imputa una edad: una metrica de fracaso calculada sobre una "
            "edad supuesta es peor que no tener metrica."
        )
    return fecha


def dias_para_corte(fecha_nacimiento: date, hoy: date) -> int:
    """Dias que faltan para el cumpleanos 18. Negativo si ya paso.

    Envoltura fina sobre `cumpleanos_18` para que el modulo se lea solo. El
    caso del 29 de febrero lo resuelve `ventana_transicion.py`.
    """
    return (cumpleanos_18(fecha_nacimiento) - hoy).days


def tiene_destino_asegurado(ciclo: object) -> bool:
    """True si el ciclo alcanzo ACEPTADO_CON_SERVICIO o mas alla."""
    estado = getattr(ciclo, "estado", None)
    return estado in ESTADOS_CON_DESTINO_ASEGURADO


def evaluar_corte_etario(
    ciclo: object, hoy: date
) -> CumplioDieciochoSinDestino | None:
    """El evento de fracaso, si este ciclo ya lo consumo. None si no.

    Devuelve None en los dos casos buenos —todavia no cumplio 18, o cumplio
    pero con destino asegurado— y el evento solo en el malo. Un `None` que
    significa "aqui no hay nada que lamentar" hace que el codigo que lo consume
    se lea como lo que es: una busqueda de danos.
    """
    fecha_nacimiento = _fecha_nacimiento_de(ciclo)
    cumpleanos = cumpleanos_18(fecha_nacimiento)

    if edad_en(fecha_nacimiento, hoy) < 18:
        return None
    if tiene_destino_asegurado(ciclo):
        return None

    estado = getattr(ciclo, "estado")
    fecha_estado: date = getattr(ciclo, "fecha_estado_actual", cumpleanos)
    # Dias parado en ese estado AL CUMPLIR 18, no a dia de hoy: lo que se mide
    # es la situacion en el momento del corte. Si el ciclo entro al estado
    # despues del cumpleanos, el conteo es cero y no un numero negativo.
    dias = max(0, (cumpleanos - fecha_estado).days)

    return CumplioDieciochoSinDestino(
        id_paciente=str(getattr(ciclo, "paciente_id", "")),
        fecha_cumpleanios=cumpleanos,
        estado_al_cumplir=estado,
        dias_en_ese_estado=dias,
    )


def en_riesgo_de_corte(ciclo: object, hoy: date) -> bool:
    """True si cumple 18 dentro del horizonte y aun no tiene destino.

    No incluye a los que ya cumplieron: eso ya no es riesgo, es dano, y se
    cuenta aparte. Mezclarlos daria un numero que baja cuando la situacion
    empeora.
    """
    if tiene_destino_asegurado(ciclo):
        return False
    restantes = dias_para_corte(_fecha_nacimiento_de(ciclo), hoy)
    return 0 <= restantes < DIAS_HORIZONTE_RIESGO


def medir_corte_etario(ciclos: Iterable[object], hoy: date) -> MetricaCorteEtario:
    """La metrica agregada de toda la cohorte. Va arriba de todo en el radar."""
    en_riesgo = 0
    consumados = 0
    total = 0

    for ciclo in ciclos:
        total += 1
        if en_riesgo_de_corte(ciclo, hoy):
            en_riesgo += 1
        if evaluar_corte_etario(ciclo, hoy) is not None:
            consumados += 1

    return MetricaCorteEtario(
        en_riesgo_90_dias=en_riesgo,
        ya_cumplieron_sin_destino=consumados,
        total_cohorte=total,
    )


def fracasos(ciclos: Iterable[object], hoy: date) -> list[CumplioDieciochoSinDestino]:
    """La lista nominal de fracasos consumados, del mas reciente al mas viejo.

    Existe aparte de la metrica porque un numero agregado no permite hacer
    nada: para llamar a alguien hace falta saber a quien.
    """
    eventos = [e for c in ciclos if (e := evaluar_corte_etario(c, hoy)) is not None]
    return sorted(eventos, key=lambda e: e.fecha_cumpleanios, reverse=True)
