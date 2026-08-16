"""Control de plazos del ciclo de derivacion.

PLAN_TECNICO §7. La entidad `CicloTransicion` sabe avanzar; este servicio sabe
CUANDO un ciclo se esta quedando atras.

Los plazos estan calibrados con datos peruanos reales — estudio DIRIS Lima
Norte, Revista Medica Herediana, 19 951 referencias — y no con intuicion. El
numero que mas importa es el de 120 dias entre aceptacion y cita: la mediana
observada es de 80 a 85 dias, asi que un umbral de 90 dispararia alerta en la
mitad de los casos que van perfectamente bien.

Eso no es un detalle de calibracion. Un sistema que avisa cuando no pasa nada
deja de leerse, y un sistema que no se lee no sirve para nada.

Como en el resto del dominio, los plazos se reciben ya cargados y sin valor por
defecto: `config/plazos_ciclo.yaml` lo lee un adaptador. Los valores
provisionales viven en `tests/dominio/conftest.py`, que es donde corresponde a
lo que solo sirve para probar.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

from relevo.dominio.entidades.ciclo_transicion import CicloTransicion, EstadoCiclo
from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.dominio.objetos_valor.responsable import Responsable, responsable_de


@dataclass(frozen=True, slots=True)
class EntradaTabla:
    """Una fila de la tabla del ciclo: quien responde, en cuanto tiempo y por que.

    `fuente` no es documentacion decorativa. La regla 7 del proyecto exige que
    cada umbral diga de donde salio, y `provisional` marca sin ambiguedad los
    que todavia no tienen respaldo: un plazo provisional presentado como
    calibrado es como se pierde la credibilidad delante de un jurado clinico.
    """

    responsable: Responsable
    plazo_dias: int | None
    fuente: str
    provisional: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# LA TABLA DEL CICLO — responsable y plazo por estado
#
# El grafo de transiciones vive en `objetos_valor/estado_ciclo.py`, que es la
# capa que tanto la entidad como este servicio pueden importar. Aqui esta la
# otra mitad: a quien le toca y cuanto tiempo tiene. Las dos mitades se
# comprueban entre si al final de este bloque.
# ═══════════════════════════════════════════════════════════════════════════════

TABLA_CICLO: dict[EstadoCiclo, EntradaTabla] = {
    EstadoCiclo.PREPARACION: EntradaTabla(
        responsable=Responsable.EQUIPO_INSN,
        plazo_dias=30,
        # TODO: confirmar con mentor — cuanto tarda de verdad el equipo en
        # armar un expediente completo. 30 dias es lo que parece razonable, no
        # lo que nadie midio.
        fuente="Provisional. TODO: confirmar con mentor",
    ),
    EstadoCiclo.REFERENCIA_ENVIADA: EntradaTabla(
        responsable=Responsable.HOSPITAL_RECEPTOR,
        plazo_dias=7,
        fuente=(
            "Acuse de recepcion. Provisional, alineado al espiritu de "
            "NT 018-MINSA/DGSP-V.01"
        ),
    ),
    EstadoCiclo.RECEPCION_CONFIRMADA: EntradaTabla(
        responsable=Responsable.HOSPITAL_RECEPTOR,
        plazo_dias=15,
        fuente="Provisional",
    ),
    EstadoCiclo.EN_EVALUACION: EntradaTabla(
        responsable=Responsable.HOSPITAL_RECEPTOR,
        plazo_dias=30,
        fuente="Provisional",
    ),
    EstadoCiclo.ACEPTADO_CON_SERVICIO: EntradaTabla(
        responsable=Responsable.HOSPITAL_RECEPTOR,
        plazo_dias=120,
        # El unico plazo de la tabla que NO es provisional, y el que mas
        # importa: un umbral de 90 dias dispararia alerta en la mitad de los
        # casos que van perfectamente bien.
        fuente=(
            "Calibrado sobre mediana 80-85 d aceptacion->cita "
            "(DIRIS Lima Norte, Rev Med Hered, 19 951 referencias)"
        ),
        provisional=False,
    ),
    EstadoCiclo.CITA_PROGRAMADA: EntradaTabla(
        responsable=Responsable.PACIENTE,
        plazo_dias=7,
        # Contado desde la FECHA DE LA CITA, no desde su programacion. Ver
        # `MaquinaCiclo._fecha_referencia`.
        fuente="Fecha de cita + 7 d. El receptor confirma asistencia",
    ),
    EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA: EntradaTabla(
        responsable=Responsable.NADIE,
        plazo_dias=None,
        fuente="Terminal-exitoso: no hay plazo que vigilar",
        provisional=False,
    ),
    EstadoCiclo.PERDIDA_DE_SEGUIMIENTO: EntradaTabla(
        responsable=Responsable.EQUIPO_INSN,
        plazo_dias=15,
        fuente="Provisional",
    ),
    EstadoCiclo.REINGRESO: EntradaTabla(
        responsable=Responsable.EQUIPO_INSN,
        plazo_dias=7,
        # REINGRESO es transitorio: el plazo no mide un tramite, mide cuanto
        # puede tardar el equipo en decidir a que estado vuelve el caso.
        fuente="7 d para reclasificar. Provisional",
    ),
}


# Las dos mitades de la tabla tienen que hablar del mismo ciclo. Se comprueba
# al importar y no en un test: si alguien anade un estado y se olvida de una de
# las dos mitades, el fallo tiene que aparecer al arrancar, no al recordar.
_desalineados = [
    estado.name
    for estado in EstadoCiclo
    if estado not in TABLA_CICLO or responsable_de(estado) is not TABLA_CICLO[estado].responsable
]
if _desalineados:  # pragma: no cover - red de seguridad de desarrollo
    raise RuntimeError(
        "La tabla del ciclo y la tabla de responsables no coinciden en: "
        + ", ".join(_desalineados)
    )


def plazo_de_referencia(estado: EstadoCiclo) -> int | None:
    """El plazo de la tabla, para quien no cargo la politica desde el YAML.

    NO es el valor que usa la produccion: eso lo carga `PoliticaPlazos` desde
    `config/plazos_ciclo.yaml`. Esto es la tabla de referencia documentada,
    util para pintar la interfaz y para explicar de donde sale cada numero.
    """
    return TABLA_CICLO[estado].plazo_dias


class SituacionPlazo(Enum):
    """En que punto del plazo esta un ciclo."""

    EN_PLAZO = "en_plazo"
    POR_VENCER = "por_vencer"
    """Entro en la franja de preaviso. Aqui todavia se puede hacer algo."""

    VENCIDO = "vencido"
    CERRADO = "cerrado"
    """Llego a contrarreferencia: no hay plazo que vigilar."""

    @property
    def requiere_accion(self) -> bool:
        return self in (SituacionPlazo.POR_VENCER, SituacionPlazo.VENCIDO)


@dataclass(frozen=True, slots=True)
class PoliticaPlazos:
    """Los plazos del ciclo, en dias, por estado de origen.

    `fraccion_preaviso` y `minimo_dias_preaviso` implementan la regla de
    `plazos_ciclo.yaml`: un plazo vencido ya es tarde, asi que se avisa antes.
    Con 120 dias el preaviso cae al dia 90 — justo en la mediana observada,
    que es donde todavia se puede intervenir.
    """

    dias_por_estado: Mapping[EstadoCiclo, int]
    fraccion_preaviso: float = 0.25
    minimo_dias_preaviso: int = 3

    def __post_init__(self) -> None:
        faltantes = [
            estado.name
            for estado in EstadoCiclo
            if not estado.es_final and estado not in self.dias_por_estado
        ]
        if faltantes:
            raise ConfiguracionIncompleta(
                f"Faltan plazos para: {', '.join(faltantes)}. "
                "Un plazo inventado dispara alertas falsas: se carga o se detiene."
            )
        if not 0.0 < self.fraccion_preaviso < 1.0:
            raise ConfiguracionIncompleta(
                f"fraccion_preaviso debe estar en (0,1): {self.fraccion_preaviso}"
            )

    def plazo_de(self, estado: EstadoCiclo) -> int | None:
        """Dias permitidos en ese estado. None si el ciclo ya termino."""
        return self.dias_por_estado.get(estado)

    def dias_de_preaviso(self, estado: EstadoCiclo) -> int:
        """Cuantos dias antes del vencimiento se avisa.

        Nunca menos de `minimo_dias_preaviso`: con un plazo de 7 dias, el 25 %
        serian 1.75 dias, y avisar dia y medio antes no le da tiempo a nadie.
        """
        plazo = self.plazo_de(estado)
        if plazo is None:
            return 0
        return max(self.minimo_dias_preaviso, int(plazo * self.fraccion_preaviso))


@dataclass(frozen=True, slots=True)
class EvaluacionPlazo:
    """El diagnostico de un ciclo en una fecha dada."""

    paciente_id: str
    estado: EstadoCiclo
    situacion: SituacionPlazo
    dias_transcurridos: int
    plazo_dias: int | None
    fecha_limite: date | None

    @property
    def responsable(self) -> Responsable:
        """A quien le toca destrabar esto.

        Va en la evaluacion y no solo en la entidad porque es lo que hace util
        al aviso: "PAC-0042 vencido" obliga a que alguien abra el expediente
        para saber si le toca; "PAC-0042 vencido — turno del hospital receptor"
        se resuelve leyendo el correo. Es el entregable 1 de la rubrica del
        INSN y su Insight 5, los dos a la vez.
        """
        return responsable_de(self.estado)

    @property
    def dias_restantes(self) -> int | None:
        if self.plazo_dias is None:
            return None
        return self.plazo_dias - self.dias_transcurridos

    @property
    def requiere_accion(self) -> bool:
        return self.situacion.requiere_accion

    def mensaje(self) -> str:
        """Una linea para el correo del equipo. Sin datos clinicos: esto puede
        terminar en una pantalla de bloqueo."""
        if self.situacion is SituacionPlazo.CERRADO:
            return f"{self.paciente_id}: ciclo cerrado"
        restantes = self.dias_restantes
        turno = f" — turno de {self.responsable.etiqueta}"
        if self.situacion is SituacionPlazo.VENCIDO:
            return (
                f"{self.paciente_id}: {self.estado.etiqueta} vencido hace "
                f"{-(restantes or 0)} días{turno}"
            )
        if self.situacion is SituacionPlazo.POR_VENCER:
            return (
                f"{self.paciente_id}: {self.estado.etiqueta} vence en "
                f"{restantes} días{turno}"
            )
        return f"{self.paciente_id}: {self.estado.etiqueta} en plazo"

    def __str__(self) -> str:
        return self.mensaje()


@dataclass(frozen=True, slots=True)
class MaquinaCiclo:
    """Evalua plazos. No modifica ciclos: solo dice como estan.

    Separado de la entidad a proposito. Avanzar un ciclo es un hecho que
    alguien registra; evaluar plazos es una lectura que se recalcula cada
    noche. Mezclarlos haria que consultar el estado tuviera efectos.

    `politica` no tiene valor por defecto: un plazo inventado dispara alertas
    falsas, y un equipo que recibe alertas falsas deja de leer los correos. Si
    nadie cargo `plazos_ciclo.yaml`, esto falla en vez de suponer.
    """

    politica: PoliticaPlazos

    def evaluar(self, ciclo: CicloTransicion, hoy: date) -> EvaluacionPlazo:
        estado = ciclo.estado
        plazo = self.politica.plazo_de(estado)
        transcurridos = ciclo.dias_en_estado_actual(hoy)

        if plazo is None:
            return EvaluacionPlazo(
                paciente_id=ciclo.paciente_id,
                estado=estado,
                situacion=SituacionPlazo.CERRADO,
                dias_transcurridos=transcurridos,
                plazo_dias=None,
                fecha_limite=None,
            )

        limite = self._fecha_referencia(ciclo) + timedelta(days=plazo)
        restantes = plazo - transcurridos
        preaviso = self.politica.dias_de_preaviso(estado)

        if restantes < 0:
            situacion = SituacionPlazo.VENCIDO
        elif restantes <= preaviso:
            situacion = SituacionPlazo.POR_VENCER
        else:
            situacion = SituacionPlazo.EN_PLAZO

        return EvaluacionPlazo(
            paciente_id=ciclo.paciente_id,
            estado=estado,
            situacion=situacion,
            dias_transcurridos=transcurridos,
            plazo_dias=plazo,
            fecha_limite=limite,
        )

    @staticmethod
    def _fecha_referencia(ciclo: CicloTransicion) -> date:
        """Desde cuando se cuenta el plazo del estado actual.

        En CITA_PROGRAMADA se cuenta desde la fecha de la cita: una cita
        programada a tres meses no esta vencida a los treinta dias de haberse
        programado.
        """
        if ciclo.estado is EstadoCiclo.CITA_PROGRAMADA and ciclo.fecha_cita is not None:
            return ciclo.fecha_cita
        return ciclo.fecha_estado_actual

    def evaluar_todos(
        self, ciclos: Iterable[CicloTransicion], hoy: date
    ) -> list[EvaluacionPlazo]:
        """Ordenadas por urgencia: primero lo vencido, luego lo por vencer.

        Dentro de cada grupo, lo que lleva mas tiempo parado va arriba.
        """
        evaluaciones = [self.evaluar(c, hoy) for c in ciclos]
        prioridad = {
            SituacionPlazo.VENCIDO: 0,
            SituacionPlazo.POR_VENCER: 1,
            SituacionPlazo.EN_PLAZO: 2,
            SituacionPlazo.CERRADO: 3,
        }
        return sorted(
            evaluaciones,
            key=lambda e: (prioridad[e.situacion], -e.dias_transcurridos),
        )

    def requieren_accion(
        self, ciclos: Iterable[CicloTransicion], hoy: date
    ) -> list[EvaluacionPlazo]:
        """Solo lo que hay que atender. Es lo que va al correo semanal.

        Si sale vacia, no se manda correo: un aviso que llega siempre deja de
        leerse (PLAN_TECNICO §10).
        """
        return [e for e in self.evaluar_todos(ciclos, hoy) if e.requiere_accion]
