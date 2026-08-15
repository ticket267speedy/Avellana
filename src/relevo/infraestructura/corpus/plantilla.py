"""Plantilla de la Hoja de Referencia y el mapa de coordenadas de sus campos.

Este modulo hace dos cosas:

1. Dibuja una plantilla EN BLANCO aproximada de la Hoja de Referencia del MINSA,
   para que el generador de corpus funcione hoy, sin depender de conseguir el
   PDF oficial en alta resolucion.

2. Declara el MAPA DE CAMPOS: el rectangulo de cada campo en coordenadas de la
   plantilla. Ese mapa es la pieza central del sistema y no es descartable —
   cuando se consiga el formulario oficial escaneado, se reemplaza la funcion de
   dibujo y se recalibran las coordenadas, pero el resto no cambia.

POR QUE IMPORTA EL MAPA
El mapa convierte "lee esta pagina" en "lee esta cajita de 340x52 px que
contiene un DNI". Eso baja la dificultad para cualquier modelo en un orden de
magnitud, y permite decirle al modelo QUE espera encontrar en cada recorte.

TODO: sustituir `dibujar_plantilla_base` por el escaneo del formulario oficial y
recalibrar `MAPA_CAMPOS` con la herramienta de calibracion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# A4 a 300 ppp. Es la resolucion a la que se escanea un formulario en un
# hospital y a la que un celular fotografia una hoja de cerca.
ANCHO, ALTO = 2480, 3508

NEGRO = (20, 20, 20)
GRIS = (110, 110, 110)
BLANCO = (255, 255, 255)


@dataclass(frozen=True, slots=True)
class Campo:
    """Un campo del formulario y donde vive en la plantilla."""

    nombre: str
    etiqueta: str
    x: int
    y: int
    ancho: int
    alto: int
    tipo: str = "texto"
    """texto | numero | fecha | codigo | casilla | parrafo"""

    lineas: int = 1
    """Cuantas lineas de escritura caben. Los parrafos usan varias."""

    @property
    def caja(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.ancho, self.y + self.alto)

    def recortar(self, imagen: Image.Image, margen: int = 6) -> Image.Image:
        """El recorte de este campo. Lo que se le manda al modelo."""
        x0, y0, x1, y1 = self.caja
        return imagen.crop(
            (
                max(0, x0 - margen),
                max(0, y0 - margen),
                min(imagen.width, x1 + margen),
                min(imagen.height, y1 + margen),
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# El mapa. Coordenadas en pixeles sobre la plantilla de 2480x3508.
# ─────────────────────────────────────────────────────────────────────────────

MAPA_CAMPOS: tuple[Campo, ...] = (
    # 1 · DATOS GENERALES
    Campo("fecha_referencia", "Fecha", 300, 395, 330, 60, "fecha"),
    Campo("hora", "Hora", 800, 395, 220, 60, "texto"),
    Campo("asegurado", "Asegurado", 1330, 395, 90, 60, "casilla"),
    Campo("fecha_nacimiento", "Fecha de Nacimiento", 1950, 395, 380, 60, "fecha"),
    Campo("tipo_seguro", "Tipo de seguro", 780, 470, 380, 55, "texto"),
    Campo("dni", "DNI", 1300, 470, 340, 55, "numero"),
    Campo("celular", "Celular", 1830, 470, 400, 55, "numero"),
    Campo("establecimiento_origen", "Establecimiento de origen", 760, 545, 1560, 62, "texto"),
    Campo("establecimiento_destino", "Establecimiento destino", 760, 625, 1560, 62, "texto"),
    # 2 · IDENTIFICACION DEL USUARIO
    Campo("numero_hc", "N° Historia Clinica", 1490, 745, 400, 60, "numero"),
    Campo("apellido_paterno", "Apellido Paterno", 170, 880, 480, 62, "texto"),
    Campo("apellido_materno", "Apellido Materno", 680, 880, 480, 62, "texto"),
    Campo("nombres", "Nombres", 1190, 880, 1130, 62, "texto"),
    Campo("sexo", "Sexo", 300, 965, 60, 55, "casilla"),
    Campo("edad_anios", "Edad anios", 1420, 965, 130, 55, "numero"),
    Campo("edad_meses", "Edad meses", 1740, 965, 130, 55, "numero"),
    Campo("direccion", "Direccion", 330, 1040, 700, 58, "texto"),
    Campo("distrito", "Distrito", 1230, 1040, 520, 58, "texto"),
    Campo("departamento", "Departamento", 1980, 1040, 340, 58, "texto"),
    # 3 · RESUMEN DE HISTORIA CLINICA
    Campo("anamnesis", "Anamnesis", 330, 1180, 1990, 150, "parrafo", lineas=3),
    Campo("temperatura", "T°", 400, 1400, 200, 52, "numero"),
    Campo("presion_arterial", "P.A.", 830, 1400, 220, 52, "texto"),
    Campo("frecuencia_respiratoria", "F.R.", 1260, 1400, 180, 52, "numero"),
    Campo("frecuencia_cardiaca", "F.C.", 1630, 1400, 180, 52, "numero"),
    Campo("peso", "Peso", 2020, 1400, 240, 52, "numero"),
    Campo("examen_fisico", "Examen fisico", 330, 1470, 1990, 130, "parrafo", lineas=3),
    Campo("examenes_auxiliares", "Examenes Auxiliares", 620, 1650, 1700, 110, "parrafo", lineas=2),
    Campo("diagnostico_1", "Diagnostico 1", 480, 1830, 1180, 55, "texto"),
    Campo("cie10_1", "CIE-10 diagnostico 1", 1760, 1830, 300, 55, "codigo"),
    Campo("diagnostico_2", "Diagnostico 2", 480, 1900, 1180, 55, "texto"),
    Campo("cie10_2", "CIE-10 diagnostico 2", 1760, 1900, 300, 55, "codigo"),
    Campo("diagnostico_3", "Diagnostico 3", 480, 1970, 1180, 55, "texto"),
    Campo("cie10_3", "CIE-10 diagnostico 3", 1760, 1970, 300, 55, "codigo"),
    Campo("tratamiento", "Tratamiento", 480, 2080, 1840, 140, "parrafo", lineas=3),
    # 4 · DATOS DE LA REFERENCIA
    Campo("fecha_atencion", "Fecha en que sera atendido", 1000, 2400, 420, 55, "fecha"),
    Campo("motivo_referencia", "Motivo de Referencia", 1620, 2400, 700, 55, "texto"),
    Campo("nombre_atendera", "Nombre de quien lo atendera", 1000, 2470, 1320, 55, "texto"),
    Campo("especialidad_destino", "Especialidad de Destino", 620, 2610, 700, 55, "texto"),
    Campo("condicion_traslado", "Condicion al inicio del traslado", 620, 2700, 500, 55, "texto"),
    Campo("responsable_nombre", "Responsable de la referencia", 200, 2900, 520, 55, "texto"),
    Campo("responsable_colegiatura", "Colegiatura del responsable", 200, 2975, 520, 55, "numero"),
    # Cierre del ciclo — la parte que nunca vuelve
    Campo("condicion_llegada", "Condicion a la llegada", 700, 3230, 500, 55, "texto"),
    Campo("persona_recibe", "Persona que recibe", 1750, 2900, 520, 55, "texto"),
    Campo("fecha_recepcion", "Fecha de recepcion", 1900, 3050, 300, 52, "fecha"),
)

CAMPOS_POR_NOMBRE = {c.nombre: c for c in MAPA_CAMPOS}


# ─────────────────────────────────────────────────────────────────────────────
# Dibujo de la plantilla en blanco
# ─────────────────────────────────────────────────────────────────────────────


def _fuente(tam: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    candidatas = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if negrita
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if negrita else "C:/Windows/Fonts/arial.ttf",
    )
    for ruta in candidatas:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default(tam)


def dibujar_plantilla_base() -> Image.Image:
    """Plantilla EN BLANCO aproximada de la Hoja de Referencia del MINSA.

    Aproximada a proposito: reproduce las secciones, las etiquetas y la posicion
    de los campos, no el diseno grafico exacto. Sirve para generar el corpus y
    para calibrar el pipeline. Cuando se consiga el original escaneado, se
    reemplaza esta funcion.
    """
    img = Image.new("RGB", (ANCHO, ALTO), BLANCO)
    d = ImageDraw.Draw(img)

    f_titulo = _fuente(58, True)
    f_seccion = _fuente(34, True)
    f_etiqueta = _fuente(26)
    f_chico = _fuente(22)

    # Cabecera
    d.rectangle((150, 120, 2330, 250), outline=NEGRO, width=3)
    d.text((200, 155), "PERU  ·  Ministerio de Salud", font=f_seccion, fill=NEGRO)
    d.rectangle((900, 140, 1560, 230), fill=NEGRO)
    d.text((940, 160), "HOJA DE REFERENCIA", font=f_titulo, fill=BLANCO)
    for i, (et, x) in enumerate((("Disa", 1700), ("Lotes", 1900), ("Numero", 2100))):
        d.rectangle((x, 140, x + 180, 230), outline=NEGRO, width=2)
        d.text((x + 10, 148), et, font=f_chico, fill=NEGRO)

    secciones = (
        (330, "1.- DATOS GENERALES"),
        (710, "2.- IDENTIFICACION DEL USUARIO"),
        (1120, "3.- RESUMEN DE HISTORIA CLINICA"),
        (2330, "4.- DATOS DE LA REFERENCIA"),
    )
    for y, texto in secciones:
        d.text((150, y - 42), texto, font=f_seccion, fill=NEGRO)
        d.line((150, y - 6, 2330, y - 6), fill=NEGRO, width=3)

    # Marcos de las secciones grandes
    d.rectangle((150, 1140, 2330, 2260), outline=NEGRO, width=2)
    d.rectangle((150, 2350, 2330, 3300), outline=NEGRO, width=2)

    # Etiqueta y linea/caja de cada campo
    for c in MAPA_CAMPOS:
        d.text((max(155, c.x - 5), c.y - 32), c.etiqueta + ":", font=f_etiqueta, fill=NEGRO)
        if c.tipo == "casilla":
            d.rectangle(c.caja, outline=NEGRO, width=3)
        elif c.tipo in {"codigo", "numero"} and c.ancho < 420:
            # Casilleros individuales, como en el formulario real
            n = max(4, min(10, c.ancho // 42))
            paso = c.ancho / n
            for k in range(n + 1):
                x = c.x + int(k * paso)
                d.line((x, c.y, x, c.y + c.alto), fill=GRIS, width=2)
            d.line((c.x, c.y, c.x + c.ancho, c.y), fill=NEGRO, width=2)
            d.line((c.x, c.y + c.alto, c.x + c.ancho, c.y + c.alto), fill=NEGRO, width=2)
        elif c.tipo == "parrafo":
            paso = c.alto / c.lineas
            for k in range(1, c.lineas + 1):
                y = c.y + int(k * paso) - 4
                d.line((c.x, y, c.x + c.ancho, y), fill=GRIS, width=2)
        else:
            d.line(
                (c.x, c.y + c.alto, c.x + c.ancho, c.y + c.alto), fill=NEGRO, width=2
            )

    # Pie: el cierre de ciclo que en la practica nunca vuelve
    d.line((150, 3180, 2330, 3180), fill=NEGRO, width=3)
    d.text(
        (170, 3195),
        "Condiciones del Paciente a la llegada al Establecimiento Destino",
        font=f_seccion,
        fill=NEGRO,
    )
    d.text(
        (170, 3400),
        "Copias:  Original SIS  ·  EE.SS. Destino (1a)  ·  EE.SS. Destino (2a)  ·  SRCR (3a copia)",
        font=f_chico,
        fill=GRIS,
    )
    return img
