"""De donde salio un dato, dicho en un idioma que el paciente entiende.

`OrigenDato` es la CAPA DE PRESENTACION de `EstadoCampo`. No lo reemplaza: el
dominio sigue razonando en VERDE/AMBAR/ROJO —que es lo que el verificador
anti-error-silencioso produce— y esto traduce para la interfaz.

Por que hacen falta las dos y no una:

    EstadoCampo responde "¿me puedo fiar de esto?"      -> pregunta del sistema
    OrigenDato responde  "¿quien dijo esto?"            -> pregunta de la persona

Un adolescente mirando su Pasaporte no necesita saber que un campo esta en
ambar; necesita saber que esa dosis la dijo el, y que el INSN todavia no la
coteja con su historia. Es la misma informacion contada desde el otro lado, y
la segunda version es la que permite que alguien la corrija.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from enum import Enum

from relevo.dominio.objetos_valor.campo_extraido import EstadoCampo


class OrigenDato(Enum):
    """Quien puso este dato aqui."""

    VERIFICADO_INSN = "verificado_insn"
    """Sale de un documento del INSN y paso el verificador. ~ EstadoCampo.VERDE"""

    INFORMADO_POR_PACIENTE = "informado_por_paciente"
    """Lo dijo el propio paciente. ~ EstadoCampo.AMBAR

    Ambar y no rojo: no es un dato dudoso, es un dato de otra procedencia. En
    muchos casos el paciente sabe mejor que su historia lo que esta tomando de
    verdad — y esa discrepancia es informacion clinica valiosa, no ruido."""

    PENDIENTE_DE_COTEJO = "pendiente_de_cotejo"
    """Nadie lo confirmo todavia. ~ EstadoCampo.ROJO"""

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    @property
    def etiqueta_corta(self) -> str:
        """Para la insignia que va pegada al dato en pantalla."""
        return _ETIQUETAS_CORTAS[self]

    @property
    def estado_campo(self) -> EstadoCampo:
        """El estado del verificador que le corresponde."""
        return _A_ESTADO_CAMPO[self]

    @classmethod
    def desde_estado_campo(cls, estado: EstadoCampo) -> OrigenDato:
        """Traduce del idioma del verificador al del paciente.

        Un ambar del verificador se presenta como "lo informaste tu" solo
        cuando el dato viene de una declaracion; para eso esta
        `desde_estado_campo_de_documento`, que es la traduccion correcta cuando
        el origen es un documento del INSN.
        """
        return _DESDE_ESTADO_CAMPO[estado]

    def __str__(self) -> str:
        return self.etiqueta


_ETIQUETAS: dict[OrigenDato, str] = {
    OrigenDato.VERIFICADO_INSN: "Verificado por el INSN",
    OrigenDato.INFORMADO_POR_PACIENTE: "Informado por el paciente",
    OrigenDato.PENDIENTE_DE_COTEJO: "Pendiente de cotejo",
}

_ETIQUETAS_CORTAS: dict[OrigenDato, str] = {
    OrigenDato.VERIFICADO_INSN: "INSN",
    OrigenDato.INFORMADO_POR_PACIENTE: "lo dijiste tu",
    OrigenDato.PENDIENTE_DE_COTEJO: "sin cotejar",
}

_A_ESTADO_CAMPO: dict[OrigenDato, EstadoCampo] = {
    OrigenDato.VERIFICADO_INSN: EstadoCampo.VERDE,
    OrigenDato.INFORMADO_POR_PACIENTE: EstadoCampo.AMBAR,
    OrigenDato.PENDIENTE_DE_COTEJO: EstadoCampo.ROJO,
}

_DESDE_ESTADO_CAMPO: dict[EstadoCampo, OrigenDato] = {
    EstadoCampo.VERDE: OrigenDato.VERIFICADO_INSN,
    EstadoCampo.AMBAR: OrigenDato.INFORMADO_POR_PACIENTE,
    EstadoCampo.ROJO: OrigenDato.PENDIENTE_DE_COTEJO,
}


class TipoDiscrepancia(Enum):
    """En que no coinciden el Pasaporte y lo que declara el paciente.

    Cuatro tipos y no un booleano "hay diferencia", porque cada uno pide una
    accion distinta del equipo: una falta en el Pasaporte se resuelve mirando
    la historia; una dosis distinta se resuelve llamando al paciente.
    """

    FALTA_EN_PASAPORTE = "falta_en_pasaporte"
    """El paciente toma algo que el Pasaporte no registra. El caso mas
    interesante de los cuatro: suele ser medicacion anadida en otro
    establecimiento, y es exactamente lo que un receptor necesita saber."""

    FALTA_EN_DECLARACION = "falta_en_declaracion"
    """El Pasaporte lo registra y el paciente no lo menciono. Puede ser que lo
    dejo de tomar, o que se olvido de decirlo. No son lo mismo y el sistema no
    puede saber cual es: por eso reporta, no decide."""

    DOSIS_DISTINTA = "dosis_distinta"
    FRECUENCIA_DISTINTA = "frecuencia_distinta"

    @property
    def etiqueta(self) -> str:
        return {
            TipoDiscrepancia.FALTA_EN_PASAPORTE: "Falta en el Pasaporte",
            TipoDiscrepancia.FALTA_EN_DECLARACION: "No lo menciono el paciente",
            TipoDiscrepancia.DOSIS_DISTINTA: "La dosis no coincide",
            TipoDiscrepancia.FRECUENCIA_DISTINTA: "La frecuencia no coincide",
        }[self]

    @property
    def es_de_ausencia(self) -> bool:
        """True si el problema es que algo esta en un lado y no en el otro."""
        return self in (
            TipoDiscrepancia.FALTA_EN_PASAPORTE,
            TipoDiscrepancia.FALTA_EN_DECLARACION,
        )

    def __str__(self) -> str:
        return self.etiqueta
