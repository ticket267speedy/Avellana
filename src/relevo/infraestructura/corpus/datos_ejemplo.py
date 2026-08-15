"""Datos de relleno para el corpus, mientras no se conecta con `cohorte_sintetica`.

Esto es un puente temporal. Lo correcto es que el corpus de documentos y la
cohorte del Radar sean la MISMA poblacion: un formulario escaneado se convierte
en un paciente priorizado sin costuras, y la demo se puede recorrer de punta a
punta con un solo caso.

TODO: reemplazar `valores_de_ejemplo` por un adaptador que tome un `Paciente`
de `infraestructura.fuentes.cohorte_sintetica` y lo proyecte a los campos de la
Hoja de Referencia.

Nada de aqui corresponde a una persona real.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

APELLIDOS = (
    "Quispe", "Mamani", "Huaman", "Flores", "Ccahuana", "Ramos", "Vilca",
    "Condori", "Apaza", "Chambi", "Cruz", "Zapata", "Rojas", "Paredes",
    "Ticona", "Cusi", "Sanchez", "Aguirre", "Bautista", "Ninahuanca",
)
NOMBRES_F = ("Ana Lucia", "Maria Fernanda", "Rosa Elena", "Yulissa", "Katherine", "Milagros")
NOMBRES_M = ("Juan Diego", "Luis Alberto", "Jose Manuel", "Cristian", "Jhonatan", "Piero")

DEPARTAMENTOS = (
    "Lima", "Ucayali", "Loreto", "Cusco", "Puno", "Junin", "Piura",
    "Cajamarca", "Ayacucho", "Huanuco", "Arequipa", "La Libertad",
)

ESTABLECIMIENTOS = (
    "Hospital Regional de Ucayali", "Hospital Regional de Loreto",
    "Hospital Regional del Cusco", "Hospital Manuel Nunez Butron Puno",
    "Hospital Daniel Alcides Carrion", "Hospital de Emergencias Pediatricas",
    "Centro de Salud Villa El Salvador", "Hospital Hipolito Unanue",
    "Hospital Regional de Cajamarca", "Hospital Santa Rosa Piura",
)

# (diagnostico, CIE-10). Codigos tomados de patologias que llegan al INSN SB.
DIAGNOSTICOS = (
    ("Fibrosis quistica con manifestaciones pulmonares", "E84.0"),
    ("Diabetes mellitus tipo 1 sin complicaciones", "E10.9"),
    ("Enfermedad renal cronica estadio 5", "N18.5"),
    ("Tetralogia de Fallot", "Q21.3"),
    ("Paralisis cerebral no especificada", "G80.9"),
    ("Anemia de celulas falciformes con crisis", "D57.1"),
    ("Insuficiencia pancreatica exocrina", "K86.8"),
    ("Epilepsia focal sintomatica", "G40.2"),
    ("Lupus eritematoso sistemico", "M32.9"),
    ("Artritis idiopatica juvenil poliarticular", "M08.3"),
)

ESPECIALIDADES = ("Pediatria", "Medicina", "Cirugia", "Gineco-Obst", "Laboratorio")

TRATAMIENTOS = (
    "Dornasa alfa 2.5 mg nebulizada c/24h. Enzimas pancreaticas con cada comida.",
    "Insulina glargina 18 UI nocturna. Insulina lispro segun conteo de carbohidratos.",
    "Enalapril 5 mg c/12h. Carbonato de calcio 500 mg c/8h. Dieta hipoproteica.",
    "Acido valproico 500 mg c/12h. Control de niveles sericos cada 6 meses.",
    "Hidroxiurea 15 mg/kg/dia. Acido folico 5 mg diario.",
)

ANAMNESIS = (
    "Paciente en control por consultorio externo desde los {a} anos. Refiere "
    "sintomatologia persistente y necesidad de continuar seguimiento especializado.",
    "Acude por control programado. Madre refiere adherencia irregular al "
    "tratamiento en los ultimos {a} meses por dificultad para acudir a citas.",
    "Paciente con diagnostico establecido desde la infancia, en seguimiento "
    "multidisciplinario. Se solicita continuidad de atencion en servicio de adultos.",
)


def valores_de_ejemplo(rnd: random.Random) -> dict[str, str]:
    """Un juego completo de campos para una Hoja de Referencia.

    Se sesga a 14–18 anos a proposito: es la cohorte del proyecto y es la que
    tiene que quedar bien representada en el corpus.
    """
    hoy = date(2026, 8, 14)
    edad = rnd.randint(14, 18)
    nacimiento = hoy - timedelta(days=edad * 365 + rnd.randint(0, 364))
    femenino = rnd.random() < 0.5

    dx = rnd.sample(DIAGNOSTICOS, k=rnd.randint(1, 3))
    departamento = rnd.choice(DEPARTAMENTOS)

    valores = {
        "fecha_referencia": hoy.strftime("%d/%m/%Y"),
        "hora": f"{rnd.randint(8, 17):02d}:{rnd.choice(('00', '15', '30', '45'))}",
        "asegurado": "X",
        "fecha_nacimiento": nacimiento.strftime("%d/%m/%Y"),
        "tipo_seguro": rnd.choice(("SIS", "SIS", "SIS", "EsSalud", "Particular")),
        "dni": f"7{rnd.randint(1000000, 9999999)}",
        "celular": f"9{rnd.randint(10000000, 99999999)}",
        "establecimiento_origen": rnd.choice(ESTABLECIMIENTOS),
        "establecimiento_destino": "INSN San Borja",
        "numero_hc": str(rnd.randint(10000, 99999)),
        "apellido_paterno": rnd.choice(APELLIDOS),
        "apellido_materno": rnd.choice(APELLIDOS),
        "nombres": rnd.choice(NOMBRES_F if femenino else NOMBRES_M),
        "sexo": "X",
        "edad_anios": str(edad),
        "edad_meses": str(rnd.randint(0, 11)),
        "direccion": f"{rnd.choice(('Jr.', 'Av.', 'Calle'))} {rnd.choice(('Los Cedros', 'San Martin', 'Bolognesi', 'Grau', 'Las Palmeras'))} {rnd.randint(100, 999)}",
        "distrito": rnd.choice(("Calleria", "San Juan", "Wanchaq", "El Tambo", "Castilla", "Ate")),
        "departamento": departamento,
        "anamnesis": rnd.choice(ANAMNESIS).format(a=rnd.randint(2, 9)),
        "temperatura": f"{rnd.uniform(36.2, 38.4):.1f}",
        "presion_arterial": f"{rnd.randint(90, 125)}/{rnd.randint(55, 80)}",
        "frecuencia_respiratoria": str(rnd.randint(16, 28)),
        "frecuencia_cardiaca": str(rnd.randint(64, 104)),
        "peso": f"{rnd.uniform(34.0, 62.0):.1f}",
        "examen_fisico": "Regular estado general, hidratado, ventilando espontaneamente. Abdomen blando depresible.",
        "examenes_auxiliares": "Hemograma dentro de parametros. Se adjuntan resultados de laboratorio e imagenes.",
        "tratamiento": rnd.choice(TRATAMIENTOS),
        "fecha_atencion": (hoy + timedelta(days=rnd.randint(15, 120))).strftime("%d/%m/%Y"),
        "motivo_referencia": rnd.choice(
            ("Transicion a servicio de adultos", "Continuidad de tratamiento", "Evaluacion por especialidad")
        ),
        "nombre_atendera": f"Dr. {rnd.choice(APELLIDOS)}",
        "especialidad_destino": rnd.choice(ESPECIALIDADES),
        "condicion_traslado": rnd.choice(("Estable", "Estable", "Estable", "Mal Estado")),
        "responsable_nombre": f"Dr{'a' if rnd.random() < 0.5 else ''}. {rnd.choice(APELLIDOS)}",
        "responsable_colegiatura": str(rnd.randint(20000, 79999)),
    }

    for i, (nombre_dx, codigo) in enumerate(dx, start=1):
        valores[f"diagnostico_{i}"] = nombre_dx
        valores[f"cie10_{i}"] = codigo

    return valores
