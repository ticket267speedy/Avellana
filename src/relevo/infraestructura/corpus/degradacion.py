"""Convierte un render limpio en algo que parece una foto de celular.

POR QUE
Nadie va a escanear las Hojas de Referencia en un escaner plano. Segun el propio
INSN, el flujo es enviar los documentos ESCANEADOS por correo, y en la practica
eso significa una foto tomada con el telefono, torcida, con sombra y comprimida.

Si el corpus solo tiene renders perfectos, el pipeline se calibra contra un
escenario que no existe y el dia de la demo falla. Las degradaciones de aqui son
las que de verdad rompen la lectura:

  perspectiva  — la hoja nunca esta paralela al sensor
  sombra       — la mano o el cuerpo tapan parte de la hoja
  desenfoque   — enfoque en el centro, bordes blandos
  ruido ISO    — luz de interior de hospital
  JPEG         — WhatsApp y el correo recomprimen sin piedad

La perspectiva ademas es la que justifica el paso de rectificacion con RANSAC:
sin distorsion no haria falta homografia y el recorte por plantilla seria
trivial.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


@dataclass(frozen=True, slots=True)
class Degradacion:
    """Que tan maltratada esta la imagen. Se sortea por foto."""

    perspectiva: float = 0.02
    """Fraccion del ancho que se desplaza cada esquina."""

    rotacion: float = 0.0
    desenfoque: float = 0.8
    sombra: float = 0.25
    """0 = sin sombra, 1 = mitad de la hoja a oscuras."""

    ruido: float = 4.0
    calidad_jpeg: int = 72
    brillo: float = 1.0
    contraste: float = 1.0

    @staticmethod
    def limpia() -> Degradacion:
        """Escaneo de verdad, con escaner. El caso facil."""
        return Degradacion(
            perspectiva=0.0, rotacion=0.3, desenfoque=0.3, sombra=0.0,
            ruido=1.5, calidad_jpeg=92,
        )

    @staticmethod
    def foto_celular(rnd: random.Random) -> Degradacion:
        """El caso real: alguien fotografia la hoja sobre un escritorio."""
        return Degradacion(
            perspectiva=rnd.uniform(0.010, 0.045),
            rotacion=rnd.uniform(-3.5, 3.5),
            desenfoque=rnd.uniform(0.6, 2.0),
            sombra=rnd.uniform(0.10, 0.45),
            ruido=rnd.uniform(3.0, 11.0),
            calidad_jpeg=rnd.randint(48, 82),
            brillo=rnd.uniform(0.82, 1.14),
            contraste=rnd.uniform(0.86, 1.12),
        )

    @staticmethod
    def fotocopia(rnd: random.Random) -> Degradacion:
        """Copia de copia: alto contraste, trazo comido, mucho grano."""
        return Degradacion(
            perspectiva=rnd.uniform(0.0, 0.012),
            rotacion=rnd.uniform(-1.5, 1.5),
            desenfoque=rnd.uniform(0.9, 1.8),
            sombra=0.0,
            ruido=rnd.uniform(8.0, 16.0),
            calidad_jpeg=rnd.randint(40, 65),
            brillo=rnd.uniform(1.02, 1.20),
            contraste=rnd.uniform(1.20, 1.55),
        )


def _perspectiva(img: Image.Image, k: float, rnd: random.Random) -> Image.Image:
    """Homografia aleatoria suave. Es lo que despues hay que deshacer con RANSAC."""
    if k <= 0:
        return img
    w, h = img.size
    d = k * w
    origen = [(0, 0), (w, 0), (w, h), (0, h)]
    destino = [
        (rnd.uniform(0, d), rnd.uniform(0, d)),
        (w - rnd.uniform(0, d), rnd.uniform(0, d)),
        (w - rnd.uniform(0, d), h - rnd.uniform(0, d)),
        (rnd.uniform(0, d), h - rnd.uniform(0, d)),
    ]
    # Resolver los 8 coeficientes de la homografia por minimos cuadrados
    A, B = [], []
    for (xd, yd), (xo, yo) in zip(destino, origen):
        A.append([xd, yd, 1, 0, 0, 0, -xo * xd, -xo * yd])
        A.append([0, 0, 0, xd, yd, 1, -yo * xd, -yo * yd])
        B += [xo, yo]
    coef = np.linalg.solve(np.array(A, dtype=float), np.array(B, dtype=float))
    return img.transform(
        (w, h), Image.Transform.PERSPECTIVE, tuple(coef), Image.Resampling.BICUBIC,
        fillcolor=(248, 248, 246),
    )


def _sombra(img: Image.Image, fuerza: float, rnd: random.Random) -> Image.Image:
    """Gradiente lineal en una direccion aleatoria: el cuerpo tapando la luz."""
    if fuerza <= 0:
        return img
    w, h = img.size
    xs = np.linspace(0, 1, w, dtype=np.float32)
    ys = np.linspace(0, 1, h, dtype=np.float32)
    gx, gy = np.meshgrid(xs, ys)
    ang = rnd.uniform(0, 2 * np.pi)
    g = gx * np.cos(ang) + gy * np.sin(ang)
    g = (g - g.min()) / (np.ptp(g) + 1e-6)
    mascara = (1.0 - fuerza * g)[..., None]
    arr = np.asarray(img, dtype=np.float32) * mascara
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def degradar(img: Image.Image, cfg: Degradacion, semilla: int) -> Image.Image:
    """Aplica la cadena completa. El orden importa: la compresion va al final."""
    rnd = random.Random(semilla)

    img = _perspectiva(img, cfg.perspectiva, rnd)
    if abs(cfg.rotacion) > 0.01:
        img = img.rotate(
            cfg.rotacion, resample=Image.Resampling.BICUBIC,
            fillcolor=(248, 248, 246), expand=False,
        )
    img = _sombra(img, cfg.sombra, rnd)

    if cfg.brillo != 1.0:
        img = ImageEnhance.Brightness(img).enhance(cfg.brillo)
    if cfg.contraste != 1.0:
        img = ImageEnhance.Contrast(img).enhance(cfg.contraste)
    if cfg.desenfoque > 0:
        img = img.filter(ImageFilter.GaussianBlur(cfg.desenfoque))

    if cfg.ruido > 0:
        arr = np.asarray(img, dtype=np.float32)
        arr += np.random.default_rng(semilla).normal(0, cfg.ruido, arr.shape)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # JPEG al final, como lo hace el telefono y despues el correo
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=cfg.calidad_jpeg)
    buf.seek(0)
    return Image.open(buf).convert("RGB")
