"""Acta de digitalizacion: el PDF que cierra la lectura de un documento.

QUE ES Y POR QUE EXISTE
Cuando alguien revisa los campos que el sistema leyo, corrige los que hagan
falta y firma, ESE es el momento en que un papel se convierte en dato fiable.
El acta deja constancia de ese momento.

Y deja constancia de algo mas, que es lo inusual: **de que campos fueron
corregidos a mano y cuales acepto el sistema solo**. Un acta que solo mostrara
los valores finales seria indistinguible de una transcripcion automatica sin
revisar, y perderia justo lo que la hace confiable.

REGLA QUE HEREDA DEL RESTO DEL PROYECTO
Nadie firma lo que no vio. El acta lleva el nombre de quien reviso, y mientras
dure el hackathon sale marcada como datos sinteticos igual que el Pasaporte:
un documento con aspecto clinico y sin marca puede terminar en manos de alguien
que lo tome por real.
"""

from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

MARCA_DEMO = "DATOS SINTETICOS — DEMO"

# Estilo de las celdas de la tabla.
#
# `leading` explicito porque sin el las lineas se pisan al ajustar, y
# `wordWrap="CJK"` porque parte tambien DENTRO de palabras largas sin espacios
# —un nombre de establecimiento en mayusculas o un codigo— que el ajuste por
# palabras no sabe romper.
_CELDA = ParagraphStyle(
    "celda",
    fontName="Helvetica",
    fontSize=7.5,
    leading=9.5,
    wordWrap="CJK",
)

_CELDA_ENCABEZADO = ParagraphStyle(
    "celda_encabezado",
    parent=_CELDA,
    fontName="Helvetica-Bold",
)


def _celda(texto: str | None, encabezado: bool = False) -> Paragraph:
    """Toda celda va en Paragraph: un str no ajusta y se sale de la columna.

    `escape` es obligatorio — ReportLab interpreta el contenido de un Paragraph
    como marcado, y un valor leido por el modelo puede traer '&' o '<'. Un
    ampersand en el nombre de un establecimiento rompia el render entero.
    """
    return Paragraph(
        escape(str(texto if texto not in (None, "") else "—")),
        _CELDA_ENCABEZADO if encabezado else _CELDA,
    )

AVISO_ACTA = (
    "Acta de digitalizacion asistida. Los valores marcados como CORREGIDO fueron "
    "modificados manualmente por la persona revisora sobre la lectura automatica. "
    "Este documento no reemplaza la Hoja de Referencia original, que debe "
    "conservarse."
)


def generar_acta_pdf_bytes(
    documento_id: str,
    campos: list[dict[str, str]],
    revisor: str,
    momento: datetime | None = None,
) -> bytes:
    """Arma el acta.

    `campos` es una lista de dicts con las claves:
        nombre, valor_final, valor_leido, estado

    `estado` es uno de: AUTOMATICO, CORREGIDO, VACIO. La distincion es el
    contenido real del acta — sin ella, esto seria una tabla de valores.
    """
    momento = momento or datetime.now()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Acta de digitalizacion {documento_id}",
    )

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "titulo",
        parent=estilos["Heading1"],
        fontSize=15,
        textColor=colors.HexColor("#1a365d"),
        spaceAfter=2,
    )
    sub = ParagraphStyle(
        "sub", parent=estilos["Normal"], fontSize=8.5,
        textColor=colors.HexColor("#4a5568"),
    )
    marca = ParagraphStyle(
        "marca", parent=estilos["Normal"], fontSize=9,
        textColor=colors.HexColor("#9b2c2c"), spaceAfter=8,
    )
    nota = ParagraphStyle(
        "nota", parent=estilos["Normal"], fontSize=7.5,
        textColor=colors.HexColor("#718096"),
    )

    piezas: list[object] = [
        Paragraph(f"<b>{MARCA_DEMO}</b>", marca),
        Paragraph("Acta de Digitalización Asistida", titulo),
        Paragraph(
            "Sistema Relevo · Instituto Nacional de Salud del Niño San Borja", sub
        ),
        Spacer(1, 8),
        Paragraph(
            f"<b>Documento origen:</b> {documento_id} &nbsp;&nbsp;·&nbsp;&nbsp; "
            f"<b>Revisado por:</b> {revisor or '(sin identificar)'} &nbsp;&nbsp;·&nbsp;&nbsp; "
            f"<b>Fecha:</b> {momento.strftime('%d/%m/%Y %H:%M')}",
            sub,
        ),
        Spacer(1, 10),
    ]

    # ═══════════════════════════════════════════════════════════════════════
    # POR QUE CADA CELDA VA EN UN Paragraph Y NO EN UN str
    #
    # ReportLab NO ajusta lineas dentro de un `str`: lo dibuja de corrido y lo
    # deja salir de la celda, invadiendo la columna vecina. Con un nombre como
    # "INSTITUTO NACIONAL DE SALUD DEL NINO SAN BORJA" el acta salia
    # ilegible.
    #
    # Y las anchuras: [42, 52, 52, 28] suman 174 mm, pero el ancho util de un
    # A4 con margenes de 20 mm es 170. Se desbordaba por los dos lados a la vez.
    # ═══════════════════════════════════════════════════════════════════════
    filas: list[list[Paragraph]] = [
        [_celda(t, encabezado=True)
         for t in ("Campo", "Valor validado", "Lectura automática", "Origen")]
    ]
    for c in campos:
        leido = c.get("valor_leido")
        estado = c.get("estado", "")
        filas.append(
            [
                _celda(c.get("nombre", "")),
                _celda(c.get("valor_final")),
                # "no legible" y "no aplica" son cosas distintas: el guion se
                # lee como lo segundo y aqui casi siempre es lo primero.
                _celda(leido if estado == "CORREGIDO" else ("=" if leido else "no legible")),
                _celda(estado),
            ]
        )

    tabla = Table(
        filas,
        colWidths=[38 * mm, 54 * mm, 50 * mm, 28 * mm],  # 170 mm = ancho util real
        repeatRows=1,
    )
    estilo_tabla = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#4a5568")),
        # Sin FONTSIZE: con Paragraph el tamano lo manda el ParagraphStyle, y
        # tener los dos declarados confunde a quien venga a tocarlo.
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Las filas corregidas a mano se resaltan: son la informacion que hace
    # distinta a esta acta de una transcripcion automatica cualquiera.
    for i, c in enumerate(campos, start=1):
        if c.get("estado") == "CORREGIDO":
            estilo_tabla.append(
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#feebc8"))
            )
        elif c.get("estado") == "VACIO":
            estilo_tabla.append(
                ("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#a0aec0"))
            )
    tabla.setStyle(TableStyle(estilo_tabla))

    piezas.append(tabla)
    piezas.append(Spacer(1, 10))

    corregidos = sum(1 for c in campos if c.get("estado") == "CORREGIDO")
    automaticos = sum(1 for c in campos if c.get("estado") == "AUTOMATICO")
    vacios = sum(1 for c in campos if c.get("estado") == "VACIO")
    piezas.append(
        Paragraph(
            f"<b>Resumen:</b> {automaticos} campos aceptados de la lectura automatica · "
            f"{corregidos} corregidos manualmente · {vacios} sin dato.",
            sub,
        )
    )
    piezas.append(Spacer(1, 8))
    piezas.append(Paragraph(AVISO_ACTA, nota))
    piezas.append(Spacer(1, 14))
    piezas.append(
        Paragraph(
            "_______________________________<br/>"
            f"{revisor or 'Firma de la persona revisora'}",
            sub,
        )
    )

    doc.build(piezas)
    return buffer.getvalue()
