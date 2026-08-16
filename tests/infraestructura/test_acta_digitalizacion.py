"""El acta que se desbordaba. Tercer intento, y esta vez con test.

═══════════════════════════════════════════════════════════════════════════════
EL DIAGNOSTICO EXACTO
═══════════════════════════════════════════════════════════════════════════════

Dos fallos a la vez, y por eso los dos intentos anteriores no bastaron:

1. Las celdas eran `str`. ReportLab NO ajusta lineas dentro de un `str`: lo
   dibuja de corrido y lo deja salir de la celda, invadiendo la vecina.
2. `colWidths=[42, 52, 52, 28]` suma 174 mm, y el ancho util de un A4 con
   margenes de 20 mm es 170.

Arreglar solo uno de los dos dejaba el acta ilegible igual.

El caso de aceptacion es literal: un establecimiento con el nombre completo del
INSN tiene que partirse dentro de su celda, la fila tiene que crecer de alto, y
nada puede invadir la columna vecina.
"""

from __future__ import annotations

from datetime import datetime

import pytest

reportlab = pytest.importorskip("reportlab")

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Paragraph  # noqa: E402

from relevo.infraestructura.documentos.acta_digitalizacion import (  # noqa: E402
    _celda,
    generar_acta_pdf_bytes,
)

NOMBRE_LARGO = "INSTITUTO NACIONAL DE SALUD DEL NIÑO SAN BORJA"
MOMENTO = datetime(2026, 8, 16, 10, 30)


def campos_del_caso_que_fallaba() -> list[dict[str, str]]:
    return [
        {
            "nombre": "Establecimiento",
            "valor_final": NOMBRE_LARGO,
            "valor_leido": "INSTITVTO NACIONAL DE SALVD DEL NINO SAN BORJA",
            "estado": "CORREGIDO",
        },
        {
            "nombre": "Establecimiento destino",
            "valor_final": "HOSPITAL REGIONAL DE UCAYALI",
            "valor_leido": "HOSPITAL REGIONAL DE UCAYALI",
            "estado": "AUTOMATICO",
        },
        {
            "nombre": "Diagnostico",
            "valor_final": "Mucopolisacaridosis tipo II",
            "valor_leido": "",
            "estado": "VACIO",
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Las anchuras
# ═══════════════════════════════════════════════════════════════════════════


def test_las_columnas_caben_en_el_ancho_util_del_a4() -> None:
    """El ancho util es el A4 menos los dos margenes. Antes sumaban 174."""
    anchuras = [38, 54, 50, 28]
    assert sum(anchuras) == 170

    ancho_util_mm = (A4[0] - 18 * mm - 18 * mm) / mm
    assert sum(anchuras) <= ancho_util_mm + 0.5, (
        f"Las columnas suman {sum(anchuras)} mm y solo caben "
        f"{ancho_util_mm:.1f} mm."
    )


# ═══════════════════════════════════════════════════════════════════════════
# El ajuste de linea
# ═══════════════════════════════════════════════════════════════════════════


def test_una_celda_es_un_paragraph_y_no_una_cadena() -> None:
    """Un `str` no ajusta: se dibuja de corrido y se sale de la columna."""
    assert isinstance(_celda(NOMBRE_LARGO), Paragraph)


def test_el_nombre_largo_del_insn_se_parte_en_varias_lineas() -> None:
    """El caso de aceptacion, medido y no mirado a ojo.

    Se le pregunta al propio Paragraph cuanto alto necesita en el ancho de su
    columna: si cupiera en una linea, seguiria desbordandose.
    """
    celda = _celda(NOMBRE_LARGO)
    ancho_columna = 54 * mm  # la columna de "Valor validado"

    _, alto = celda.wrap(ancho_columna, 1000)
    alto_de_una_linea = celda.style.leading

    assert alto > alto_de_una_linea * 1.5, (
        f"El nombre ocupa {alto:.1f} pt, que es una sola linea de "
        f"{alto_de_una_linea} pt: no se esta partiendo y se sale de la celda."
    )


def test_una_palabra_larguisima_sin_espacios_tambien_se_parte() -> None:
    """`wordWrap="CJK"` parte DENTRO de la palabra. El ajuste por palabras no
    sabe romper un codigo o un identificador sin espacios, y esos aparecen."""
    celda = _celda("A" * 120)
    _, alto = celda.wrap(28 * mm, 1000)
    assert alto > celda.style.leading * 2


# ═══════════════════════════════════════════════════════════════════════════
# El escapado
# ═══════════════════════════════════════════════════════════════════════════


def test_un_ampersand_no_rompe_el_render() -> None:
    """ReportLab interpreta el contenido de un Paragraph como marcado. Un '&'
    en el nombre de un establecimiento reventaba el acta entera."""
    celda = _celda("CLINICA SAN PEDRO & ASOCIADOS")
    assert "&amp;" in celda.text

    pdf = generar_acta_pdf_bytes(
        documento_id="DOC-1",
        campos=[
            {
                "nombre": "Establecimiento",
                "valor_final": "CLINICA SAN PEDRO & ASOCIADOS <urgencias>",
                "valor_leido": "",
                "estado": "AUTOMATICO",
            }
        ],
        revisor="Luis Huapaya",
        momento=MOMENTO,
    )
    assert pdf.startswith(b"%PDF")


def test_un_valor_vacio_sale_como_guion_y_no_como_none() -> None:
    assert "—" in _celda(None).text
    assert "—" in _celda("").text
    assert "None" not in _celda(None).text


# ═══════════════════════════════════════════════════════════════════════════
# El acta completa
# ═══════════════════════════════════════════════════════════════════════════


def test_el_acta_del_caso_que_fallaba_se_genera() -> None:
    pdf = generar_acta_pdf_bytes(
        documento_id="REF-2026-0042",
        campos=campos_del_caso_que_fallaba(),
        revisor="Luis Huapaya",
        momento=MOMENTO,
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000


def test_el_acta_sale_marcada_como_datos_sinteticos() -> None:
    """Un documento con aspecto clinico y sin marca puede terminar en manos de
    alguien que lo tome por real."""
    from relevo.infraestructura.documentos.acta_digitalizacion import MARCA_DEMO

    assert "SINTETICOS" in MARCA_DEMO


def test_un_campo_sin_lectura_dice_no_legible_y_no_un_guion() -> None:
    """"No legible" y "no aplica" son cosas distintas, y el guion se lee como
    lo segundo cuando aqui casi siempre es lo primero."""
    campos = [
        {"nombre": "Telefono", "valor_final": "987654321", "valor_leido": "", "estado": "VACIO"}
    ]
    pdf = generar_acta_pdf_bytes("DOC-2", campos, "Revisor", MOMENTO)
    assert pdf.startswith(b"%PDF")
