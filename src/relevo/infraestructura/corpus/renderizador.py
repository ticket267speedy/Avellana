"""Escribe datos de un paciente sintetico sobre la plantilla, con letra distinta cada vez.

POR QUE ESTO EXISTE
El hospital no puede entregarnos Hojas de Referencia llenas: son datos
personales y la negativa es correcta. Sin muestras no se puede construir ni
—sobre todo— MEDIR un sistema de digitalizacion.

La salida es generarlas nosotros. Y sale mejor que pedirlas prestadas, porque:

  · No hay dato personal de nadie. Se puede publicar y versionar.
  · La VERDAD viene gratis: nosotros escribimos cada campo, asi que sabemos
    exactamente que dice sin que nadie transcriba nada a mano. Eso convierte la
    evaluacion en una funcion, no en una tarde de trabajo.
  · Se generan mil, no cinco.

LIMITACION, Y HAY QUE DECIRLA EN EL PITCH
Letra renderizada con fuente es mas regular que letra humana: no varia dentro de
una misma palabra, no arrastra el trazo ni se sale del renglon igual. La
exactitud medida sobre este corpus es OPTIMISTA respecto de la letra real.

Lo que el corpus SI valida honestamente es el pipeline completo, la deteccion de
errores y la calibracion de umbrales — que es donde esta el aporte.
"""

from __future__ import annotations

import random
import textwrap
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from relevo.infraestructura.corpus.plantilla import (
    MAPA_CAMPOS,
    Campo,
    dibujar_plantilla_base,
)

# Tinta: no todo el mundo escribe con el mismo boligrafo ni aprieta igual.
TINTAS = (
    (24, 34, 88),    # azul
    (12, 22, 66),    # azul oscuro
    (28, 28, 28),    # negro
    (55, 55, 60),    # negro gastado
    (18, 52, 30),    # verde, poco comun pero existe
)


@dataclass(frozen=True, slots=True)
class EstiloEscritura:
    """Como escribe UNA persona. Se sortea una vez por formulario.

    Un mismo formulario lo llena una sola persona: la fuente, la tinta y la
    inclinacion tienen que ser consistentes dentro de la hoja y distintas entre
    hojas. Sortearlas por campo produciria formularios imposibles que el modelo
    nunca vera en la realidad.
    """

    fuente: Path
    tinta: tuple[int, int, int]
    escala: float
    """Multiplicador del tamano base. Hay gente de letra grande y de letra chica."""

    inclinacion: float
    """Grados. Positivo inclina a la derecha."""

    jitter_linea: int
    """Cuanto se desvia verticalmente del renglon, en pixeles."""

    presion: float
    """0.6 = trazo claro, 1.0 = trazo marcado."""

    @staticmethod
    def sortear(rnd: random.Random, fuentes: list[Path]) -> EstiloEscritura:
        return EstiloEscritura(
            fuente=rnd.choice(fuentes),
            tinta=rnd.choice(TINTAS),
            escala=rnd.uniform(0.82, 1.18),
            inclinacion=rnd.uniform(-3.0, 3.5),
            jitter_linea=rnd.randint(2, 7),
            presion=rnd.uniform(0.62, 1.0),
        )


def _aplicar_presion(capa: Image.Image, presion: float) -> Image.Image:
    """Simula cuanta tinta deja el boligrafo."""
    alfa = capa.getchannel("A").point(lambda v: int(v * presion))
    capa.putalpha(alfa)
    return capa


def _escribir(
    fondo: Image.Image,
    texto: str,
    campo: Campo,
    estilo: EstiloEscritura,
    rnd: random.Random,
) -> None:
    """Escribe un texto dentro de la caja de un campo, con desprolijidad humana.

    Cada linea se dibuja en su propia capa transparente, se rota unos grados y
    se pega con desplazamiento aleatorio. Rotar linea por linea (y no la hoja
    entera) es lo que produce el aspecto de renglon torcido en vez de pagina
    torcida.
    """
    if not texto:
        return

    alto_linea = campo.alto / campo.lineas
    tam = max(18, int(alto_linea * 0.62 * estilo.escala))
    fuente = ImageFont.truetype(str(estilo.fuente), tam)

    if campo.lineas > 1:
        # Cuantos caracteres entran por renglon, medido con la fuente real
        ancho_char = max(1.0, fuente.getlength("n"))
        por_linea = max(10, int(campo.ancho / ancho_char))
        lineas = textwrap.wrap(texto, width=por_linea)[: campo.lineas]
    else:
        lineas = [texto]

    for i, linea in enumerate(lineas):
        capa = Image.new("RGBA", (campo.ancho + 260, int(alto_linea) + 90), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.text((14, 8), linea, font=fuente, fill=(*estilo.tinta, 255))

        capa = _aplicar_presion(capa, estilo.presion)
        capa = capa.rotate(
            estilo.inclinacion + rnd.uniform(-0.7, 0.7),
            resample=Image.Resampling.BICUBIC,
            expand=False,
        )

        # La escritura tiende a montarse sobre el renglon, no a flotar encima
        base_y = campo.y + int(i * alto_linea) + int(alto_linea * 0.10)
        dx = rnd.randint(-3, 10)
        dy = rnd.randint(-estilo.jitter_linea, estilo.jitter_linea)
        fondo.paste(capa, (campo.x + dx - 14, base_y + dy - 8), capa)


def _marcar_casilla(
    fondo: Image.Image, campo: Campo, estilo: EstiloEscritura, rnd: random.Random
) -> None:
    """Una equis a mano: dos trazos que no se cruzan exactamente en el centro."""
    d = ImageDraw.Draw(fondo)
    x0, y0, x1, y1 = campo.caja
    m = 8
    grosor = max(2, int(4 * estilo.presion))
    for _ in range(2):
        d.line(
            (
                x0 + m + rnd.randint(-4, 4),
                y0 + m + rnd.randint(-4, 4),
                x1 - m + rnd.randint(-4, 4),
                y1 - m + rnd.randint(-4, 4),
            ),
            fill=estilo.tinta,
            width=grosor,
        )
        x0, x1 = x1, x0  # el segundo trazo va al reves


def renderizar_formulario(
    valores: dict[str, str],
    fuentes: list[Path],
    semilla: int,
    plantilla: Image.Image | None = None,
) -> tuple[Image.Image, dict[str, str]]:
    """Rellena la plantilla con `valores` y devuelve (imagen, verdad).

    La verdad devuelta es exactamente lo que se escribio, campo por campo. No es
    una anotacion: es el insumo. Por eso el corpus no necesita etiquetadores.
    """
    rnd = random.Random(semilla)
    fondo = (plantilla or dibujar_plantilla_base()).copy()
    estilo = EstiloEscritura.sortear(rnd, fuentes)
    verdad: dict[str, str] = {}

    for campo in MAPA_CAMPOS:
        valor = valores.get(campo.nombre, "")
        if not valor:
            continue
        if campo.tipo == "casilla":
            _marcar_casilla(fondo, campo, estilo, rnd)
        else:
            _escribir(fondo, valor, campo, estilo, rnd)
        verdad[campo.nombre] = valor

    return fondo, verdad
