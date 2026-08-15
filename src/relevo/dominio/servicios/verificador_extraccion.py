"""El motor que impide el error silencioso.

PLAN_TECNICO — modulo de digitalizacion.

Idea central, y es la unica idea de este archivo:

    NO HAY QUE LEER MEJOR. HAY QUE HACER IMPOSIBLE ESTAR MAL EN SILENCIO.

Un modelo de vision leyendo una Hoja de Referencia manuscrita se va a equivocar.
Es inevitable. Lo que NO es inevitable es que el error pase inadvertido, porque
casi todos los campos de ese formulario tienen estructura conocida:

  · Formato   — un DNI tiene 8 digitos; una fecha es DD/MM/AAAA; un celular
                peruano tiene 9 y empieza en 9.
  · Catalogo  — un CIE-10 tiene que existir en el listado oficial; un
                establecimiento tiene que estar en el directorio; la
                especialidad de destino sale de una lista de siete.
  · Coherencia— la edad tiene que cuadrar con la fecha de nacimiento; en un
                grupo de casillas excluyentes hay exactamente una marcada.

Cada una de esas tres capas convierte un error de lectura en un error DETECTADO.
Y lo que se detecta va a una persona, que revisa tres campos amarillos en vez de
tipear cuarenta.

De ahi sale la metrica que el sistema puede prometer y demostrar:

    tasa de error no detectado = campos mal leidos que quedaron en VERDE
                                 --------------------------------------
                                            campos totales

El objetivo de esa metrica es CERO. La exactitud bruta puede ser 90% y el
sistema sigue siendo utilizable, siempre que el 10% restante este en amarillo.

Sin dependencias externas: distancia de edicion propia, nada de rapidfuzz.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from relevo.dominio.objetos_valor.campo_extraido import (
    AjusteCatalogo,
    CampoExtraido,
    EstadoCampo,
    Motivo,
)

# ─────────────────────────────────────────────────────────────────────────────
# Distancia de edicion
# ─────────────────────────────────────────────────────────────────────────────


def normalizar(texto: str) -> str:
    """Minusculas, sin tildes, sin espacios de mas.

    Se comparan formas normalizadas porque el modelo va a leer 'Cardiologia' o
    'CARDIOLOGÍA' o 'cardiologia' y las tres son el mismo valor de catalogo.
    """
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


# Pares que un lector optico confunde de verdad. Un modelo que lee "E84.O" casi
# nunca quiso decir "E84.1": quiso decir "E84.0" y confundio cero con O
# mayuscula. Cobrar lo mismo por las dos sustituciones tira esa informacion a la
# basura y deja ambiguo lo que no lo es.
#
# Fuente: confusiones clasicas de OCR/HTR sobre caracteres latinos y digitos.
# TODO: ampliar con las que aparezcan al medir contra el corpus sintetico.
CONFUSIONES_OCR: dict[frozenset[str], float] = {
    frozenset("0O"): 0.3,
    frozenset("0D"): 0.5,
    frozenset("0Q"): 0.5,
    frozenset("1I"): 0.3,
    frozenset("1L"): 0.4,
    frozenset("17"): 0.5,
    frozenset("5S"): 0.3,
    frozenset("8B"): 0.3,
    frozenset("2Z"): 0.3,
    frozenset("6G"): 0.4,
    frozenset("9Q"): 0.5,
    frozenset("UV"): 0.5,
    frozenset("CE"): 0.6,
    frozenset("NM"): 0.6,
}

COSTO_SUSTITUCION = 1.0


def _costo_sustitucion(a: str, b: str) -> float:
    """Cuanto cuesta cambiar `a` por `b`. Barato si es confusion tipica de lectura."""
    if a == b:
        return 0.0
    return CONFUSIONES_OCR.get(frozenset((a.upper(), b.upper())), COSTO_SUSTITUCION)


def distancia_edicion(a: str, b: str) -> float:
    """Levenshtein PONDERADO por confusiones tipicas de lectura optica.

    Igual que el Levenshtein clasico salvo en el costo de sustitucion: las
    parejas de `CONFUSIONES_OCR` cuestan una fraccion en vez de 1. Eso hace que
    el catalogo desempate donde la distancia plana se quedaba ambigua:

        "E84.O" -> "E84.0"  cuesta 0.3   (cero confundido con O)
        "E84.O" -> "E84.1"  cuesta 1.0   (nada que ver)

    Con distancia plana las dos cuestan 1 y el campo se manda a revision sin
    necesidad. Con esta, se corrige solo y se deja constancia.

    Dos filas, O(len(a)*len(b)) tiempo y O(len(b)) memoria. Sin dependencias.
    """
    if a == b:
        return 0.0
    if not a:
        return float(len(b))
    if not b:
        return float(len(a))

    previa: list[float] = [float(j) for j in range(len(b) + 1)]
    for i, ca in enumerate(a, start=1):
        actual: list[float] = [float(i)]
        for j, cb in enumerate(b, start=1):
            actual.append(
                min(
                    previa[j] + 1.0,                              # borrado
                    actual[j - 1] + 1.0,                          # insercion
                    previa[j - 1] + _costo_sustitucion(ca, cb),   # sustitucion
                )
            )
        previa = actual
    return previa[-1]


# ─────────────────────────────────────────────────────────────────────────────
# Especificacion de un campo
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EspecificacionCampo:
    """Todo lo que se sabe de antemano sobre un campo del formulario.

    Cuanto mas se declara aqui, mas errores se detectan solos. Es el archivo
    donde vive el conocimiento del dominio, y por eso se carga de YAML: lo puede
    editar quien conoce el formulario, no quien programa.
    """

    nombre: str
    etiqueta: str
    obligatorio: bool = True

    patron: str | None = None
    """Expresion regular que el valor debe cumplir tras normalizar espacios."""

    descripcion_formato: str = ""
    """Como se le explica el formato a una persona: 'ocho digitos'."""

    catalogo: tuple[str, ...] = ()
    """Vocabulario cerrado. Si esta, el valor se ajusta al vecino mas cercano."""

    distancia_maxima: float = 2.0
    """Hasta cuantas ediciones se acepta como correccion automatica.

    Por encima, el valor leido esta demasiado lejos de todo y se marca en rojo:
    corregir a ciegas seria inventar. Se escala con la longitud en
    `_ajustar_a_catalogo`.
    """

    longitud_minima: int = 1
    umbral_confianza: float = 0.75
    """Debajo de esto, ambar aunque formato y catalogo esten bien.

    TODO: calibrar empiricamente contra el corpus sintetico, por campo.
    Hoy es provisional y es el mismo para todos, que casi seguro esta mal.
    """


# ─────────────────────────────────────────────────────────────────────────────
# Validaciones cruzadas
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ReglaCruzada:
    """Coherencia entre campos. La capa que mas errores atrapa por lo barata que es.

    Un modelo puede leer mal la edad, o mal la fecha de nacimiento, pero es muy
    improbable que se equivoque en las dos de forma que sigan cuadrando entre si.
    """

    nombre: str
    campos: tuple[str, ...]
    descripcion: str
    predicado: Callable[[Mapping[str, str | None]], bool]
    """Devuelve True si los campos son coherentes. Si algun campo implicado
    falta, la regla se salta: no se puede juzgar lo que no se leyo."""


def regla_edad_coherente_con_nacimiento(
    hoy: date,
    campo_edad: str = "edad_anios",
    campo_nacimiento: str = "fecha_nacimiento",
    tolerancia_anios: int = 1,
) -> ReglaCruzada:
    """La edad escrita debe cuadrar con la fecha de nacimiento escrita."""

    def predicado(valores: Mapping[str, str | None]) -> bool:
        crudo_edad = valores.get(campo_edad)
        crudo_nac = valores.get(campo_nacimiento)
        if not crudo_edad or not crudo_nac:
            return True
        try:
            edad = int(crudo_edad.strip())
            d, m, a = (int(p) for p in re.split(r"[/\-.]", crudo_nac.strip()))
            nacimiento = date(a, m, d)
        except (ValueError, TypeError):
            return True  # el formato ya lo juzga otra capa
        calculada = (
            hoy.year
            - nacimiento.year
            - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
        )
        return abs(calculada - edad) <= tolerancia_anios

    return ReglaCruzada(
        nombre="edad_vs_nacimiento",
        campos=(campo_edad, campo_nacimiento),
        descripcion="la edad escrita no cuadra con la fecha de nacimiento",
        predicado=predicado,
    )


def regla_exclusividad(nombre: str, campos: Sequence[str]) -> ReglaCruzada:
    """En un grupo de casillas excluyentes hay exactamente una marcada."""

    def predicado(valores: Mapping[str, str | None]) -> bool:
        marcados = [c for c in campos if (valores.get(c) or "").strip().lower() in {"x", "si", "1", "true", "marcado"}]
        return len(marcados) == 1

    return ReglaCruzada(
        nombre=nombre,
        campos=tuple(campos),
        descripcion=f"debe haber exactamente una opcion marcada en {nombre}",
        predicado=predicado,
    )


# ─────────────────────────────────────────────────────────────────────────────
# El verificador
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ReporteVerificacion:
    """El resultado de verificar un documento completo."""

    campos: Mapping[str, CampoExtraido]

    @property
    def verdes(self) -> tuple[CampoExtraido, ...]:
        return tuple(c for c in self.campos.values() if c.estado is EstadoCampo.VERDE)

    @property
    def ambares(self) -> tuple[CampoExtraido, ...]:
        return tuple(c for c in self.campos.values() if c.estado is EstadoCampo.AMBAR)

    @property
    def rojos(self) -> tuple[CampoExtraido, ...]:
        return tuple(c for c in self.campos.values() if c.estado is EstadoCampo.ROJO)

    @property
    def requieren_revision(self) -> tuple[CampoExtraido, ...]:
        """Lo unico que una persona tiene que mirar. El resto ya esta."""
        return tuple(
            c for c in self.campos.values() if c.estado.requiere_persona
        )

    @property
    def corregidos_por_catalogo(self) -> tuple[CampoExtraido, ...]:
        return tuple(c for c in self.campos.values() if c.fue_corregido)

    @property
    def utilizable(self) -> bool:
        """No hay obligatorios en rojo. Con ambares el documento avanza tras revision."""
        return not any(c.obligatorio for c in self.rojos)

    def resumen(self) -> str:
        return (
            f"{len(self.verdes)} validados · "
            f"{len(self.ambares)} a revisar · "
            f"{len(self.rojos)} no legibles · "
            f"{len(self.corregidos_por_catalogo)} corregidos por catalogo"
        )


@dataclass(frozen=True, slots=True)
class Metricas:
    """Lo que se mide contra el corpus con verdad conocida."""

    total: int
    correctos: int
    revisados: int
    errores_no_detectados: int
    """Campos mal leidos que quedaron en VERDE. LA metrica. Objetivo: cero."""

    errores_detectados: int

    @property
    def exactitud_bruta(self) -> float:
        return self.correctos / self.total if self.total else 0.0

    @property
    def tasa_error_no_detectado(self) -> float:
        return self.errores_no_detectados / self.total if self.total else 0.0

    @property
    def carga_de_revision(self) -> float:
        """Fraccion de campos que una persona tiene que mirar."""
        return self.revisados / self.total if self.total else 0.0

    def __str__(self) -> str:
        return (
            f"exactitud bruta {self.exactitud_bruta:.1%} · "
            f"error NO detectado {self.tasa_error_no_detectado:.2%} · "
            f"revision humana {self.carga_de_revision:.1%}"
        )


@dataclass(frozen=True, slots=True)
class VerificadorExtraccion:
    """Convierte lecturas crudas en campos con estado justificado.

    No lee nada: recibe lo que el modelo ya leyo. Es aritmetica y reglas — se
    prueba sin imagenes, sin red y sin modelo.
    """

    especificaciones: Mapping[str, EspecificacionCampo]
    reglas_cruzadas: tuple[ReglaCruzada, ...] = ()

    def verificar(
        self,
        lecturas: Mapping[str, str | None],
        confianzas: Mapping[str, float] | None = None,
        segunda_lectura: Mapping[str, str | None] | None = None,
    ) -> ReporteVerificacion:
        """Verifica un documento completo.

        `segunda_lectura` permite pasar la salida de un SEGUNDO modelo sobre la
        misma imagen. Donde las dos lecturas discrepan, el campo va a ambar
        aunque ambas sean formalmente validas. Es la forma mas barata de obtener
        una senal de confianza cuando el modelo no expone probabilidades.
        """
        confianzas = confianzas or {}
        resultado: dict[str, CampoExtraido] = {}

        for nombre, spec in self.especificaciones.items():
            resultado[nombre] = self._verificar_campo(
                spec,
                lecturas.get(nombre),
                confianzas.get(nombre),
                (segunda_lectura or {}).get(nombre) if segunda_lectura else None,
            )

        resultado = self._aplicar_reglas_cruzadas(resultado, lecturas)
        return ReporteVerificacion(campos=resultado)

    # ── un campo ─────────────────────────────────────────────────────────────

    def _verificar_campo(
        self,
        spec: EspecificacionCampo,
        crudo: str | None,
        confianza: float | None,
        crudo_segundo: str | None,
    ) -> CampoExtraido:
        limpio = (crudo or "").strip()

        # 1 · Ausencia. No se inventa nada.
        if not limpio:
            return CampoExtraido(
                nombre=spec.nombre,
                valor_crudo=crudo,
                valor=None,
                estado=EstadoCampo.ROJO if spec.obligatorio else EstadoCampo.AMBAR,
                motivos=(Motivo.VACIO,),
                confianza_modelo=confianza,
                obligatorio=spec.obligatorio,
            )

        motivos: list[Motivo] = []
        valor = " ".join(limpio.split())
        ajuste: AjusteCatalogo | None = None
        estado = EstadoCampo.VERDE

        # 2 · Catalogo cerrado. Aqui es donde se gana casi todo.
        if spec.catalogo:
            ajuste = self._ajustar_a_catalogo(valor, spec)
            if ajuste is None:
                return CampoExtraido(
                    nombre=spec.nombre,
                    valor_crudo=crudo,
                    valor=None,
                    estado=EstadoCampo.ROJO,
                    motivos=(Motivo.FUERA_DE_CATALOGO,),
                    confianza_modelo=confianza,
                    obligatorio=spec.obligatorio,
                )
            valor = ajuste.valor_catalogo
            if ajuste.ambiguo:
                motivos.append(Motivo.CATALOGO_AMBIGUO)
                estado = EstadoCampo.AMBAR
            elif ajuste.distancia > 0:
                motivos.append(Motivo.AJUSTADO_A_CATALOGO)

        # 3 · Formato. Solo si no hubo catalogo: el catalogo ya garantiza forma.
        elif spec.patron is not None:
            if not re.fullmatch(spec.patron, valor):
                return CampoExtraido(
                    nombre=spec.nombre,
                    valor_crudo=crudo,
                    valor=None,
                    estado=EstadoCampo.ROJO,
                    motivos=(Motivo.FORMATO_INVALIDO,),
                    confianza_modelo=confianza,
                    obligatorio=spec.obligatorio,
                )

        if len(valor) < spec.longitud_minima:
            motivos.append(Motivo.NO_LEGIBLE)
            estado = EstadoCampo.AMBAR

        # 4 · Desacuerdo entre dos lecturas independientes.
        if crudo_segundo is not None:
            if normalizar(crudo_segundo) != normalizar(valor) and normalizar(
                crudo_segundo
            ) != normalizar(limpio):
                motivos.append(Motivo.DESACUERDO_ENTRE_MODELOS)
                estado = EstadoCampo.AMBAR

        # 5 · Confianza declarada por el modelo. Nunca mejora el estado.
        if confianza is not None and confianza < spec.umbral_confianza:
            motivos.append(Motivo.CONFIANZA_BAJA)
            estado = EstadoCampo.AMBAR

        if not motivos:
            motivos.append(Motivo.VALIDADO)

        return CampoExtraido(
            nombre=spec.nombre,
            valor_crudo=crudo,
            valor=valor,
            estado=estado,
            motivos=tuple(motivos),
            confianza_modelo=confianza,
            ajuste=ajuste,
            obligatorio=spec.obligatorio,
        )

    def _ajustar_a_catalogo(
        self, valor: str, spec: EspecificacionCampo
    ) -> AjusteCatalogo | None:
        """Vecino mas cercano dentro del vocabulario cerrado.

        El umbral escala con la longitud: en 'E84.0' (5 caracteres) dos ediciones
        ya es otro codigo distinto, mientras que en 'Hospital Nacional Docente
        Madre Nino San Bartolome' dos ediciones es una tilde y una letra.
        """
        objetivo = normalizar(valor)
        distancias = sorted(
            ((distancia_edicion(objetivo, normalizar(c)), c) for c in spec.catalogo),
            key=lambda par: (par[0], par[1]),
        )
        mejor_d, mejor = distancias[0]

        tope = min(spec.distancia_maxima, max(1.0, len(objetivo) / 3.0))
        if mejor_d > tope:
            return None

        segundo, d_segundo = (None, None)
        if len(distancias) > 1:
            d2, c2 = distancias[1]
            if d2 <= tope:
                segundo, d_segundo = c2, d2

        return AjusteCatalogo(
            valor_leido=valor,
            valor_catalogo=mejor,
            distancia=mejor_d,
            segundo_candidato=segundo,
            distancia_segundo=d_segundo,
        )

    # ── coherencia entre campos ──────────────────────────────────────────────

    def _aplicar_reglas_cruzadas(
        self,
        campos: dict[str, CampoExtraido],
        lecturas: Mapping[str, str | None],
    ) -> dict[str, CampoExtraido]:
        for regla in self.reglas_cruzadas:
            if regla.predicado(lecturas):
                continue
            for nombre in regla.campos:
                actual = campos.get(nombre)
                if actual is None or actual.estado is EstadoCampo.ROJO:
                    continue
                campos[nombre] = CampoExtraido(
                    nombre=actual.nombre,
                    valor_crudo=actual.valor_crudo,
                    valor=actual.valor,
                    estado=EstadoCampo.AMBAR,
                    motivos=tuple(
                        m for m in actual.motivos if m is not Motivo.VALIDADO
                    )
                    + (Motivo.INCONSISTENTE_CON_OTRO_CAMPO,),
                    confianza_modelo=actual.confianza_modelo,
                    ajuste=actual.ajuste,
                    obligatorio=actual.obligatorio,
                )
        return campos


# ─────────────────────────────────────────────────────────────────────────────
# Medicion contra verdad conocida
# ─────────────────────────────────────────────────────────────────────────────


def medir(
    reporte: ReporteVerificacion, verdad: Mapping[str, str | None]
) -> Metricas:
    """Compara el reporte contra lo que el documento realmente decia.

    Solo es posible porque el corpus es sintetico: nosotros renderizamos el
    formulario, asi que conocemos cada campo sin que nadie transcriba nada.

    El numero que importa NO es la exactitud. Es `tasa_error_no_detectado`:
    campos mal leidos que el sistema dejo pasar en verde. Un sistema con 88% de
    exactitud y 0% de error no detectado es utilizable en un hospital. Uno con
    97% de exactitud y 3% de error no detectado, no.
    """
    total = correctos = revisados = no_detectados = detectados = 0

    for nombre, campo in reporte.campos.items():
        esperado = verdad.get(nombre)
        total += 1
        acierta = normalizar(campo.valor or "") == normalizar(esperado or "")
        if acierta:
            correctos += 1
        if campo.estado.requiere_persona:
            revisados += 1
            if not acierta:
                detectados += 1
        elif not acierta:
            no_detectados += 1

    return Metricas(
        total=total,
        correctos=correctos,
        revisados=revisados,
        errores_no_detectados=no_detectados,
        errores_detectados=detectados,
    )
