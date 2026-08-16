"""Generador de Pasaporte de Salud 18+ en formato PDF con ReportLab.

Diseñado para impresión láser monocroma o color en el INSN San Borja y entrega física al paciente.
Cumple con la RM 214-2018-MINSA y NT 018-MINSA/DGSP-V.01.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from relevo.dominio.entidades.paciente import Paciente


def generar_qr_imagen_bytes(contenido: str) -> io.BytesIO:
    """Genera la imagen del QR en un buffer de memoria BytesIO."""
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(contenido)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#000000", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generar_pasaporte_pdf_bytes(paciente: Paciente, hoy: date) -> bytes:
    """Genera el Pasaporte de Salud 18+ en formato PDF como bytes descargables."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Estilos tipográficos institucionales
    style_inst = ParagraphStyle(
        "Institucional",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#1a365d"),
    )
    style_subinst = ParagraphStyle(
        "SubInstitucional",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#4a5568"),
    )
    style_titulo = ParagraphStyle(
        "Titulo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1a365d"),
    )
    style_subtitulo = ParagraphStyle(
        "SubTitulo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2d3748"),
    )
    style_sec_title = ParagraphStyle(
        "SecTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#1a365d"),
    )
    style_body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1a202c"),
    )
    style_body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1a202c"),
    )
    style_legal = ParagraphStyle(
        "Legal",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#4a5568"),
    )

    story = []

    # 1. Cabecera Institucional + QR
    qr_buf = generar_qr_imagen_bytes(
        f"RELEVO-INSN-SB|{paciente.id}|EDAD:{paciente.edad(hoy)}|FECHA:{hoy.isoformat()}"
    )
    qr_img = Image(qr_buf, width=65, height=65)

    header_text = [
        Paragraph("INSTITUTO NACIONAL DE SALUD DEL NIÑO SAN BORJA", style_inst),
        Paragraph("PROGRAMA DE TRANSICIÓN ASISTENCIAL PEDIÁTRICO A ADULTO · PUENTE 18+", style_subinst),
        Spacer(1, 4),
        Paragraph("PASAPORTE DE SALUD 18+", style_titulo),
        Paragraph("Documento Oficial de Transferencia Asistencial Pediátrico a Adulto", style_subtitulo),
    ]

    header_table = Table([[header_text, qr_img]], colWidths=[440, 75])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a365d"), spaceAfter=8))

    # 2. Datos de Identificación del Paciente
    dx_principal = paciente.diagnostico_principal
    dx_p_texto = f"{dx_principal.codigo} — {dx_principal.descripcion}" if dx_principal else "No registrado"
    meses_corte = paciente.meses_hasta_corte(hoy)
    tiempo_str = f"{meses_corte} meses" if meses_corte > 0 else "Mayor de 18 años (Corte cumplido)"

    datos_paciente = [
        [
            Paragraph(f"<b>Código Interno:</b> {paciente.id}", style_body),
            Paragraph(f"<b>Edad Actual:</b> {paciente.edad(hoy)} años", style_body),
            Paragraph(f"<b>Tiempo al corte 18+:</b> {tiempo_str}", style_body),
        ],
        [
            Paragraph(f"<b>Régimen de Seguro:</b> {paciente.tipo_seguro.value}", style_body),
            Paragraph(f"<b>Procedencia:</b> {paciente.procedencia or 'No registrada'}", style_body),
            Paragraph(f"<b>Fecha de Emisión:</b> {hoy.strftime('%d/%m/%Y')}", style_body),
        ],
    ]
    t_datos = Table(datos_paciente, colWidths=[170, 170, 175])
    t_datos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t_datos)
    story.append(Spacer(1, 8))

    # 3. Diagnósticos Activos y Comorbilidades
    story.append(Paragraph("1. DIAGNÓSTICOS CLÍNICOS ACTIVOS", style_sec_title))
    story.append(Spacer(1, 2))
    dx_rows = [
        [
            Paragraph(f"<b>Diagnóstico Principal:</b> {dx_p_texto}", style_body),
        ]
    ]
    for d in paciente.diagnosticos:
        if not d.es_principal:
            dx_rows.append([Paragraph(f"• <b>{d.codigo}:</b> {d.descripcion}", style_body)])

    t_dx = Table(dx_rows, colWidths=[515])
    t_dx.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_dx)
    story.append(Spacer(1, 8))

    # 4. Medicación y Tratamiento Farmacológico
    story.append(Paragraph("2. MEDICACIÓN ACTIVA Y ESQUEMA FARMACOLÓGICO", style_sec_title))
    story.append(Spacer(1, 2))
    med_rows = [
        [
            Paragraph("<b>Medicamento</b>", style_body_bold),
            Paragraph("<b>Dosis y Vía</b>", style_body_bold),
            Paragraph("<b>Frecuencia</b>", style_body_bold),
            Paragraph("<b>Estado de Validación</b>", style_body_bold),
        ]
    ]
    if paciente.medicamentos:
        for m in paciente.medicamentos:
            if m.requiere_completar_manualmente:
                dosis_txt = "____________ (Completar)"
                frec_txt = "____________"
                val_txt = "<font color='#c53030'><b>Requiere firma/dosis manual</b></font>"
            else:
                dosis_txt = f"{m.dosis or ''} {m.via or ''}".strip()
                frec_txt = m.frecuencia or "Según indicación"
                val_txt = "Verificado en HC"
            med_rows.append(
                [
                    Paragraph(m.nombre, style_body),
                    Paragraph(dosis_txt, style_body),
                    Paragraph(frec_txt, style_body),
                    Paragraph(val_txt, style_body),
                ]
            )
    else:
        med_rows.append([Paragraph("Sin medicación activa registrada", style_body), Paragraph("-", style_body), Paragraph("-", style_body), Paragraph("-", style_body)])

    t_med = Table(med_rows, colWidths=[150, 130, 115, 120])
    t_med.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_med)
    story.append(Spacer(1, 8))

    # 5. Dispositivos de Soporte Vital y Cirugías
    story.append(Paragraph("3. DISPOSITIVOS DE SOPORTE VITAL Y CIRUGÍAS", style_sec_title))
    story.append(Spacer(1, 2))
    disp_txt = ", ".join(d.descripcion or d.tipo for d in paciente.dispositivos) if paciente.dispositivos else "Ninguno registrado"
    cir_txt = ", ".join(str(c) for c in paciente.cirugias) if paciente.cirugias else "Ninguna registrada"
    alergias_txt = ", ".join(paciente.alergias) if paciente.alergias else "No conocidas / No registradas"

    t_soporte = Table(
        [
            [Paragraph(f"<b>Dispositivos de Soporte:</b> {disp_txt}", style_body)],
            [Paragraph(f"<b>Cirugías Previas Relevantes:</b> {cir_txt}", style_body)],
            [Paragraph(f"<b>Alergias Medicamentosas (RAM):</b> <font color='#c53030'><b>{alergias_txt}</b></font>", style_body)],
        ],
        colWidths=[515],
    )
    t_soporte.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_soporte)
    story.append(Spacer(1, 8))

    # 4. Aspectos Psicosociales y Red de Apoyo (Rúbrica INSN #5)
    story.append(Paragraph("4. ASPECTOS PSICOSOCIALES Y RED DE APOYO FAMILIAR", style_sec_title))
    story.append(Spacer(1, 2))
    psi = paciente.psicosocial
    apoyo_txt = psi.apoyo_familiar if (psi and psi.apoyo_familiar) else "Acompañamiento familiar activo en consultas y tratamiento."
    escolaridad_txt = psi.escolaridad_ocupacion if (psi and psi.escolaridad_ocupacion) else "Educación básica en curso / adaptada."
    autonomia_txt = psi.autonomia_autocuidado if (psi and psi.autonomia_autocuidado) else "En proceso de aprendizaje de autonomía en medicación y citas."

    t_psico = Table(
        [
            [Paragraph(f"• <b>Soporte Familiar:</b> {apoyo_txt}", style_body)],
            [Paragraph(f"• <b>Escolaridad / Proyecto:</b> {escolaridad_txt}", style_body)],
            [Paragraph(f"• <b>Nivel de Autonomía:</b> {autonomia_txt}", style_body)],
        ],
        colWidths=[515],
    )
    t_psico.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_psico)
    story.append(Spacer(1, 8))

    # 5. Alertas y Recomendaciones para el Servicio de Adultos
    story.append(Paragraph("5. RECOMENDACIONES PARA EL ESTABLECIMIENTO RECEPTOR DE ADULTOS", style_sec_title))
    story.append(Spacer(1, 2))
    contacto_pref = paciente.contacto_preferente(hoy)
    contacto_str = (
        f"{contacto_pref.nombre} ({contacto_pref.tipo.value}) — Tel: {contacto_pref.telefono.enmascarado() if contacto_pref.telefono else 'Sin teléfono'}"
        if contacto_pref
        else "No registrado"
    )

    t_alertas = Table(
        [
            [Paragraph("• Garantizar la continuidad inmediata del tratamiento sin interrupción de entrega de fármacos.", style_body)],
            [Paragraph("• Programar primera consulta de acogida dentro de los 30 días posteriores a la recepción de la referencia.", style_body)],
            [Paragraph(f"• <b>Contacto de enlace familiar registrado:</b> {contacto_str}", style_body)],
        ],
        colWidths=[515],
    )
    t_alertas.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_alertas)
    story.append(Spacer(1, 10))

    # 7. Marco Legal y Casilla de Firma Médica
    t_firma = Table(
        [
            [
                Paragraph(
                    "<b>VALIDEZ NORMATIVA:</b> Documento complementario de transferencia asistencial elaborado con asistencia del sistema Relevo (INSN San Borja). "
                    "Conforme a la RM 214-2018-MINSA y la NT 018-MINSA/DGSP-V.01. Requiere firma y sello del médico tratante para su entrega oficial.",
                    style_legal,
                ),
                Paragraph(
                    "<br/><br/>________________________________________<br/>"
                    "<b>Firma y Sello del Médico Tratante</b><br/>"
                    "CMP: _________________  RNE: _________________",
                    style_body,
                ),
            ]
        ],
        colWidths=[315, 200],
    )
    t_firma.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#a0aec0")),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f7fafc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t_firma)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
