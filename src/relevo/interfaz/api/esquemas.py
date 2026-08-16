"""Los objetos que cruzan la frontera HTTP. Pydantic v2, sin logica de negocio.

═══════════════════════════════════════════════════════════════════════════════
CERO DOBLE DIGITACION — LA RESTRICCION QUE MANDA EN ESTE ARCHIVO
═══════════════════════════════════════════════════════════════════════════════

    Relevo no pide datos. Pide decisiones.

El INSN ya tiene SisGalenPlus. Si Relevo pide que el personal vuelva a escribir
diagnostico, tratamiento o filiacion, el sistema se abandona en la segunda
semana por muy bien construido que este. Este es el motivo real por el que el
extractor y el verificador existen.

Consecuencia para este archivo, y es comprobable: **ningun esquema de entrada
de los endpoints de personal de salud admite un campo clinico de escritura
libre.** Lo unico que el personal escribe son veredictos de verificacion,
selecciones de lista cerrada y notas administrativas explicitamente marcadas
como no clinicas.

`tests/interfaz/test_sin_captura_clinica_por_personal.py` recorre estos
esquemas y falla si aparece uno.

El dato clinico entra por exactamente tres puertas, y ninguna es el teclado del
personal de salud:
  1. digitalizacion de un documento que ya existe -> extractor -> verificador
     -> firma;
  2. lectura del sistema del hospital, el dia que exista el adaptador;
  3. el propio paciente sobre si mismo — que no es doble digitacion, porque ese
     dato no lo tenia nadie mas.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────────────────────────────────────────────────────────
# Marcador de esquemas de entrada del personal de salud
#
# El test bloqueante los reconoce por herencia, no por el nombre del archivo:
# un esquema nuevo puesto en otro sitio seguiria estando vigilado mientras
# herede de aqui, y si alguien lo crea sin heredar, el test tambien lo detecta
# porque recorre los endpoints y no las clases.
# ─────────────────────────────────────────────────────────────────────────────


class EntradaDePersonal(BaseModel):
    """Todo lo que un profesional de salud puede enviar al sistema.

    Heredar de aqui es declarar: "esto lo teclea alguien del INSN o del
    receptor, y por tanto no puede contener dato clinico".
    """

    model_config = ConfigDict(extra="forbid")
    # `extra="forbid"` no es cosmetico: sin el, un cliente podria enviar
    # {"diagnostico": "..."} y Pydantic lo descartaria en silencio. Prefiero
    # que reviente: un campo clinico que llega y se ignora es un campo clinico
    # que alguien creyo haber guardado.


class EntradaDePaciente(BaseModel):
    """Lo que el propio paciente declara sobre si mismo.

    Aqui SI hay texto libre con contenido clinico, y esta bien: es la tercera
    puerta. Nadie mas tenia este dato, y su valor esta justamente en no haberlo
    normalizado. Nunca sobrescribe el Pasaporte — genera un caso de
    conciliacion (ver `dominio/entidades/conciliacion.py`).
    """

    model_config = ConfigDict(extra="forbid")


# ═══════════════════════════════════════════════════════════════════════════
# Salidas — radar y paciente
# ═══════════════════════════════════════════════════════════════════════════


class AporteSalida(BaseModel):
    """Un factor del indice con su peso. El desglose no es un adorno.

    Un indice sin explicacion es un dato invalido en este dominio: es lo que
    permite a un medico discutirlo y corregirlo, y es lo que convierte
    "priorizacion autonoma" en "una lista ordenada que se puede auditar".
    """

    nombre: str
    valor: float
    beta: float
    aporte: float
    dato_faltante: bool


class IndiceSalida(BaseModel):
    valor: float
    z: float
    estado: str
    confianza: float
    datos_insuficientes: bool
    aportes: list[AporteSalida]


class FilaRadarSalida(BaseModel):
    """Una linea del radar del INSN."""

    id: str
    edad: int
    meses_restantes: int
    cohorte: str
    diagnostico_principal: str
    indice: IndiceSalida
    estado_ciclo: str | None
    estado_ciclo_etiqueta: str | None
    responsable: str | None
    tiene_destino_asegurado: bool
    dias_para_corte: int | None
    requiere_atencion_ahora: bool


class PacienteSalida(BaseModel):
    id: str
    edad: int
    sexo: str
    procedencia: str
    tipo_seguro: str
    meses_restantes: int
    cohorte: str
    diagnosticos: list[str]
    medicamentos: list[str]
    dispositivos: list[str]
    alergias: list[str]
    traq: float | None
    tiene_contacto_vigente: bool


# ═══════════════════════════════════════════════════════════════════════════
# Ciclo
# ═══════════════════════════════════════════════════════════════════════════


class EventoSalida(BaseModel):
    estado: str
    etiqueta: str
    fecha: date
    registrado_por: str
    nota: str


class EtapaSalida(BaseModel):
    """Una de las siete etapas de la linea de tiempo del paciente."""

    orden: int
    estado: str
    etiqueta: str
    etiqueta_llana: str
    alcanzada: bool
    es_actual: bool


class CicloSalida(BaseModel):
    paciente_id: str
    estado: str
    etiqueta: str
    etiqueta_llana: str
    responsable: str
    responsable_etiqueta: str
    fecha_estado: date
    dias_en_estado: int
    plazo_dias: int | None
    situacion_plazo: str
    fecha_limite: date | None
    establecimiento_receptor: str
    servicio_asignado: str
    fecha_cita: date | None
    tiene_destino_asegurado: bool
    transiciones_posibles: list[str]
    etapas: list[EtapaSalida]
    historial: list[EventoSalida]


class AvanzarCicloEntrada(EntradaDePersonal):
    """Avanzar el ciclo es un clic. Esto es lo unico que viaja con el.

    Ni un campo clinico. `nota_administrativa` se llama asi y no `nota` porque
    el nombre es parte de la regla: un campo llamado `nota` acabaria recibiendo
    diagnosticos.
    """

    estado: str = Field(description="estado destino, del enum EstadoCiclo")
    registrado_por: str = Field(default="", max_length=120)
    fuente_confirmacion: str | None = Field(
        default=None,
        description="solo al confirmar primera atencion: formal, receptor o pragmatica",
    )
    motivo_reingreso: str | None = Field(
        default=None, description="solo al reabrir: valor de MotivoReingreso"
    )
    nota_administrativa: str = Field(
        default="",
        max_length=280,
        description=(
            "NO CLINICA. Contexto administrativo del avance: con quien se hablo, "
            "por que medio. Nunca diagnostico, dosis ni resultado."
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Receptor
# ═══════════════════════════════════════════════════════════════════════════


class AccionDisponibleSalida(BaseModel):
    codigo: str
    etiqueta: str


class FilaBandejaSalida(BaseModel):
    """Una referencia entrante en la bandeja del receptor.

    Lleva `dias_para_corte` a proposito: el receptor tiene que poder ver que
    este adolescente se queda sin ningun servicio dentro de X dias. Es la unica
    cifra que convierte un tramite en una urgencia.
    """

    paciente_id: str
    edad: int
    estado: str
    etiqueta: str
    dias_en_estado: int
    situacion_plazo: str
    dias_para_corte: int | None
    diagnostico_principal: str
    acciones: list[AccionDisponibleSalida]


class AccionReceptorEntrada(EntradaDePersonal):
    """Lo que acompana a las seis acciones del receptor.

    Todas las acciones son de un clic; estos campos son opcionales y ninguno
    es clinico. `servicio` es una seleccion de la cartera del establecimiento y
    `faltantes` es una lista CERRADA: son las dos unicas cosas que el receptor
    aporta y que el sistema no podia saber solo.
    """

    quien: str = Field(default="", max_length=120)
    servicio: str = Field(
        default="",
        max_length=160,
        description="servicio y medico asignado. Seleccion de cartera, no texto clinico",
    )
    fecha_cita: date | None = None
    faltantes: list[str] = Field(
        default_factory=list,
        description=(
            "lista cerrada: falta_epicrisis, falta_resultado_laboratorio, "
            "falta_consentimiento, falta_dato_de_contacto, otro"
        ),
    )
    detalle: str = Field(
        default="",
        max_length=280,
        description=(
            "OPCIONAL y complementario. Precisa que documento falta; nunca es "
            "el portador del dato clinico."
        ),
    )


class ResultadoAccionSalida(BaseModel):
    accion: str
    estado: str
    etiqueta: str
    responsable: str
    responsable_etiqueta: str
    cambio_de_turno: bool
    devolvio_el_turno: bool
    gano_destino_asegurado: bool
    mensaje: str


# ═══════════════════════════════════════════════════════════════════════════
# Aprendizaje — Entrenate
# ═══════════════════════════════════════════════════════════════════════════


class HabilidadSalida(BaseModel):
    numero: int
    codigo: str
    titulo: str
    estado: str
    estado_etiqueta: str


class PasoSalida(BaseModel):
    titulo: str
    contenido: str


class FuenteSalida(BaseModel):
    """La fuente va VISIBLE, al lado de la afirmacion.

    Una leccion que le dice a un adolescente que su madre ya no puede pedir sus
    resultados tiene que poder decirle en que norma esta escrito, o es
    indistinguible de un rumor.
    """

    afirmacion: str
    norma: str
    detalle: str


class LeccionSalida(BaseModel):
    numero: int
    titulo: str
    objetivo: str
    habilidad: str
    completa: bool
    sello: str | None
    pasos: list[PasoSalida]
    fuentes: list[FuenteSalida]


class AprendizajeSalida(BaseModel):
    paciente_id: str
    franja: str | None
    franja_etiqueta: str | None
    version_pasaporte: str | None
    resumen: str
    total_logradas: int
    habilidades: list[HabilidadSalida]
    siguiente_leccion: int | None
    motivo: str
    lecciones: list[LeccionSalida]


class AvanzarAprendizajeEntrada(EntradaDePaciente):
    """Lo marca el adolescente sobre si mismo. Nunca el personal de salud."""

    habilidad: str
    estado: str = Field(description="por_iniciar, en_practica, lograda, necesita_refuerzo")
    nota: str = Field(default="", max_length=280)


# ═══════════════════════════════════════════════════════════════════════════
# Conciliacion de medicacion
# ═══════════════════════════════════════════════════════════════════════════


class MedicacionDeclaradaEntrada(EntradaDePaciente):
    """Lo que el paciente dice que toma, con sus palabras.

    Texto libre a proposito: es la unica entrada clinica libre de toda la API,
    y viene del paciente. Nunca sobrescribe el Pasaporte.
    """

    nombre: str = Field(max_length=160)
    dosis: str | None = Field(default=None, max_length=80)
    frecuencia: str | None = Field(default=None, max_length=80)
    lo_sigue_tomando: bool = True


class DeclararMedicacionEntrada(EntradaDePaciente):
    medicamentos: list[MedicacionDeclaradaEntrada]


class LineaMedicacionSalida(BaseModel):
    nombre: str
    dosis: str | None
    frecuencia: str | None
    origen: str
    insignia: str
    hay_que_completar: bool


class DiscrepanciaSalida(BaseModel):
    tipo: str
    etiqueta: str
    medicamento: str
    valor_pasaporte: str | None
    valor_declarado: str | None
    descripcion: str


class ConciliacionSalida(BaseModel):
    paciente_id: str
    requiere_revision: bool
    responsable: str
    titular: str
    lineas: list[LineaMedicacionSalida]
    discrepancias: list[DiscrepanciaSalida]


class ResolverConciliacionEntrada(EntradaDePersonal):
    """Una persona decide. El sistema nunca elige cual version es la correcta.

    `nota` aqui SI es texto libre y no viola la regla: describe la DECISION del
    profesional sobre su propio proceso ("se confirmo con la madre por
    telefono"), no un dato clinico del paciente.
    """

    quien: str = Field(min_length=1, max_length=120)
    nota: str = Field(min_length=1, max_length=500)


# ═══════════════════════════════════════════════════════════════════════════
# Metricas
# ═══════════════════════════════════════════════════════════════════════════


class FilaRiesgoSalida(BaseModel):
    paciente_id: str
    dias_para_corte: int
    estado: str
    responsable: str
    es_urgente: bool


class FracasoSalida(BaseModel):
    id_paciente: str
    fecha_cumpleanios: date
    estado_al_cumplir: str
    dias_en_ese_estado: int


class CorteEtarioSalida(BaseModel):
    """La metrica estrella. Va arriba de todo en el radar."""

    en_riesgo_90_dias: int
    ya_cumplieron_sin_destino: int
    total_cohorte: int
    horizonte_dias: int
    titular: str
    en_riesgo: list[FilaRiesgoSalida]
    consumados: list[FracasoSalida]
    sin_fecha_de_nacimiento: list[str]


class CoberturaDestinosSalida(BaseModel):
    """El entregable de B1. La cifra no se esconde: es la evidencia.

    El propio INSN lo escribio: "la falta de datos tambien es un hallazgo".
    El sistema no inventa destinos; mide su ausencia.
    """

    total_evaluados: int
    con_destino: int
    sin_destino: int
    porcentaje_sin_destino: float
    por_motivo: dict[str, int]
    brecha_de_oferta: int
    resumen_directorio: str


# ═══════════════════════════════════════════════════════════════════════════
# Apoderado
# ═══════════════════════════════════════════════════════════════════════════


class PermisosApoderadoSalida(BaseModel):
    puede_ver_estado_del_ciclo: bool
    puede_ver_pasaporte: bool
    puede_ver_aprendizaje: bool
    base_legal: str
    base_legal_etiqueta: str
    norma: str
    aviso: str | None
    dias_para_el_corte: int


# ═══════════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════════


class CambiarRolEntrada(BaseModel):
    """Barra de control de demo. No es autenticacion y no finge serlo."""

    model_config = ConfigDict(extra="forbid")
    rol: str


class AvanzarEtapaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paciente_id: str


class EstadoDemoSalida(BaseModel):
    es_demo: bool
    pacientes: int
    ciclos: int
    entradas_auditoria: int
    cadena_intacta: bool
    fecha_referencia: date
    aviso: str
