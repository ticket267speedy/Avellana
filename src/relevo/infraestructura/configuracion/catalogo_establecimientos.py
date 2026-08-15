"""Catalogo nacional de establecimientos de salud, desde RENIPRESS.

DE DONDE SALE Y POR QUE IMPORTA
`config/renipress_referencia.csv` es un recorte del Registro Nacional de IPRESS
que publica SUSALUD en la Plataforma Nacional de Datos Abiertos del Estado
(datosabiertos.gob.pe, licencia Open Data Commons Attribution). Es dato publico
y descargable: no hace falta pedirselo a nadie.

Del registro completo —26 787 establecimientos activos— se conservan los 12 794
que pueden emitir o recibir una derivacion: hospitales, institutos, centros de
salud, policlinicos y puestos de salud. Se descartan servicios de apoyo
(laboratorio, imagenes, optica, protesis dental, traslados), que no emiten
Hojas de Referencia de un paciente cronico y solo multiplicarian los falsos
parecidos al buscar.

POR QUE UN CATALOGO NACIONAL Y NO UNA LISTA A MANO
Un paciente del INSN San Borja puede venir referido desde una posta de Ucayali
o desde un hospital regional del Cusco. Una lista escrita a mano con los diez
establecimientos que se nos ocurran obliga a marcar "Otro" en la mayoria de los
casos reales, y "Otro" es texto libre — que es exactamente lo que ensucia una
base de datos.

DEFECTO CONOCIDO DEL ORIGEN
86 registros del archivo de SUSALUD traen la enie corrompida: dice
"INSTITUTO NACIONAL DE SALUD NI?O SAN BORJA". El defecto viene del propio
archivo publicado, no de nuestra conversion. Por eso la normalizacion trata el
signo de interrogacion como un caracter mas a ignorar al comparar.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
RUTA_CATALOGO = RAIZ_PROYECTO / "config" / "renipress_referencia.csv"

# Codigos que conviene tener a mano: son los dos INSN.
COD_INSN_SAN_BORJA = "00016918"
COD_INSN_BRENA = "00006216"

# Palabras que aparecen en medio nombre del catalogo: no distinguen nada y no
# deben confundirse con una sigla al interpretar la busqueda.
_PALABRAS_COMUNES = frozenset(
    {
        "hospital", "centro", "salud", "clinica", "puesto", "instituto",
        "nacional", "regional", "policlinico", "medico", "medicos", "san",
        "santa", "del", "las", "los", "dr", "de", "la", "el",
    }
)


@dataclass(frozen=True, slots=True)
class Establecimiento:
    codigo: str
    nombre: str
    clasificacion: str
    departamento: str
    provincia: str
    distrito: str
    categoria: str
    institucion: str

    @property
    def etiqueta(self) -> str:
        """Como se muestra al usuario. Incluye el lugar porque hay nombres
        repetidos en departamentos distintos: 'SAN BORJA' es un policlinico en
        Lima y podria ser otra cosa en otra region."""
        lugar = ", ".join(p for p in (self.distrito, self.departamento) if p)
        return f"{self.nombre} ({lugar})" if lugar else self.nombre


_INTERROGACION_ENTRE_LETRAS = re.compile(r"(?<=[A-Za-z])\?(?=[A-Za-z])")


def reparar_enie(texto: str) -> str:
    """Repara la enie que SUSALUD publico corrompida.

    86 registros del archivo de origen traen '?' donde iba 'Ñ'. Se repara AL
    CARGAR y no al comparar, por dos razones: el nombre se muestra en pantalla y
    debe verse bien, y arreglar el dato una vez es mas robusto que recordar
    normalizarlo en cada sitio donde se compare.

    Solo se toca el '?' que esta ENTRE letras. Un '?' suelto o al final podria
    ser otra cosa, y ahi no hay nada que suponer.
    """
    return _INTERROGACION_ENTRE_LETRAS.sub("Ñ", texto)


def _normalizar(texto: str) -> str:
    """Para comparar: sin tildes, sin mayusculas, sin puntuacion."""
    descompuesto = unicodedata.normalize("NFD", texto.lower().strip())
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", sin_tildes).strip()


def _sigla(nombre: str) -> str:
    """Sigla a partir de las iniciales de las palabras con contenido.

    'INSTITUTO NACIONAL DE SALUD NIÑO SAN BORJA' -> 'INSNSB'

    Existe porque los formularios NO escriben el nombre oficial: escriben
    'INSN San Borja'. Sin esto, buscar por la sigla que usa todo el mundo no
    encuentra nada, que es como no tener catalogo.
    """
    vacias = {"de", "del", "la", "las", "el", "los", "y", "en", "para"}
    palabras = [p for p in _normalizar(nombre).split() if p not in vacias]
    return "".join(p[0] for p in palabras)


@lru_cache(maxsize=1)
def cargar_establecimientos() -> tuple[Establecimiento, ...]:
    """Lee el catalogo una sola vez. Devuelve vacio si el archivo no esta.

    Vacio y no excepcion: el sistema tiene que arrancar sin el catalogo, igual
    que arranca sin modelo. La interfaz cae entonces a texto libre marcado como
    pendiente de conciliar.
    """
    if not RUTA_CATALOGO.exists():
        return ()
    with RUTA_CATALOGO.open(encoding="utf-8", newline="") as f:
        return tuple(
            Establecimiento(
                codigo=fila["COD_IPRESS"],
                nombre=reparar_enie(fila["NOMBRE"]),
                clasificacion=fila["CLASIFICACION"],
                # La enie corrompida tambien afecta a los lugares: 'BRE?A'.
                departamento=reparar_enie(fila["DEPARTAMENTO"]),
                provincia=reparar_enie(fila["PROVINCIA"]),
                distrito=reparar_enie(fila["DISTRITO"]),
                categoria=fila["CATEGORIA"],
                institucion=fila["INSTITUCION"],
            )
            for fila in csv.DictReader(f)
        )


def buscar(consulta: str, limite: int = 15) -> tuple[Establecimiento, ...]:
    """Los establecimientos que mejor encajan con lo que se escribio.

    Primero los que contienen literalmente el texto —que es lo que espera quien
    escribe— y despues los parecidos, para tolerar erratas del OCR y de quien
    teclea.
    """
    catalogo = cargar_establecimientos()
    q = _normalizar(consulta)
    if not q or not catalogo:
        return ()

    # La consulta suele mezclar sigla y nombre: "INSN San Borja". Se separa la
    # parte que parece sigla del resto, para poder exigir las dos cosas.
    partes = q.split()
    posible_sigla = next((p for p in partes if len(p) >= 3 and p not in _PALABRAS_COMUNES), "")
    resto_consulta = " ".join(p for p in partes if p != posible_sigla)

    contienen: list[Establecimiento] = []
    parecidos: list[tuple[float, Establecimiento]] = []
    for e in catalogo:
        n = _normalizar(e.nombre)
        if q in n:
            contienen.append(e)
            if len(contienen) >= limite:
                return tuple(contienen)
            continue

        # Coincidencia por sigla: "insn san borja" encuentra
        # "INSTITUTO NACIONAL DE SALUD NIÑO SAN BORJA" porque su sigla es
        # INSNSB, que empieza por INSN, y el resto del texto tambien encaja.
        sig = _sigla(e.nombre)
        if posible_sigla and sig.startswith(posible_sigla) and len(posible_sigla) >= 3:
            if not resto_consulta or resto_consulta in n:
                contienen.append(e)
                if len(contienen) >= limite:
                    return tuple(contienen)
                continue

        if len(q) >= 4:
            r = SequenceMatcher(None, q, n).ratio()
            if r >= 0.7:
                parecidos.append((r, e))

    parecidos.sort(key=lambda p: -p[0])
    resto = [e for _, e in parecidos[: limite - len(contienen)]]
    return tuple(contienen + resto)


def por_codigo(codigo: str) -> Establecimiento | None:
    for e in cargar_establecimientos():
        if e.codigo == codigo:
            return e
    return None


def existe_en_catalogo(nombre: str) -> bool:
    """True si el nombre coincide exactamente con alguno del registro."""
    n = _normalizar(nombre)
    return any(_normalizar(e.nombre) == n for e in cargar_establecimientos())
