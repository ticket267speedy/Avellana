"""Los campos que se extraen de un documento de referencia, con sus catalogos.

Es el punto donde se junta lo que se le PIDE al modelo (`CampoPedido`) con lo que
se le EXIGE al resultado (`EspecificacionCampo`). Van juntos a proposito: si se
le pide un DNI y no se valida que tenga ocho digitos, la mitad del sistema no
sirve.

TODO: cargar desde `config/campos_documento.yaml`. Hoy esta en codigo para que
el modulo funcione de una; la politica pertenece a config, como el resto.

Los catalogos completos (558 codigos de la RM 478-2026, directorio de
establecimientos) se cargan de `config/`. Aqui van subconjuntos representativos
para que el modulo arranque sin depender de esos archivos.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from relevo.dominio.servicios.verificador_extraccion import (
    EspecificacionCampo,
    ReglaCruzada,
    regla_edad_coherente_con_nacimiento,
)
from relevo.infraestructura.llm.extractor import CampoPedido

# ── Catalogos ────────────────────────────────────────────────────────────────

# Subconjunto de la RM 478-2026-MINSA + codigos cronicos frecuentes.
# TODO: sustituir por config/cie10_raras_rm478.csv completo.
CIE10 = (
    "E84.0", "E84.1", "E84.8", "E84.9",   # fibrosis quistica
    "E10.9", "E10.2", "E10.5",            # diabetes tipo 1
    "N18.3", "N18.4", "N18.5",            # enfermedad renal cronica
    "Q21.0", "Q21.1", "Q21.3",            # cardiopatias congenitas
    "G80.0", "G80.1", "G80.9",            # paralisis cerebral
    "G40.2", "G71.0", "G71.2",            # epilepsia, distrofia muscular
    "D57.0", "D57.1",                     # anemia falciforme
    "K86.8", "M08.3", "M32.9",
    "E70.0", "E71.0", "E74.0",            # errores innatos del metabolismo
    "Z94.0", "Z94.4", "Z99.2",            # trasplante, dependencia de dialisis
    "C91.0", "C71.9",                     # oncologicos
)

ESPECIALIDADES = (
    "Pediatria", "Medicina", "Cirugia", "Gineco-Obst",
    "Laboratorio", "Dx. Imagen", "Otros",
)

CONDICIONES = ("Estable", "Mal Estado", "Fallecido")

DEPARTAMENTOS = (
    "Amazonas", "Ancash", "Apurimac", "Arequipa", "Ayacucho", "Cajamarca",
    "Callao", "Cusco", "Huancavelica", "Huanuco", "Ica", "Junin",
    "La Libertad", "Lambayeque", "Lima", "Loreto", "Madre de Dios",
    "Moquegua", "Pasco", "Piura", "Puno", "San Martin", "Tacna",
    "Tumbes", "Ucayali",
)

TIPOS_SEGURO = ("SIS", "EsSalud", "Particular", "SOAT", "Sanidad", "Ninguno")

# TODO: reemplazar por el directorio real de establecimientos (RENAES).
ESTABLECIMIENTOS = (
    "INSN San Borja", "INSN Brena", "Hospital Regional de Ucayali",
    "Hospital Regional de Loreto", "Hospital Regional del Cusco",
    "Hospital Manuel Nunez Butron Puno", "Hospital Daniel Alcides Carrion",
    "Hospital de Emergencias Pediatricas", "Hospital Hipolito Unanue",
    "Hospital Regional de Cajamarca", "Hospital Santa Rosa Piura",
    "Centro de Salud Villa El Salvador",
)


# ── Lo que se le pide al modelo ──────────────────────────────────────────────


def campos_pedidos() -> tuple[CampoPedido, ...]:
    return (
        CampoPedido("dni", "numero de DNI del paciente", "exactamente 8 digitos",
                    ("DNI", "D.N.I.", "Documento", "Doc. Identidad"), "71234567"),
        CampoPedido("celular", "telefono de contacto del paciente o su familia",
                    "9 digitos empezando en 9", ("Celular", "Cel.", "Telefono", "Tlf")),
        CampoPedido("fecha_nacimiento", "fecha de nacimiento del paciente",
                    "DD/MM/AAAA", ("Fecha de Nacimiento", "F. Nac.", "FN"), "14/03/2009"),
        CampoPedido("edad_anios", "edad del paciente en anios COMPLETOS, solo si esta escrita",
                    "1 o 2 digitos", ("Edad", "Anios", "Anos")),
        CampoPedido("apellido_paterno", "apellido paterno", "", ("Apellido Paterno", "Ap. Paterno")),
        CampoPedido("apellido_materno", "apellido materno", "", ("Apellido Materno", "Ap. Materno")),
        CampoPedido("nombres", "nombres de pila del paciente", "", ("Nombres", "Nombre")),
        CampoPedido("tipo_seguro", "tipo de seguro del paciente", "",
                    ("Tipo de seguro", "Seguro", "Financiador"), "SIS"),
        CampoPedido("departamento", "departamento de procedencia o domicilio", "",
                    ("Departamento", "Dpto", "Region")),
        CampoPedido("numero_hc", "numero de historia clinica", "digitos",
                    ("N Historia Clinica", "HC", "H.C.", "N HC")),
        CampoPedido("establecimiento_origen", "establecimiento que emite la referencia", "",
                    ("Establecimiento de origen", "EE.SS. Origen", "Procedencia")),
        CampoPedido("establecimiento_destino", "establecimiento al que se deriva", "",
                    ("Establecimiento Destino", "EE.SS. Destino", "Destino")),
        CampoPedido("cie10_1", "codigo CIE-10 del PRIMER diagnostico",
                    "una letra mayuscula, dos digitos, y opcionalmente punto y un digito",
                    ("CIE-10", "CIE 10", "Codigo CIE"), "E84.0"),
        CampoPedido("cie10_2", "codigo CIE-10 del SEGUNDO diagnostico, si existe",
                    "una letra mayuscula, dos digitos, y opcionalmente punto y un digito",
                    ("CIE-10", "CIE 10")),
        CampoPedido("diagnostico_1", "texto del primer diagnostico", "",
                    ("Diagnostico", "Dx", "Impresion diagnostica")),
        CampoPedido("especialidad_destino", "especialidad a la que se deriva", "",
                    ("Especialidad de Destino", "Especialidad", "Servicio")),
        CampoPedido("condicion_traslado", "condicion del paciente al inicio del traslado", "",
                    ("Condiciones del Paciente", "Condicion")),
        CampoPedido("tratamiento", "tratamiento indicado, transcrito literalmente", "",
                    ("Tratamiento", "Indicaciones", "Terapeutica")),
    )


# ── Lo que se le exige al resultado ──────────────────────────────────────────


def especificaciones() -> Mapping[str, EspecificacionCampo]:
    def esp(**kw) -> EspecificacionCampo:
        return EspecificacionCampo(**kw)

    return {
        "dni": esp(nombre="dni", etiqueta="DNI", patron=r"\d{8}",
                   descripcion_formato="ocho digitos"),
        "celular": esp(nombre="celular", etiqueta="Celular", patron=r"9\d{8}",
                       descripcion_formato="nueve digitos empezando en 9",
                       obligatorio=False),
        "fecha_nacimiento": esp(nombre="fecha_nacimiento", etiqueta="Fecha de nacimiento",
                                patron=r"\d{2}[/\-.]\d{2}[/\-.]\d{4}",
                                descripcion_formato="DD/MM/AAAA"),
        "edad_anios": esp(nombre="edad_anios", etiqueta="Edad", patron=r"\d{1,2}",
                          descripcion_formato="uno o dos digitos"),
        "apellido_paterno": esp(nombre="apellido_paterno", etiqueta="Apellido paterno",
                                patron=r"[A-Za-zÁÉÍÓÚÑáéíóúñ' ]{2,40}",
                                descripcion_formato="solo letras"),
        "apellido_materno": esp(nombre="apellido_materno", etiqueta="Apellido materno",
                                patron=r"[A-Za-zÁÉÍÓÚÑáéíóúñ' ]{2,40}",
                                descripcion_formato="solo letras"),
        "nombres": esp(nombre="nombres", etiqueta="Nombres",
                       patron=r"[A-Za-zÁÉÍÓÚÑáéíóúñ' ]{2,60}",
                       descripcion_formato="solo letras"),
        "tipo_seguro": esp(nombre="tipo_seguro", etiqueta="Tipo de seguro",
                           catalogo=TIPOS_SEGURO, distancia_maxima=2.0),
        "departamento": esp(nombre="departamento", etiqueta="Departamento",
                            catalogo=DEPARTAMENTOS, distancia_maxima=3.0),
        "numero_hc": esp(nombre="numero_hc", etiqueta="N° Historia Clinica",
                         patron=r"\d{4,10}", descripcion_formato="entre 4 y 10 digitos"),
        "establecimiento_origen": esp(nombre="establecimiento_origen",
                                      etiqueta="Establecimiento de origen",
                                      catalogo=ESTABLECIMIENTOS, distancia_maxima=5.0),
        "establecimiento_destino": esp(nombre="establecimiento_destino",
                                       etiqueta="Establecimiento destino",
                                       catalogo=ESTABLECIMIENTOS, distancia_maxima=5.0),
        "cie10_1": esp(nombre="cie10_1", etiqueta="CIE-10 diagnostico 1",
                       catalogo=CIE10, distancia_maxima=1.5),
        "cie10_2": esp(nombre="cie10_2", etiqueta="CIE-10 diagnostico 2",
                       catalogo=CIE10, distancia_maxima=1.5, obligatorio=False),
        # Texto libre: sin catalogo ni patron. NO se puede validar, y por eso
        # nunca deberia darse por bueno sin que una persona lo lea.
        "diagnostico_1": esp(nombre="diagnostico_1", etiqueta="Diagnostico 1",
                             umbral_confianza=1.01),
        "especialidad_destino": esp(nombre="especialidad_destino", etiqueta="Especialidad destino",
                                    catalogo=ESPECIALIDADES, distancia_maxima=3.0),
        "condicion_traslado": esp(nombre="condicion_traslado", etiqueta="Condicion al traslado",
                                  catalogo=CONDICIONES, distancia_maxima=3.0),
        "tratamiento": esp(nombre="tratamiento", etiqueta="Tratamiento",
                           umbral_confianza=1.01, obligatorio=False),
    }


def reglas_cruzadas(hoy: date) -> tuple[ReglaCruzada, ...]:
    return (regla_edad_coherente_con_nacimiento(hoy=hoy),)
