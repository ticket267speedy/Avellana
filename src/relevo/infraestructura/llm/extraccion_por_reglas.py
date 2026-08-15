"""Extraccion de campos desde una transcripcion, con reglas y sin modelo.

POR QUE EXISTE ESTO
Medido sobre nuestro propio corpus: `glm-ocr` transcribe el documento entero
bien, pero NO obedece esquemas JSON. Se le piden tres claves planas y devuelve
el documento anidado con claves propias e inventadas (`DNN`, `Cellular`). Es un
transcriptor, no un modelo de seguimiento de instrucciones, y pedirle otra cosa
es pelearse con su naturaleza.

La salida es no pedirle JSON. Que haga lo que sabe —transcribir— y que la
extraccion de campos la haga esto, que es determinista y no alucina:

    imagen ──► glm-ocr ──► texto ──► ESTE MODULO ──► campos ──► VerificadorExtraccion

Cumple ademas la regla 3 de CLAUDE.md, que pedia construir el respaldo sin
modelo ANTES que cualquier proveedor. Llego tarde, pero llego.

LA IDEA QUE HACE QUE ESTO FUNCIONE
Un campo se acepta solo si se cumplen DOS condiciones independientes: que la
etiqueta coincida Y que el valor encaje en su formato. La segunda es la que
salva, porque el OCR falla de dos maneras distintas:

    "DN: 7231911"           etiqueta bien, valor de 7 digitos  -> rechazado
    "Celular: 10/11/2007"   etiqueta bien, valor que es fecha  -> rechazado

Ambos casos son reales, salidos de `hr_0001`. Sin la comprobacion de formato
los dos habrian entrado al expediente como buenos.

LO QUE ESTO NO PUEDE HACER, Y HAY QUE DECIRLO
Si el OCR lee `30889` donde decia `30389`, el valor tiene cinco digitos y pasa
el formato. Este modulo NO lo detecta y no puede: no hay nada en el valor que
delate el error. Para eso esta la doble lectura — dos modelos distintos leen la
misma imagen y el desacuerdo marca el campo. La validacion de formato y el
contraste entre modelos atacan errores diferentes, y por eso hacen falta los dos.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from relevo.dominio.objetos_valor.campo_extraido import AjusteCatalogo
from relevo.infraestructura.llm.catalogo_campos import ESTABLECIMIENTOS


def _sin_tildes(texto: str) -> str:
    """Normaliza para comparar. El OCR pierde y agrega tildes sin criterio."""
    descompuesto = unicodedata.normalize("NFD", texto.lower().strip())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _parecido(a: str, b: str) -> float:
    """Similitud en [0, 1], insensible a tildes y mayusculas."""
    return SequenceMatcher(None, _sin_tildes(a), _sin_tildes(b)).ratio()

# ─────────────────────────────────────────────────────────────────────────────
# Especificacion de campos
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ReglaCampo:
    """Como encontrar un campo en una transcripcion y como validarlo.

    `etiqueta` es tolerante a proposito: el OCR se come letras y cambia acentos.
    `DNI` aparecio como `DN` en un documento real del corpus, asi que el patron
    acepta las dos formas. Ser estricto en la etiqueta solo produce nulls.

    `formato` es lo contrario: estricto sin excepciones. Es la unica defensa
    contra un valor mal leido que viene bien etiquetado.
    """

    nombre: str
    etiqueta: str
    formato: str
    descripcion: str = ""

    catalogo: tuple[str, ...] = ()
    """Vocabulario cerrado, cuando el campo lo tiene.

    Es la tercera defensa, y ataca errores que el formato no ve. Medido: el OCR
    leyo `NISN San Borja` por `INSN San Borja`. Tiene la etiqueta correcta y
    encaja en cualquier formato de texto razonable, asi que habria entrado como
    bueno. Contra el catalogo no existe, y ahi se detiene.
    """

    umbral_catalogo: float = 0.82
    """Parecido minimo para corregir contra el catalogo.

    Por debajo se declara que no se pudo identificar, en vez de forzar la
    entrada mas cercana. Corregir `Hospital X` a `Hospital Y` porque comparten
    la palabra `Hospital` seria inventar un establecimiento.
    """

    def buscar(self, texto: str) -> tuple[str | None, str, AjusteCatalogo | None]:
        """Devuelve (valor_valido, crudo_encontrado, ajuste_si_lo_hubo).

        El crudo se conserva aunque se rechace: en la pantalla de revision, a
        una persona le sirve mucho mas ver "se leyo 7231911, tiene 7 digitos"
        que un campo vacio sin explicacion.
        """
        patron = re.compile(
            rf"{self.etiqueta}\s*[:\-]\s*(?P<valor>[^\n]+)", re.IGNORECASE
        )
        m = patron.search(texto)
        if not m:
            return None, "", None
        crudo = m.group("valor").strip()

        encaje = re.fullmatch(self.formato, crudo)
        if encaje is None:
            return None, crudo, None
        valor = encaje.group(0).strip()

        if not self.catalogo:
            return valor, crudo, None
        return self._contra_catalogo(valor, crudo)

    def _contra_catalogo(
        self, valor: str, crudo: str
    ) -> tuple[str | None, str, AjusteCatalogo | None]:
        """Ajusta el valor al vocabulario cerrado, o lo manda a revision."""
        if valor in self.catalogo:
            return valor, crudo, None

        puntuados = sorted(
            ((_parecido(valor, opcion), opcion) for opcion in self.catalogo),
            reverse=True,
        )
        mejor_puntaje, mejor = puntuados[0]
        segundo_puntaje, segundo = (
            puntuados[1] if len(puntuados) > 1 else (0.0, None)
        )

        if mejor_puntaje < self.umbral_catalogo:
            # Demasiado lejos de todo. No se inventa el mas parecido.
            return None, crudo, None

        ajuste = AjusteCatalogo(
            valor_leido=valor,
            valor_catalogo=mejor,
            # `AjusteCatalogo` razona en distancia, no en parecido.
            distancia=round((1.0 - mejor_puntaje) * 10, 3),
            segundo_candidato=segundo,
            distancia_segundo=(
                round((1.0 - segundo_puntaje) * 10, 3) if segundo else None
            ),
        )
        if ajuste.ambiguo:
            # Dos candidatos igual de cerca: el catalogo no desempata y
            # corregir seria una moneda al aire.
            return None, crudo, ajuste
        return mejor, crudo, ajuste


@dataclass(frozen=True, slots=True)
class CampoLeido:
    """Un campo extraido, con por que se acepto o se rechazo."""

    nombre: str
    valor: str | None
    crudo: str = ""
    motivo: str = ""
    ajuste: AjusteCatalogo | None = None
    """Rastro de la correccion contra catalogo, si la hubo.

    Se propaga hasta la pantalla: una correccion automatica sin constancia es
    indistinguible de una alucinacion.
    """

    @property
    def requiere_revision(self) -> bool:
        return self.valor is None

    @property
    def fue_corregido(self) -> bool:
        return self.ajuste is not None and self.valor is not None

    def explicacion(self) -> str:
        if self.fue_corregido and self.ajuste is not None:
            return (
                f"{self.nombre}: {self.valor} "
                f"(se leyo '{self.ajuste.valor_leido}', corregido contra catalogo)"
            )
        if self.valor is not None:
            return f"{self.nombre}: {self.valor}"
        if not self.crudo:
            return f"{self.nombre}: no se encontro la etiqueta en el documento"
        return f"{self.nombre}: se leyo '{self.crudo}', {self.motivo}"


# ─────────────────────────────────────────────────────────────────────────────
# El catalogo de reglas
# ─────────────────────────────────────────────────────────────────────────────

# Los formatos NO se inventan aqui: son los de `catalogo_campos.especificaciones()`,
# que a su vez salen de la Hoja de Referencia del MINSA.
REGLAS: tuple[ReglaCampo, ...] = (
    ReglaCampo(
        nombre="dni",
        # El OCR perdio la I de DNI en un caso real. Se aceptan D.N.I., DNI, DN.
        etiqueta=r"D\.?N\.?I?\.?",
        formato=r"\d{8}",
        descripcion="DNI del paciente, exactamente 8 digitos",
    ),
    ReglaCampo(
        nombre="celular",
        etiqueta=r"(?:celular|cel|tel[eé]fono|tlf)",
        formato=r"9\d{8}",
        descripcion="Movil peruano: 9 digitos empezando en 9",
    ),
    ReglaCampo(
        nombre="numero_hc",
        etiqueta=r"(?:N[°ºo]?\s*)?historia\s*cl[ií]nica",
        formato=r"\d{1,10}",
        descripcion="Numero de historia clinica",
    ),
    ReglaCampo(
        nombre="fecha_nacimiento",
        etiqueta=r"fecha\s*(?:de\s*)?nacimiento",
        formato=r"\d{2}/\d{2}/\d{4}",
        descripcion="Fecha de nacimiento en dd/mm/aaaa",
    ),
    ReglaCampo(
        nombre="apellido_paterno",
        etiqueta=r"apellido\s*paterno",
        formato=r"[A-Za-zÁÉÍÓÚÑáéíóúñ' -]{2,40}",
        descripcion="Apellido paterno",
    ),
    ReglaCampo(
        nombre="apellido_materno",
        etiqueta=r"apellido\s*materno",
        formato=r"[A-Za-zÁÉÍÓÚÑáéíóúñ' -]{2,40}",
        descripcion="Apellido materno",
    ),
    ReglaCampo(
        nombre="establecimiento_origen",
        etiqueta=r"establecimiento\s*(?:de\s*)?origen",
        formato=r".{3,60}",
        descripcion="Establecimiento que refiere",
        catalogo=ESTABLECIMIENTOS,
    ),
    ReglaCampo(
        nombre="establecimiento_destino",
        etiqueta=r"establecimiento\s*(?:de\s*)?destino",
        formato=r".{3,60}",
        descripcion="Establecimiento receptor",
        catalogo=ESTABLECIMIENTOS,
    ),
)


def _motivo_rechazo(regla: ReglaCampo, crudo: str) -> str:
    """Por que no se acepto. En castellano llano: lo lee una persona."""
    if regla.nombre == "dni" and crudo.isdigit():
        return f"tiene {len(crudo)} digitos y el DNI tiene 8"
    if regla.nombre == "celular":
        if re.search(r"\d{2}/\d{2}/\d{4}", crudo):
            return "parece una fecha, no un numero de telefono"
        return "no es un movil peruano valido (9 digitos empezando en 9)"
    if regla.catalogo and re.fullmatch(regla.formato, crudo):
        # Paso el formato pero no esta en el vocabulario cerrado.
        return "no figura en el catalogo de establecimientos"
    return f"no cumple el formato esperado ({regla.descripcion})"


@dataclass(frozen=True, slots=True)
class LecturaPorReglas:
    """El resultado de extraer una transcripcion completa."""

    campos: tuple[CampoLeido, ...] = field(default_factory=tuple)

    @property
    def valores(self) -> dict[str, str | None]:
        return {c.nombre: c.valor for c in self.campos}

    @property
    def requieren_revision(self) -> tuple[CampoLeido, ...]:
        return tuple(c for c in self.campos if c.requiere_revision)

    @property
    def tasa_captura(self) -> float:
        """Fraccion de campos que salieron con valor valido."""
        if not self.campos:
            return 0.0
        return sum(1 for c in self.campos if c.valor is not None) / len(self.campos)


def extraer_de_transcripcion(
    texto: str, reglas: tuple[ReglaCampo, ...] = REGLAS
) -> LecturaPorReglas:
    """Saca los campos de una transcripcion libre. Determinista y sin red.

    No corrige, no completa y no adivina: si el valor no encaja en su formato,
    el campo sale `None` y va a revision. Un null se revisa; un valor
    equivocado con aspecto correcto no se detecta.
    """
    leidos: list[CampoLeido] = []
    for regla in reglas:
        valor, crudo, ajuste = regla.buscar(texto)
        leidos.append(
            CampoLeido(
                nombre=regla.nombre,
                valor=valor,
                crudo=crudo,
                motivo="" if valor is not None else _motivo_rechazo(regla, crudo),
                ajuste=ajuste,
            )
        )
    return LecturaPorReglas(campos=tuple(leidos))


INSTRUCCION_TRANSCRIPCION = (
    "Transcribe TODO el texto que veas en este documento clinico, respetando "
    "las etiquetas de cada campo tal como aparecen. No corrijas la ortografia, "
    "no completes abreviaturas y no calcules nada. Si un dato no es legible, "
    "escribe la etiqueta y dejalo vacio."
)
"""Lo unico que se le pide al modelo de vision.

Deliberadamente NO se le pide JSON ni un esquema: medido sobre el corpus,
`glm-ocr` ignora el esquema pedido y devuelve su propia estructura. Pedirle lo
que sabe hacer da un resultado utilizable; pedirle lo que no sabe da `null` en
todos los campos tras cuatro minutos.
"""
