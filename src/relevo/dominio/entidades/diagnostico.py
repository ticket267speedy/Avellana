"""Diagnostico, medicamento, dispositivo, cirugia y contacto.

Todo lo que cuelga de un paciente y que el motor de reglas necesita leer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from relevo.dominio.objetos_valor.codigo_cie10 import CodigoCIE10
from relevo.dominio.objetos_valor.telefono import Telefono


class CategoriaCCC(Enum):
    """Las 10 categorias de Complex Chronic Conditions v2, mas 'otra'.

    Feudtner et al., BMC Pediatrics 2014;14:199. Los nombres son los del
    articulo, traducidos; los pesos de severidad viven en
    `config/reglas_transicion.yaml`, no aqui: son politica clinica, no dominio.
    """

    NEUROMUSCULAR = "neuromuscular"
    CARDIOVASCULAR = "cardiovascular"
    RESPIRATORIA = "respiratoria"
    RENAL = "renal"
    GASTROINTESTINAL = "gastrointestinal"
    HEMATOLOGICA_INMUNOLOGICA = "hematologica_inmunologica"
    METABOLICA = "metabolica"
    CONGENITA_GENETICA = "congenita_genetica"
    MALIGNIDAD = "malignidad"
    NEONATAL = "neonatal"
    DEPENDENCIA_TECNOLOGICA = "dependencia_tecnologica"
    TRASPLANTE = "trasplante"
    OTRA = "otra"


class TipoSeguro(Enum):
    """Regimen de aseguramiento. Determina el factor x8.

    VERIFICADO — EsSalud: se deja de ser derechohabiente a los 18 salvo
    incapacidad total y permanente acreditada ante la Comision Medica
    Evaluadora (Ley 26790). Un cronico que no califica como discapacitado
    total pierde la cobertura el dia que cumple 18.

    NO VERIFICADO — SIS: no sabemos que pasa al cumplir 18.
    TODO: verificar con Servicio Social INSN.
    """

    SIS = "SIS"
    ESSALUD = "ESSALUD"
    PRIVADO = "PRIVADO"
    NINGUNO = "NINGUNO"


@dataclass(frozen=True, slots=True)
class Diagnostico:
    """Un diagnostico codificado."""

    codigo: CodigoCIE10
    descripcion: str
    categoria: CategoriaCCC = CategoriaCCC.OTRA
    es_principal: bool = False
    es_raro: bool = False
    """True si el codigo figura en el listado de enfermedades raras
    (RM 478-2026-MINSA). Lo determina el adaptador que carga el CSV, no el
    dominio: el listado es politica, no logica."""

    fecha_diagnostico: date | None = None

    activo: bool = True
    """False si el proceso ya se resolvio: una fractura consolidada, una
    infeccion curada.

    PLAN_TECNICO §6.2 define K como diagnosticos cronicos ACTIVOS. Sin esta
    marca, una fractura de hace tres anios seguiria subiendo la complejidad de
    un paciente para siempre. Lo pone el adaptador que lee la historia, no el
    dominio.
    """

    @property
    def es_cronico(self) -> bool:
        """Cronico si cae en una categoria de CCC v2 o si figura en el listado
        de enfermedades raras.

        Se deriva en vez de guardarse como campo suelto para no tener dos
        verdades: `categoria` viene de `ccc_v2_categorias.csv` y `es_raro` de
        `cie10_raras_rm478.csv` — las dos primeras fuentes de PLAN_TECNICO
        §6.1. El dominio no decide cuales son cronicas: combina lo que los
        adaptadores ya marcaron.

        TODO: confirmar con mentor — la tercera fuente (codigos cronicos
        locales del INSN) todavia no llega hasta aqui. Cuando exista el
        listado, el adaptador debe asignarle categoria CCC al cargarlo, para
        que entre por este mismo camino y no por uno paralelo.
        """
        return self.categoria is not CategoriaCCC.OTRA or self.es_raro

    @property
    def cuenta_para_el_indice(self) -> bool:
        """Cronico y activo: los unicos que pesan en x2 y x3."""
        return self.es_cronico and self.activo

    def __str__(self) -> str:
        marca = " [principal]" if self.es_principal else ""
        resuelto = "" if self.activo else " [resuelto]"
        return f"{self.codigo} {self.descripcion}{marca}{resuelto}"


@dataclass(frozen=True, slots=True)
class Medicamento:
    """Un medicamento con su dosis.

    REGLA INVIOLABLE: `dosis` solo se puebla si el texto aparece LITERALMENTE
    en la fuente. `verificada_en_fuente=False` significa que hay que
    completarla a mano, no que se pueda estimar.

    Inventar una dosis es el peor fallo posible de este sistema: un medico
    firma rapido, la familia lee el Pasaporte como si fuera cierto, y nadie se
    entera hasta que alguien toma mal un farmaco.
    """

    nombre: str
    dosis: str | None = None
    via: str | None = None
    frecuencia: str | None = None
    verificada_en_fuente: bool = False

    @property
    def requiere_completar_manualmente(self) -> bool:
        return self.dosis is None or not self.verificada_en_fuente

    def texto_seguro(self) -> str:
        """Como se imprime en el Pasaporte.

        Si la dosis no esta verificada, NO se imprime un valor: se imprime el
        hueco. Un hueco visible obliga al medico a llenarlo. Una dosis
        plausible pero inventada no obliga a nada.
        """
        if self.requiere_completar_manualmente:
            return f"{self.nombre} — dosis: ____________  (completar)"
        partes = [self.nombre, self.dosis or ""]
        if self.via:
            partes.append(self.via)
        if self.frecuencia:
            partes.append(self.frecuencia)
        return " · ".join(p for p in partes if p)

    def __str__(self) -> str:
        return self.texto_seguro()


@dataclass(frozen=True, slots=True)
class Dispositivo:
    """Dispositivo o soporte tecnologico del que depende el paciente.

    Alimenta el factor x4. La clave debe coincidir con `peso_dispositivos` de
    `config/reglas_transicion.yaml`.
    """

    tipo: str
    descripcion: str = ""
    fecha_colocacion: date | None = None

    def __str__(self) -> str:
        return self.descripcion or self.tipo.replace("_", " ")


@dataclass(frozen=True, slots=True)
class Cirugia:
    nombre: str
    fecha: date | None = None
    institucion: str = ""

    def __str__(self) -> str:
        anio = f" ({self.fecha.year})" if self.fecha else ""
        return f"{self.nombre}{anio}"


class TipoContacto(Enum):
    PACIENTE = "paciente"
    MADRE = "madre"
    PADRE = "padre"
    CUIDADOR = "cuidador"
    OTRO = "otro"


@dataclass(frozen=True, slots=True)
class Contacto:
    """Una via para alcanzar al paciente o a su familia.

    `verificado_en` existe porque la plantilla oficial del INSN no tiene campo
    de telefono: el numero que hay, si lo hay, se anoto informalmente hace
    anios. La captura progresiva en los hitos de 14, 16 y 17 es funcionalidad
    central del sistema, no un formulario mas.
    """

    nombre: str
    tipo: TipoContacto
    telefono: Telefono | None = None
    correo: str | None = None
    verificado_en: date | None = None

    @property
    def es_del_paciente(self) -> bool:
        return self.tipo is TipoContacto.PACIENTE

    def esta_vigente(self, hoy: date) -> bool:
        if self.telefono is None:
            return False
        return self.telefono.esta_vigente(hoy)


@dataclass(frozen=True, slots=True)
class ResultadoTRAQ:
    """Transition Readiness Assessment Questionnaire — version espanola validada.

    Puntua de 1.0 a 5.0. Alimenta x5: brecha de preparacion = (5 - TRAQ)/4.
    Sin TRAQ se imputa 0.5 Y se marca dato_faltante.
    """

    puntaje: float
    fecha: date

    def __post_init__(self) -> None:
        if not 1.0 <= self.puntaje <= 5.0:
            raise ValueError(f"TRAQ fuera de rango [1.0, 5.0]: {self.puntaje}")


@dataclass
class HistoriaTextoLibre:
    """Los campos narrativos de la historia clinica.

    Se guardan por seccion y no como un unico bloque porque el desambiguador
    de abreviaturas necesita saber la seccion: 'PC' en examen fisico es
    perimetro cefalico; 'PC' en diagnosticos es paralisis cerebral. Sin la
    seccion no se puede resolver, y adivinar esta prohibido.
    """

    secciones: dict[str, str] = field(default_factory=dict)

    def texto_de(self, seccion: str) -> str:
        return self.secciones.get(seccion, "")

    def todo(self) -> str:
        return "\n\n".join(
            f"[{seccion}]\n{texto}" for seccion, texto in self.secciones.items()
        )


@dataclass(frozen=True, slots=True)
class ChecklistPreparacionINSN:
    """Checklist institucional de preparacion para la transicion (Rubrica INSN #3).

    Evalua los seis items literales exigidos por el INSN San Borja:
    1. Diagnostico
    2. Tratamiento
    3. Medicamentos
    4. Senales de alerta
    5. Documentos
    6. Servicio de destino

    Alimenta el factor x5 del IUT de forma compatible y complementaria con el TRAQ.
    """

    conoce_diagnostico: bool = False
    conoce_tratamiento: bool = False
    conoce_medicamentos: bool = False
    conoce_senales_de_alerta: bool = False
    conoce_documentos: bool = False
    conoce_servicio_de_destino: bool = False
    fecha_evaluacion: date | None = None

    @property
    def items_cumplidos(self) -> int:
        return sum(
            [
                self.conoce_diagnostico,
                self.conoce_tratamiento,
                self.conoce_medicamentos,
                self.conoce_senales_de_alerta,
                self.conoce_documentos,
                self.conoce_servicio_de_destino,
            ]
        )

    @property
    def total_items(self) -> int:
        return 6

    @property
    def proporcion_lograda(self) -> float:
        return self.items_cumplidos / 6.0

    @property
    def puntaje_traq_equivalente(self) -> float:
        """Convierte los 6 items a la escala TRAQ 1.0 - 5.0."""
        return 1.0 + self.proporcion_lograda * 4.0


@dataclass(frozen=True, slots=True)
class PerfilPsicosocial:
    """Necesidades psicosociales y red de apoyo familiar (Rubrica INSN #5).

    Documenta factores socioambientales determinantes para la continuidad de
    cuidados al cumplir la mayoria de edad: apoyo familiar, escolaridad,
    autonomia y situacion habitacional.
    """

    apoyo_familiar: str = ""
    escolaridad_ocupacion: str = ""
    autonomia_autocuidado: str = ""
    vivienda_servicios: str = ""
    observaciones: str = ""

