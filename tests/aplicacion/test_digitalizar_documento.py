"""Casos de uso de digitalizacion, probados con dobles de los puertos.

Estos tests son la razon de ser de A2. Antes esta logica vivia dentro de
`app.py` y solo se podia ejercitar levantando un navegador; ahora corre en
milisegundos contra un lector falso.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from relevo.aplicacion.digitalizar_documento import (
    CampoDigitalizado,
    ConfirmarDigitalizacion,
    DigitalizarDocumento,
)
from relevo.dominio.puertos.lectura_documento import LectorDocumento


class LectorFalso(LectorDocumento):
    """Doble del puerto. Devuelve lo que se le diga, y cuenta las llamadas."""

    def __init__(self, texto: str = "", falla: bool = False) -> None:
        self._texto = texto
        self._falla = falla
        self.llamadas = 0

    def leer(self, imagen: bytes, instruccion: str) -> str:
        self.llamadas += 1
        if self._falla:
            raise RuntimeError("el lector no responde")
        return self._texto

    @property
    def nombre(self) -> str:
        return "falso"

    @property
    def requiere_red(self) -> bool:
        return False


def _extraer_dni(texto: str) -> list[CampoDigitalizado]:
    """Extractor minimo: acepta un DNI de 8 digitos y rechaza lo demas."""
    for linea in texto.splitlines():
        if linea.lower().startswith("dni:"):
            crudo = linea.split(":", 1)[1].strip()
            valido = crudo.isdigit() and len(crudo) == 8
            return [
                CampoDigitalizado(
                    nombre="dni",
                    valor=crudo if valido else None,
                    crudo=crudo,
                    motivo="" if valido else f"tiene {len(crudo)} digitos, el DNI tiene 8",
                )
            ]
    return [CampoDigitalizado(nombre="dni", valor=None, motivo="no se encontro")]


# ── DigitalizarDocumento ────────────────────────────────────────────────────


def test_lee_el_documento_y_extrae_los_campos() -> None:
    caso = DigitalizarDocumento(LectorFalso("DNI: 72319111"), _extraer_dni)
    doc = caso.ejecutar("hr_0001", b"imagen")

    assert doc.valores["dni"] == "72319111"
    assert doc.tasa_captura == 1.0
    assert not doc.requieren_revision


def test_un_valor_que_no_cumple_formato_va_a_revision_y_no_se_inventa() -> None:
    """La regla del proyecto: un null se revisa, un valor equivocado no se ve."""
    caso = DigitalizarDocumento(LectorFalso("DNI: 7231911"), _extraer_dni)
    doc = caso.ejecutar("hr_0001", b"imagen")

    assert doc.valores["dni"] is None
    assert len(doc.requieren_revision) == 1
    # El crudo se conserva: quien revisa necesita ver que se leyo y por que
    # se rechazo, no un campo vacio sin explicacion.
    assert doc.requieren_revision[0].crudo == "7231911"
    assert "8" in doc.requieren_revision[0].motivo


def test_el_fallo_del_lector_se_propaga_y_no_se_disfraza_de_lectura_vacia() -> None:
    """Un documento sin leer y uno leido como vacio son cosas distintas."""
    caso = DigitalizarDocumento(LectorFalso(falla=True), _extraer_dni)
    with pytest.raises(RuntimeError):
        caso.ejecutar("hr_0001", b"imagen")


def test_desde_texto_no_vuelve_a_llamar_al_modelo() -> None:
    """La transcripcion cuesta minutos en CPU; la extraccion es instantanea.

    Separarlas permite re-correr las reglas sin pagar el modelo, que es lo que
    hace que la pantalla abra al instante en una demo.
    """
    lector = LectorFalso("DNI: 72319111")
    caso = DigitalizarDocumento(lector, _extraer_dni)

    doc = caso.desde_texto("hr_0001", "DNI: 72319111")

    assert lector.llamadas == 0
    assert doc.desde_cache is True
    assert doc.valores["dni"] == "72319111"


# ── ConfirmarDigitalizacion ─────────────────────────────────────────────────


def _acta_de(finales: dict[str, str], leidos: dict[str, str | None], revisor: str = "Dra. Lopez"):
    pdfs: list[tuple] = []

    def generar(doc_id, campos, rev, momento) -> bytes:  # type: ignore[no-untyped-def]
        pdfs.append((doc_id, campos, rev, momento))
        return b"%PDF-falso"

    caso = ConfirmarDigitalizacion(generar_pdf=generar)
    acta, pdf = caso.ejecutar(
        documento_id="hr_0001",
        valores_finales=finales,
        valores_leidos=leidos,
        revisor=revisor,
        momento=datetime(2026, 8, 15, 10, 30),
    )
    return acta, pdf, pdfs


def test_distingue_lo_aceptado_de_lo_corregido_a_mano() -> None:
    """Es el contenido real del acta: sin esa distincion seria indistinguible
    de una transcripcion automatica sin revisar."""
    acta, _, _ = _acta_de(
        finales={"dni": "72319111", "celular": "965698006", "numero_hc": ""},
        leidos={"dni": "72319111", "celular": None, "numero_hc": None},
    )

    porNombre = {c.nombre: c for c in acta.campos}
    assert porNombre["dni"].origen == "AUTOMATICO"
    assert porNombre["celular"].origen == "CORREGIDO"
    assert porNombre["numero_hc"].origen == "VACIO"
    assert (acta.automaticos, acta.corregidos, acta.vacios) == (1, 1, 1)


def test_conserva_el_valor_leido_en_los_campos_corregidos() -> None:
    """El acta tiene que poder mostrar de que valor se corrigio."""
    acta, _, _ = _acta_de(
        finales={"numero_hc": "30389"},
        leidos={"numero_hc": "30889"},
    )
    campo = acta.campos[0]
    assert campo.origen == "CORREGIDO"
    assert campo.valor_leido == "30889"
    assert campo.valor_final == "30389"


def test_no_se_emite_acta_sin_quien_la_revisa() -> None:
    """La trazabilidad es el contenido del acta, no un adorno."""
    with pytest.raises(ValueError, match="revisa"):
        _acta_de(finales={"dni": "72319111"}, leidos={"dni": "72319111"}, revisor="   ")


def test_el_pdf_recibe_los_campos_ya_clasificados() -> None:
    """El caso de uso decide QUE va en el acta; el adaptador solo lo dibuja."""
    _, pdf, llamadas = _acta_de(
        finales={"dni": "72319111"}, leidos={"dni": "72319111"}
    )
    assert pdf == b"%PDF-falso"
    assert len(llamadas) == 1
    doc_id, campos, revisor, momento = llamadas[0]
    assert doc_id == "hr_0001"
    assert revisor == "Dra. Lopez"
    assert campos[0]["estado"] == "AUTOMATICO"
    assert momento == datetime(2026, 8, 15, 10, 30)
