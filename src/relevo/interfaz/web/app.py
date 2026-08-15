"""Sistema de Acompañamiento a la Transición Pediátrico-Adulto — Relevo (Puente 18+).

Adaptador de Entrada Web (Streamlit).
Diseñado para médicos, enfermeras, asistentas sociales y coordinadores de referencia
del Instituto Nacional de Salud del Niño San Borja (INSN SB).

Funciona 100% offline (sin conexión a internet) con datos sintéticos auditables.
"""

from __future__ import annotations

import base64
import io
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

# Asegurar que el paquete relevo se encuentre en el path
_SRC_DIR = Path(__file__).resolve().parents[3]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import pandas as pd
import qrcode
import streamlit as st

from relevo.aplicacion.priorizar_cohorte import (
    FilaPrioridad,
    PriorizarCohorte,
    ResultadoPriorizacion,
)
from relevo.aplicacion.validacion_captura import (
    ETIQUETA_OTRO,
    Estado,
    Veredicto,
    validar_celular,
    validar_dni,
    validar_fecha_nacimiento,
    validar_numero_hc,
)
from relevo.dominio.entidades.diagnostico import TipoContacto
from relevo.dominio.objetos_valor.indice_urgencia import EstadoSemaforo

# Unico punto donde esta pantalla toca el mundo exterior. No importa ningun
# adaptador concreto: pide casos de uso ya construidos y pinta el resultado.
# `tests/test_arquitectura.py` verifica que siga siendo asi.
from relevo.interfaz.arranque import construir

FECHA_HOY_DEFECTO = date(2026, 8, 14)


def _host_ollama_configurado() -> str | None:
    """El Ollama declarado en los secretos del despliegue, si lo hay.

    En Streamlit Cloud no puede correr el modelo de vision: necesita varios GB
    de RAM y no hay GPU. Para que el equipo pueda ver el modelo trabajando de
    verdad desde la URL publica, se declara en los secretos de la app la
    direccion de un Ollama alcanzable —tipicamente el de una maquina del
    equipo, expuesto por un tunel. Ver `docs/DESPLIEGUE.md`.

    Cuando no hay secreto declarado se devuelve None y `construir` se queda con
    el Ollama local, que es el comportamiento de siempre en desarrollo.
    """
    try:
        valor = st.secrets.get("RELEVO_OLLAMA_HOST", "")
    except Exception:  # noqa: BLE001
        # Sin archivo de secretos, `st.secrets` puede lanzar en vez de devolver
        # vacio. Correr en local sin secretos es el caso normal, no un error.
        return None
    texto = str(valor).strip()
    return texto or None


# El sistema completo, armado una sola vez. Todo lo que esta pantalla necesita
# del exterior sale de aqui.
SISTEMA = construir(host_ollama=_host_ollama_configurado())

# ═══════════════════════════════════════════════════════════════════════════
# CORPUS DE DOCUMENTOS ESCANEADOS (pestaña de digitalización)
#
# Todo el acceso al corpus pasa por `SISTEMA.revisar_corpus`. Esta pantalla ya
# no sabe que existen archivos: pide lecturas y las pinta.
#
# La transcripción con el modelo tarda ~2 minutos por documento en CPU, así que
# se cachea en disco. Una demo que obliga a esperar dos minutos delante de un
# jurado no es una demo: la caché hace que la pantalla abra instantánea, y el
# botón de leer en vivo queda para quien quiera ver el modelo trabajando.
# ═══════════════════════════════════════════════════════════════════════════
_CORPUS = SISTEMA.revisar_corpus
_CORPUS_DISPONIBLE = _CORPUS.hay_documentos
_CORPUS_ES_DEMO = _CORPUS.es_muestra_parcial


def _donde_corre_el_modelo() -> tuple[str, str]:
    """(nivel, mensaje) sobre dónde se está ejecutando el lector.

    En local esto era obvio y no hacía falta decirlo. En el despliegue deja de
    serlo: el modelo puede estar en el contenedor (nunca), en la máquina de
    quien mira, o en la de otra persona al otro lado de un túnel. Quien juzga
    una demo de lectura automática tiene derecho a saber dónde se ejecuta.
    """
    if not SISTEMA.lector_disponible:
        return (
            "warning",
            "**Sin modelo alcanzable.** Se muestran transcripciones ya "
            "producidas por el modelo y guardadas en disco. La lectura en vivo "
            "necesita un Ollama accesible; ver `docs/DESPLIEGUE.md`.",
        )
    remoto = "localhost" not in SISTEMA.host_lector and "127.0.0.1" not in (
        SISTEMA.host_lector
    )
    if remoto:
        return (
            "success",
            f"**Modelo en vivo:** `{SISTEMA.nombre_lector}` — ejecutándose en "
            f"una máquina del equipo, alcanzada en `{SISTEMA.host_lector}`. "
            "El documento viaja a ese equipo y vuelve transcrito.",
        )
    return (
        "success",
        f"**Modelo en vivo:** `{SISTEMA.nombre_lector}` en esta máquina. "
        "Ningún documento sale de aquí.",
    )


st.set_page_config(
    page_title="Relevo · Puente 18+ (INSN San Borja)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS CSS CLÍNICOS: ALTA LEGIBILIDAD, SERIO Y SIN DISTRACCIONES
# ═══════════════════════════════════════════════════════════════════════════

st.markdown(
    """
    <style>
    /* Ocultar barra de deploy y toolbar de Streamlit para evitar recorte del encabezado */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {
        display: none !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2.5rem;
    }

    /* Encabezado Hospitalario Formal */
    .hospital-header {
        background-color: #1a365d;
        color: #ffffff;
        padding: 16px 22px;
        border-radius: 6px;
        margin-bottom: 12px;
        border-left: 6px solid #2b6cb0;
    }
    .hospital-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.01em;
    }
    .hospital-sub {
        font-size: 0.85rem;
        color: #e2e8f0;
        margin-top: 3px;
    }

    /* Banner informativo de simulación */
    .demo-banner {
        background-color: #edf2f7;
        border: 1px solid #cbd5e0;
        border-left: 4px solid #4a5568;
        color: #2d3748;
        padding: 8px 14px;
        font-size: 0.82rem;
        font-weight: 600;
        border-radius: 4px;
        margin-bottom: 16px;
    }

    /* Tarjetas de Indicadores Asistenciales (KPIs) */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
    }
    .kpi-card {
        background: #ffffff;
        border: 1px solid #cbd5e0;
        border-radius: 6px;
        padding: 12px 14px;
    }
    .kpi-card-rojo {
        border-top: 3px solid #c53030;
    }
    .kpi-card-ambar {
        border-top: 3px solid #c05621;
    }
    .kpi-card-azul {
        border-top: 3px solid #2b6cb0;
    }
    .kpi-card-gris {
        border-top: 3px solid #4a5568;
    }
    .kpi-label {
        font-size: 0.74rem;
        text-transform: uppercase;
        font-weight: 700;
        color: #4a5568;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }
    .kpi-val {
        font-size: 1.7rem;
        font-weight: 700;
        line-height: 1.1;
        color: #1a202c;
    }
    .kpi-note {
        font-size: 0.74rem;
        color: #718096;
        margin-top: 4px;
    }

    /* Badges Formales */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .badge-rojo {
        background-color: #fed7d7;
        color: #9b2c2c;
        border: 1px solid #feb2b2;
    }
    .badge-ambar {
        background-color: #feebc8;
        color: #9c4221;
        border: 1px solid #fbd38d;
    }
    .badge-verde {
        background-color: #c6f6d5;
        color: #22543d;
        border: 1px solid #9ae6b4;
    }

    /* Hoja Previsualización del Pasaporte */
    .passport-sheet {
        background: #ffffff;
        border: 1px solid #a0aec0;
        border-radius: 6px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    .passport-header-box {
        border-bottom: 2px solid #1a365d;
        padding-bottom: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    .passport-section-title {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #1a365d;
        letter-spacing: 0.04em;
        margin-top: 12px;
        margin-bottom: 6px;
        border-bottom: 1px solid #cbd5e0;
        padding-bottom: 2px;
    }

    /* Tarjetas de Criterios Clínicos */
    .criterion-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #2b6cb0;
        border-radius: 4px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    .criterion-title {
        font-weight: 700;
        font-size: 0.88rem;
        color: #1a365d;
    }
    .criterion-desc {
        font-size: 0.8rem;
        color: #4a5568;
        margin-top: 2px;
    }

    /* Línea de tiempo formal */
    .timeline-box {
        border-left: 2px solid #2b6cb0;
        margin-left: 8px;
        padding-left: 14px;
        margin-top: 8px;
    }
    .timeline-entry {
        position: relative;
        margin-bottom: 14px;
    }
    .timeline-entry::before {
        content: '';
        position: absolute;
        left: -19px;
        top: 3px;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #2b6cb0;
    }
    .timeline-entry.pending::before {
        background: #a0aec0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def construir_sistema(cantidad: int, hoy: date) -> PriorizarCohorte:
    """El caso de uso de priorización para el padrón elegido en pantalla."""
    return SISTEMA.priorizar(cantidad, hoy)


def generar_qr_base64(contenido: str) -> str:
    """Genera código QR local en base64 para previsualización directa."""
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(contenido)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#000000", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# BARRA LATERAL: PARÁMETROS INSTITUCIONALES
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("#### Panel de Control")
    st.caption("INSN San Borja · Transición Asistencial")

    fecha_evaluacion = st.date_input(
        "Fecha de evaluación clínica",
        value=FECHA_HOY_DEFECTO,
        help="Fecha institucional contra la cual se evalúa la edad y el tiempo restante al corte de 18 años.",
    )
    if not isinstance(fecha_evaluacion, date):
        fecha_evaluacion = FECHA_HOY_DEFECTO

    total_pacientes = st.slider(
        "Total de pacientes en padrón",
        min_value=50,
        max_value=500,
        value=300,
        step=50,
        help="Tamaño de la población de adolescentes evaluada.",
    )

    st.divider()
    politica = SISTEMA.politica_plazos
    st.caption(
        f"**Normativa MINSA cargada:**\n"
        f"- Plazo registro de referencia: 7 días\n"
        f"- Mediana de espera en adultos: 85 días\n"
        f"- Umbral de alerta máxima: {politica.dias_por_estado.get(list(politica.dias_por_estado)[2], 120)} días"
    )

# Ejecución reactiva inmediata
sistema = construir_sistema(int(total_pacientes), fecha_evaluacion)
resultado: ResultadoPriorizacion = sistema.ejecutar(fecha_evaluacion)

# ═══════════════════════════════════════════════════════════════════════════
# ENCABEZADO HOSPITALARIO
# ═══════════════════════════════════════════════════════════════════════════

st.markdown(
    """
    <div class="hospital-header">
        <div class="hospital-title">RELEVO · Acompañamiento a la Transición Pediátrico a Adulto</div>
        <div class="hospital-sub">Instituto Nacional de Salud del Niño San Borja · Reto 1: Puente 18+</div>
    </div>
    <div class="demo-banner">
        MODO DE DEMOSTRACIÓN CLÍNICA: Todos los registros evaluados son sintéticos generados localmente. No se utiliza información de pacientes reales.
    </div>
    """,
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════
# PESTAÑAS CLÍNICAS FORMALES
# ═══════════════════════════════════════════════════════════════════════════

tab_radar, tab_ficha, tab_whatsapp, tab_ciclo, tab_digital, tab_config = st.tabs(
    [
        "Radar de Pacientes (Padrón)",
        "Ficha y Pasaporte 18+",
        "Avisos y Contacto Familiar",
        "Seguimiento y Cierre de Ciclo",
        "Digitalización de Hoja de Referencia",
        "Criterios Clínicos e Interoperabilidad",
    ]
)

# ───────────────────────────────────────────────────────────────────────────
# TAB 1: RADAR DE PACIENTES (PADRÓN)
# ───────────────────────────────────────────────────────────────────────────
with tab_radar:
    # Indicadores Asistenciales
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card kpi-card-azul">
                <div class="kpi-label">Padrón en Seguimiento</div>
                <div class="kpi-val">{len(resultado.filas)}</div>
                <div class="kpi-note">De {resultado.total_evaluados} evaluados</div>
            </div>
            <div class="kpi-card kpi-card-rojo">
                <div class="kpi-label">Prioridad Alta</div>
                <div class="kpi-val" style="color:#c53030;">{len(resultado.rojos)}</div>
                <div class="kpi-note">Intervención inmediata</div>
            </div>
            <div class="kpi-card kpi-card-ambar">
                <div class="kpi-label">Prioridad Media</div>
                <div class="kpi-val" style="color:#c05621;">{len(resultado.ambares)}</div>
                <div class="kpi-note">En preparación activa</div>
            </div>
            <div class="kpi-card kpi-card-gris">
                <div class="kpi-label">Teléfono por Actualizar</div>
                <div class="kpi-val">{len(resultado.sin_contacto_vigente)}</div>
                <div class="kpi-note">Sin verificación en > 1 año</div>
            </div>
            <div class="kpi-card kpi-card-gris">
                <div class="kpi-label">Datos Incompletos</div>
                <div class="kpi-val">{len(resultado.con_datos_insuficientes)}</div>
                <div class="kpi-note">Revisión de historia requerida</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filtros de lista
    col_filtro, col_busqueda = st.columns([2, 2])
    with col_filtro:
        filtro_vista = st.selectbox(
            "Filtrar lista de trabajo:",
            options=[
                "Todos los pacientes",
                "Prioridad Alta",
                "Teléfono por actualizar",
                "Datos incompletos",
            ],
        )
    with col_busqueda:
        texto_buscar = st.text_input(
            "Buscar por código o diagnóstico:",
            placeholder="Ejemplo: SINT-0001, renal, fibrosis, E84.0...",
        )

    pacientes_filtrados = list(resultado.filas)
    if filtro_vista == "Prioridad Alta":
        pacientes_filtrados = list(resultado.rojos)
    elif filtro_vista == "Teléfono por actualizar":
        pacientes_filtrados = list(resultado.sin_contacto_vigente)
    elif filtro_vista == "Datos incompletos":
        pacientes_filtrados = list(resultado.con_datos_insuficientes)

    if texto_buscar.strip():
        q = texto_buscar.strip().lower()
        pacientes_filtrados = [
            f
            for f in pacientes_filtrados
            if q in f.id.lower()
            or (f.paciente.diagnostico_principal and q in f.paciente.diagnostico_principal.descripcion.lower())
            or (f.paciente.diagnostico_principal and q in f.paciente.diagnostico_principal.codigo.valor.lower())
        ]

    # Construcción de DataFrame con todas las columnas disponibles
    TODAS_COLUMNAS = [
        "Código",
        "Prioridad",
        "Diagnóstico Principal",
        "Tiempo para 18 Años",
        "Seguro",
        "Procedencia",
        "Contacto Familiar",
        "Motivo de Urgencia",
    ]

    tabla_datos = []
    for f in pacientes_filtrados:
        dx_p = f.paciente.diagnostico_principal
        dx_texto = f"{dx_p.codigo}: {dx_p.descripcion}" if dx_p else "No registrado"

        contacto = f.paciente.contacto_preferente(fecha_evaluacion)
        tel_estado = "Vigente" if (contacto and contacto.esta_vigente(fecha_evaluacion)) else "Por actualizar"

        if f.meses_restantes <= 0:
            tiempo_str = f"Cumplió 18 años (hace {abs(f.meses_restantes)} m)"
        else:
            tiempo_str = f"{f.meses_restantes} meses ({f.edad} años)"

        motivo = f.indice.principales(1)[0].explicacion if f.indice.aportes else "Evaluación general"

        tabla_datos.append(
            {
                "Código": f.id,
                "Prioridad": f.indice.estado.etiqueta,
                "Diagnóstico Principal": dx_texto,
                "Tiempo para 18 Años": tiempo_str,
                "Seguro": f.paciente.tipo_seguro.value,
                "Procedencia": f.paciente.procedencia or "No registrada",
                "Contacto Familiar": tel_estado,
                "Motivo de Urgencia": motivo,
            }
        )

    df_completo = pd.DataFrame(tabla_datos) if tabla_datos else pd.DataFrame(columns=TODAS_COLUMNAS)

    # ── Controles de paginación y columnas visibles ──
    col_pag_size, col_cols_filter = st.columns([1, 3])

    with col_pag_size:
        filas_por_pagina = st.selectbox(
            "Filas por página:",
            options=[10, 15, 25, 50],
            index=1,
            help="Cantidad de pacientes que se muestran en cada página de la tabla.",
        )

    # Panel desplegable de selección de columnas con "Seleccionar todo" y checkboxes
    with col_cols_filter:
        if "panel_columnas_abierto" not in st.session_state:
            st.session_state["panel_columnas_abierto"] = False

        boton_toggle_label = "Columnas ▾" if not st.session_state["panel_columnas_abierto"] else "Columnas ▴"
        if st.button(boton_toggle_label, key="btn_toggle_columnas"):
            st.session_state["panel_columnas_abierto"] = not st.session_state["panel_columnas_abierto"]
            if hasattr(st, "experimental_rerun"):
                st.experimental_rerun()

        if st.session_state["panel_columnas_abierto"]:
            # Inicializar checks en session_state si no existen
            for i, c in enumerate(TODAS_COLUMNAS):
                key = f"col_chk_{i}"
                if key not in st.session_state:
                    st.session_state[key] = True

            cols_check = st.columns(2)
            mitad = (len(TODAS_COLUMNAS) + 1) // 2
            for idx, c in enumerate(TODAS_COLUMNAS[:mitad]):
                with cols_check[0]:
                    st.checkbox(c, value=st.session_state.get(f"col_chk_{idx}", True), key=f"col_chk_{idx}")
            for idx, c in enumerate(TODAS_COLUMNAS[mitad:], start=mitad):
                with cols_check[1]:
                    st.checkbox(c, value=st.session_state.get(f"col_chk_{idx}", True), key=f"col_chk_{idx}")

            col_sel_all, col_sel_none = st.columns([1, 1])
            with col_sel_all:
                if st.button("Seleccionar todo", key="btn_sel_todo"):
                    for i, _c in enumerate(TODAS_COLUMNAS):
                        st.session_state[f"col_chk_{i}"] = True
                    if hasattr(st, "experimental_rerun"):
                        st.experimental_rerun()
            with col_sel_none:
                if st.button("Deseleccionar todo", key="btn_deselec_todo"):
                    for i, _c in enumerate(TODAS_COLUMNAS):
                        st.session_state[f"col_chk_{i}"] = False
                    if hasattr(st, "experimental_rerun"):
                        st.experimental_rerun()

            columnas_visibles = [c for i, c in enumerate(TODAS_COLUMNAS) if st.session_state.get(f"col_chk_{i}", True)]
        else:
            columnas_visibles = TODAS_COLUMNAS

    if not columnas_visibles:
        columnas_visibles = TODAS_COLUMNAS

    df_vista = df_completo[columnas_visibles]

    # ── Paginación ──
    total_filas = len(df_vista)
    total_paginas = max(1, (total_filas + filas_por_pagina - 1) // filas_por_pagina)

    # Resetear la página cuando el padrón cambia de tamaño
    if "pagina_actual" not in st.session_state:
        st.session_state["pagina_actual"] = 1
    if st.session_state["pagina_actual"] > total_paginas:
        st.session_state["pagina_actual"] = 1

    pagina = st.session_state["pagina_actual"]
    inicio = (pagina - 1) * filas_por_pagina
    fin = min(inicio + filas_por_pagina, total_filas)
    df_pagina = df_vista.iloc[inicio:fin]

    st.markdown(f"**Lista de Pacientes en Padrón** — Página {pagina} de {total_paginas} ({total_filas} registros)")

    # Mostrar tabla de la página actual
    seleccion_tabla = st.dataframe(
        df_pagina,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        column_config={
            "Código": st.column_config.TextColumn("Código", width="small"),
            "Prioridad": st.column_config.TextColumn("Prioridad", width="small"),
            "Diagnóstico Principal": st.column_config.TextColumn("Diagnóstico Principal (CIE-10)", width="large"),
            "Tiempo para 18 Años": st.column_config.TextColumn("Tiempo para 18 Años", width="medium"),
            "Seguro": st.column_config.TextColumn("Seguro", width="small"),
            "Procedencia": st.column_config.TextColumn("Procedencia", width="medium"),
            "Contacto Familiar": st.column_config.TextColumn("Contacto", width="small"),
            "Motivo de Urgencia": st.column_config.TextColumn("Motivo Determinante", width="large"),
        },
    )

    # Si el usuario selecciona una fila en la tabla, guardarla en session_state (ajustado al índice global)
    if seleccion_tabla and seleccion_tabla.selection and seleccion_tabla.selection.rows:
        indice_fila_sel = inicio + seleccion_tabla.selection.rows[0]
        if indice_fila_sel < len(pacientes_filtrados):
            st.session_state["paciente_seleccionado_id"] = pacientes_filtrados[indice_fila_sel].id

    # Estilos específicos para los botones de paginación (celeste, hover y active azul)
    st.markdown(
        """
        <style>
        /* Estilo aplicado a botones de paginación con aria-label exacto */
        button[aria-label="Página anterior"], button[aria-label="Página siguiente"] {
            background-color: #e6f8ff !important;
            border-radius: 6px !important;
            color: #0b6b8f !important;
            border: 1px solid rgba(11,107,143,0.12) !important;
            transition: transform 80ms ease, filter 80ms ease;
        }
        button[aria-label="Página anterior"]:hover, button[aria-label="Página siguiente"]:hover {
            filter: brightness(0.98);
            transform: translateY(-1px);
        }
        button[aria-label="Página anterior"]:active, button[aria-label="Página siguiente"]:active {
            background-color: #0ea5e9 !important;
            color: white !important;
        }
        button[aria-label="Página anterior"][disabled], button[aria-label="Página siguiente"][disabled] {
            opacity: 0.45 !important;
            filter: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Navegación de páginas ──
    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("Página anterior", use_container_width=True, disabled=(pagina <= 1)):
            st.session_state["pagina_actual"] = pagina - 1
            st.rerun()

    with col_info:
        st.markdown(
            f"<div style='text-align:center;padding:6px 0;font-size:0.85rem;color:#4a5568;'>"
            f"Mostrando registros {inicio + 1} a {fin} de {total_filas} &nbsp;|&nbsp; "
            f"Página {pagina} de {total_paginas}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button("Página siguiente", use_container_width=True, disabled=(pagina >= total_paginas)):
            st.session_state["pagina_actual"] = pagina + 1
            st.rerun()


# ───────────────────────────────────────────────────────────────────────────
# TAB 2: FICHA DEL PACIENTE Y PASAPORTE DE SALUD 18+
# ───────────────────────────────────────────────────────────────────────────
with tab_ficha:
    st.markdown("#### Evaluación Individual y Pasaporte Oficial")

    opciones_dict = {f.id: f for f in resultado.filas}
    lista_ids = list(opciones_dict.keys())

    # Sincronizar selección si viene de la tabla
    id_defecto_index = 0
    if "paciente_seleccionado_id" in st.session_state and st.session_state["paciente_seleccionado_id"] in lista_ids:
        id_defecto_index = lista_ids.index(st.session_state["paciente_seleccionado_id"])

    id_seleccionado = st.selectbox(
        "Seleccionar paciente para evaluar:",
        options=lista_ids,
        index=id_defecto_index,
        format_func=lambda pid: f"{pid} — {opciones_dict[pid].paciente.diagnostico_principal.descripcion if opciones_dict[pid].paciente.diagnostico_principal else 'S/D'} ({opciones_dict[pid].edad} años, {opciones_dict[pid].indice.estado.etiqueta})",
    )

    fila_sel = opciones_dict[id_seleccionado]
    paciente_sel = fila_sel.paciente
    iut_sel = fila_sel.indice

    col_izq, col_der = st.columns([1, 1], gap="large")

    with col_izq:
        st.markdown("##### Factores Clínicos y Nivel de Urgencia")

        badge_txt = (
            "<span class='badge badge-rojo'>Prioridad Alta</span>"
            if iut_sel.estado == EstadoSemaforo.ROJO
            else "<span class='badge badge-ambar'>Prioridad Media</span>"
            if iut_sel.estado == EstadoSemaforo.AMBAR
            else "<span class='badge badge-verde'>Seguimiento Estándar</span>"
        )

        st.markdown(
            f"""
            <div style="background:#f7fafc;border:1px solid #cbd5e0;border-radius:6px;padding:12px 16px;margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:1.1rem;font-weight:700;color:#1a365d;">Paciente: {paciente_sel.id}</span>
                    {badge_txt}
                </div>
                <div style="font-size:0.83rem;color:#4a5568;margin-top:6px;line-height:1.4;">
                    <strong>Edad:</strong> {fila_sel.edad} años &nbsp;|&nbsp; 
                    <strong>Tiempo restante al corte 18+:</strong> {fila_sel.meses_restantes} meses &nbsp;|&nbsp; 
                    <strong>Seguro:</strong> {paciente_sel.tipo_seguro.value} &nbsp;|&nbsp; 
                    <strong>Procedencia:</strong> {paciente_sel.procedencia or 'No registrada'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Factores determinantes de la urgencia asistencial:**")
        max_aporte = max((a.aporte for a in iut_sel.aportes), default=1.0)
        for aporte in iut_sel.aportes:
            if aporte.aporte <= 0:
                continue
            porcentaje_barra = int(min(100, max(5, (aporte.aporte / max_aporte) * 100)))
            marca_faltante = " *(Dato no registrado en historia)*" if aporte.dato_faltante else ""
            st.markdown(f"• **{aporte.explicacion}**{marca_faltante}")
            st.progress(porcentaje_barra / 100.0)

        st.divider()
        st.markdown("**Tratamiento Farmacológico Activo:**")
        if paciente_sel.medicamentos:
            for med in paciente_sel.medicamentos:
                if med.requiere_completar_manualmente:
                    st.warning(f"**{med.nombre}**: Dosis pendiente de confirmación manual por el médico tratante.")
                else:
                    st.markdown(f"- **{med.nombre}**: {med.dosis or ''} {med.via or ''} {med.frecuencia or ''}")
        else:
            st.caption("Sin medicamentos crónicos registrados.")

        if paciente_sel.dispositivos:
            st.markdown("**Dispositivos y Soporte Vital:**")
            for disp in paciente_sel.dispositivos:
                st.markdown(f"- {disp.descripcion or disp.tipo}")

    with col_der:
        st.markdown("##### Pasaporte de Salud 18+ (Documento Oficial)")
        st.caption("Documento clínico de traspaso generado conforme a la RM 214-2018-MINSA.")

        # Generar PDF real en bytes
        pdf_bytes = SISTEMA.emitir_pasaporte(paciente_sel, fecha_evaluacion)

        # Previsualización del Pasaporte en Pantalla
        resumen_qr = (
            f"RELEVO-INSN-SB|{paciente_sel.id}|EDAD:{fila_sel.edad}|"
            f"DX:{paciente_sel.diagnostico_principal.codigo if paciente_sel.diagnostico_principal else 'ND'}"
        )
        qr_b64 = generar_qr_base64(resumen_qr)

        dx_principal = paciente_sel.diagnostico_principal
        dx_p_txt = f"{dx_principal.codigo} — {dx_principal.descripcion}" if dx_principal else "No registrado"
        contacto_pref = paciente_sel.contacto_preferente(fecha_evaluacion)
        contacto_str = (
            f"{contacto_pref.nombre} ({contacto_pref.tipo.value}) — Tel: {contacto_pref.telefono.enmascarado() if contacto_pref.telefono else 'Sin teléfono'}"
            if contacto_pref
            else "No registrado"
        )

        st.markdown(
            f"""
            <div class="passport-sheet">
                <div class="passport-header-box">
                    <div>
                        <div style="font-size:0.72rem;color:#4a5568;font-weight:700;">INSTITUTO NACIONAL DE SALUD DEL NIÑO SAN BORJA</div>
                        <div style="font-size:1.05rem;font-weight:700;color:#1a365d;">PASAPORTE DE SALUD 18+</div>
                        <div style="font-size:0.76rem;color:#718096;">Documento Oficial de Transferencia Asistencial Pediátrico a Adulto</div>
                    </div>
                    <img src="data:image/png;base64,{qr_b64}" width="65" height="65" style="border:1px solid #cbd5e0;border-radius:4px;" />
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.8rem;background:#f7fafc;padding:8px 10px;border-radius:4px;border:1px solid #e2e8f0;margin-bottom:8px;">
                    <div><strong>Paciente:</strong> {paciente_sel.id}</div>
                    <div><strong>Edad actual:</strong> {fila_sel.edad} años</div>
                    <div><strong>Procedencia:</strong> {paciente_sel.procedencia or 'No registrada'}</div>
                    <div><strong>Seguro:</strong> {paciente_sel.tipo_seguro.value}</div>
                </div>

                <div class="passport-section-title">1. Diagnósticos Clínicos Activos</div>
                <div style="font-size:0.82rem;color:#1a202c;margin-bottom:3px;"><strong>Principal:</strong> {dx_p_txt}</div>
                {''.join(f'<div style="font-size:0.82rem;color:#2d3748;margin-bottom:2px;">• {d.codigo} — {d.descripcion}</div>' for d in paciente_sel.diagnosticos if not d.es_principal)}

                <div class="passport-section-title">2. Medicación y Tratamiento Actual</div>
                {''.join(f'<div style="font-size:0.82rem;color:#2d3748;margin-bottom:2px;">• {m.texto_seguro()}</div>' for m in paciente_sel.medicamentos) if paciente_sel.medicamentos else '<div style="font-size:0.82rem;color:#718096;">Sin medicación activa registrada.</div>'}

                <div class="passport-section-title">3. Alertas para el Establecimiento Receptor</div>
                <div style="font-size:0.82rem;color:#2d3748;margin-bottom:2px;">• Garantizar continuidad del tratamiento sin interrupción de entrega de fármacos.</div>
                <div style="font-size:0.82rem;color:#2d3748;margin-bottom:2px;">• Contacto de enlace familiar: {contacto_str}</div>

                <div style="margin-top:14px;border-top:1px dashed #cbd5e0;padding-top:8px;font-size:0.68rem;color:#718096;">
                    Documento normado conforme a la RM 214-2018-MINSA y la NT 018-MINSA/DGSP-V.01. Requiere firma y sello del médico tratante para entrega formal.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.download_button(
            label="Descargar Pasaporte de Salud 18+ (PDF Oficial para Impresión)",
            data=pdf_bytes,
            file_name=f"Pasaporte_18_{paciente_sel.id}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )


# ───────────────────────────────────────────────────────────────────────────
# TAB 3: AVISOS Y CONTACTO FAMILIAR (WHATSAPP)
# ───────────────────────────────────────────────────────────────────────────
with tab_whatsapp:
    st.markdown("#### Asistente de Contacto y Mensajería Familiar")
    st.caption(
        "Generación de enlaces seguros de WhatsApp para coordinación con la familia. "
        "Garantía de privacidad: No se incluyen diagnósticos ni medicamentos sensibles en el texto."
    )

    fila_wsp = opciones_dict[id_seleccionado]
    pac_wsp = fila_wsp.paciente
    contacto_wsp = pac_wsp.contacto_preferente(fecha_evaluacion)

    col_w1, col_w2 = st.columns([1, 1], gap="large")

    with col_w1:
        st.markdown("##### Configuración del Mensaje")

        tipo_mensaje = st.selectbox(
            "Seleccionar motivo de comunicación:",
            options=[
                "Actualización de teléfono de contacto",
                "Citación a consulta de preparación de transición",
                "Entrega de Pasaporte 18+ e inicio de referencia",
            ],
        )

        # Número telefónico de prueba por defecto solicitado por el usuario: 975 864 664
        telefono_defecto = "975864664"
        telefono_ingresado = st.text_input(
            "Número telefónico del familiar (Perú):",
            value=telefono_defecto,
            help="Ingresa el número de 9 dígitos. Formato nacional e internacional aplicado automáticamente.",
        )

        # Limpiar caracteres no numéricos
        telefono_limpio = "".join(c for c in telefono_ingresado if c.isdigit())
        if not telefono_limpio:
            telefono_limpio = "975864664"

        if tipo_mensaje == "Actualización de teléfono de contacto":
            cuerpo_mensaje = (
                f"Estimada familia de {pac_wsp.id}, le saludamos del Instituto Nacional de Salud del Niño San Borja. "
                f"Nos comunicamos para validar su número telefónico de contacto y asegurar la continuidad de su atención. "
                f"Por favor, confírmenos si este sigue siendo su número principal. Muchas gracias."
            )
        elif tipo_mensaje == "Citación a consulta de preparación de transición":
            cuerpo_mensaje = (
                f"Estimada familia de {pac_wsp.id}, le saludamos del INSN San Borja. "
                f"Le recordamos su próxima consulta médica en el programa de preparación de transición a la atención adulta. "
                f"Es muy importante su asistencia para planificar su derivación oportuna. Por favor confírmenos su recepción."
            )
        else:
            cuerpo_mensaje = (
                f"Estimada familia de {pac_wsp.id}, le saludamos del INSN San Borja. "
                f"Su Pasaporte de Salud 18+ se encuentra listo para entrega en su próxima consulta médica. "
                f"Este documento facilitará su continuidad de tratamiento en el hospital de adultos. Los esperamos."
            )

        st.text_area("Contenido del mensaje a despachar:", value=cuerpo_mensaje, height=130)

        url_whatsapp = f"https://wa.me/51{telefono_limpio}?text={quote(cuerpo_mensaje)}"

        st.markdown(
            f"""
            <a href="{url_whatsapp}" target="_blank" style="text-decoration:none;">
                <div style="background-color:#2e7d32;color:#ffffff;text-align:center;padding:10px 16px;border-radius:4px;font-weight:700;font-size:0.9rem;margin-top:10px;">
                    Abrir Chat de WhatsApp (+51 {telefono_limpio[:3]} {telefono_limpio[3:6]} {telefono_limpio[6:]})
                </div>
            </a>
            """,
            unsafe_allow_html=True,
        )

    with col_w2:
        st.markdown("##### Protección de Datos y Privacidad Asistencial")
        st.info(
            "**Cumplimiento estricto de la Ley 29733 (Protección de Datos Personales):**\n\n"
            "- El mensaje omite deliberadamente términos diagnósticos sensibles (ej. 'fibrosis', 'insuficiencia renal', 'cáncer').\n"
            "- No se detallan dosis ni nombres de medicamentos por canales de mensajería externa.\n"
            "- El envío se canaliza a través de la cuenta oficial del establecimiento o del personal asistencial autorizado.",
        )


# ───────────────────────────────────────────────────────────────────────────
# TAB 4: SEGUIMIENTO Y CIERRE DE CICLO
# ───────────────────────────────────────────────────────────────────────────
with tab_ciclo:
    st.markdown("#### Seguimiento y Cierre de la Transferencia")
    st.caption("Trazabilidad de la referencia institucional hasta verificar la primera consulta en el hospital de adultos.")

    col_t1, col_t2 = st.columns([3, 2], gap="large")

    with col_t1:
        st.markdown(f"##### Estado de Transferencia: Paciente **{paciente_sel.id}**")

        st.markdown(
            f"""
            <div class="timeline-box">
                <div class="timeline-entry">
                    <div style="font-weight:700;color:#1a365d;">1. Emisión del Pasaporte de Salud 18+</div>
                    <div style="font-size:0.8rem;color:#4a5568;">Generado en consulta especializada INSN SB.</div>
                </div>
                <div class="timeline-entry">
                    <div style="font-weight:700;color:#1a365d;">2. Registro en Sistema de Referencias (REFCON)</div>
                    <div style="font-size:0.8rem;color:#4a5568;">Solicitud enviada a hospital receptor de adultos.</div>
                </div>
                <div class="timeline-entry">
                    <div style="font-weight:700;color:#1a365d;">3. Aceptación por Establecimiento Receptor</div>
                    <div style="font-size:0.8rem;color:#4a5568;">Referencia aceptada. Pendiente asignación de fecha de cita.</div>
                </div>
                <div class="timeline-entry pending">
                    <div style="font-weight:700;color:#718096;">4. Programación de Primera Cita en Adultos</div>
                    <div style="font-size:0.8rem;color:#a0aec0;">Mediana estimada: 80 a 85 días según estadística regional.</div>
                </div>
                <div class="timeline-entry pending">
                    <div style="font-weight:700;color:#718096;">5. Confirmación de Cita Cumplida (Cierre de Ciclo)</div>
                    <div style="font-size:0.8rem;color:#a0aec0;">Verificación por contacto familiar o contrarreferencia formal.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_t2:
        st.markdown("##### Registrar Confirmación de Atención")
        st.write("Registra la verificación de la primera consulta cumplida:")

        fuente_conf = st.radio(
            "Medio de verificación:",
            options=[
                "Confirmación telefónica con la familia / paciente",
                "Contrarreferencia formal recibida del hospital receptor",
            ],
        )
        fecha_atencion = st.date_input("Fecha de atención realizada:", value=fecha_evaluacion)

        if st.button("Registrar Transferencia Efectiva", type="primary", use_container_width=True):
            st.success(f"Transferencia del paciente {paciente_sel.id} confirmada exitosamente como CITA CUMPLIDA.")


# ───────────────────────────────────────────────────────────────────────────
# TAB 5: DIGITALIZACIÓN DE HOJA DE REFERENCIA
#
# El INSN lo lleva casi todo en papel. Esta pantalla es el punto de entrada:
# un escaneo entra, y lo que sale NO es "los datos ya digitalizados" sino
# "los datos, y cuáles no me creo". Esa segunda parte es el aporte.
# ───────────────────────────────────────────────────────────────────────────
with tab_digital:
    st.markdown("#### Digitalización Asistida de Hoja de Referencia")
    st.caption(
        "Lectura automática de documentos escaneados con verificación en tres capas. "
        "El procesamiento nunca sale a un servicio externo: el modelo corre en una "
        "máquina del equipo."
    )

    _nivel, _mensaje = _donde_corre_el_modelo()
    (st.success if _nivel == "success" else st.warning)(_mensaje)

    if _CORPUS_ES_DEMO:
        st.info(
            "Estás viendo la **muestra versionada** del corpus (4 documentos de 12). "
            "El corpus completo se genera en local y no se sube al repositorio; "
            "esta muestra existe para que la pantalla funcione en el despliegue."
        )

    if not _CORPUS_DISPONIBLE:
        st.warning(
            "No hay corpus de documentos generado todavía. "
            "Genera uno con:  `python -m relevo.interfaz.cli.generar_corpus --n 12`"
        )
    else:
        col_sel, col_est = st.columns([2, 3], gap="large")

        with col_sel:
            doc_id = st.selectbox(
                "Documento escaneado:",
                options=[m.id for m in _CORPUS.muestras()],
                format_func=lambda d: f"{d}  ·  {_CORPUS.variante_de(d)}",
            )
            ruta_img = SISTEMA.corpus.ruta_imagen(doc_id)
            if ruta_img is not None:
                st.image(str(ruta_img), caption=f"{doc_id}.jpg", width="stretch")

        with col_est:
            # Una relectura en vivo sustituye a la caché solo durante esta
            # sesión del navegador: el archivo en disco se deja intacto.
            _en_vivo: dict[str, str] = st.session_state.setdefault("lecturas_vivo", {})
            if doc_id in _en_vivo:
                resultado = _CORPUS.releer_texto(doc_id, _en_vivo[doc_id])
            else:
                resultado = _CORPUS.leer_cacheado(doc_id)

            if resultado is None:
                st.info(
                    "Este documento aún no se ha leído. La transcripción con el modelo "
                    "tarda alrededor de dos minutos en CPU."
                )
                if SISTEMA.lector_disponible:
                    if st.button("Leer con el modelo ahora", type="primary"):
                        with st.spinner(
                            f"Transcribiendo con {SISTEMA.nombre_lector}…"
                        ):
                            _CORPUS.leer_en_vivo(doc_id)
                        st.rerun()
                else:
                    st.caption(
                        "No hay ningún modelo alcanzable, así que este documento "
                        "no se puede leer ahora. Elige otro: los demás ya tienen "
                        "su transcripción guardada."
                    )
            else:
                if resultado.fue_en_vivo:
                    st.success(
                        f"Transcripción recién producida por "
                        f"`{SISTEMA.nombre_lector}` en esta sesión."
                    )
                else:
                    st.caption(f"Transcripción obtenida de: {resultado.origen}")

                # POR QUE EL BOTON SIGUE AQUI CON LA TRANSCRIPCION YA HECHA
                # La cache existe para que la pantalla abra al instante, pero
                # deja al modelo invisible: quien mira la demo ve texto ya
                # puesto y no tiene forma de comprobar que hay algo leyendo.
                # Este boton es la prueba en directo, y es la razon de que la
                # cache no baste por si sola.
                if SISTEMA.lector_disponible:
                    if st.button(
                        "Volver a leer en vivo con el modelo",
                        key=f"revivo_{doc_id}",
                        help=(
                            "Ejecuta el modelo sobre esta imagen ahora mismo. "
                            "Tarda unos dos minutos en CPU. No borra la "
                            "transcripción guardada."
                        ),
                    ):
                        with st.spinner(
                            f"Transcribiendo con {SISTEMA.nombre_lector} — "
                            "esto tarda un par de minutos…"
                        ):
                            _en_vivo[doc_id] = _CORPUS.leer_en_vivo(
                                doc_id, cachear=False
                            ).documento.texto
                        st.rerun()

                lectura = resultado.documento
                verdad = resultado.verdad

                st.markdown("##### Verificación campo por campo")
                st.caption(
                    "Corrige lo que haga falta mirando el escaneo de la izquierda. "
                    "Ningún campo se da por bueno hasta que una persona lo confirma."
                )

                aciertos = revisiones = errores = 0
                editados: dict[str, tuple[str, str | None]] = {}
                veredictos: dict[str, Veredicto] = {}
                por_nombre = {c.nombre: c for c in lectura.campos}

                def _pinta(nombre: str, v: Veredicto) -> None:
                    """Feedback bajo el campo. El color dice qué hacer, no juzga."""
                    if v.estado is Estado.VACIO:
                        return
                    tono = {
                        Estado.VALIDO: "#22543d",
                        Estado.INCOMPLETO: "#9c4221",
                        Estado.ERRONEO: "#9b2c2c",
                    }[v.estado]
                    st.markdown(
                        f"<div style='font-size:0.72rem;color:{tono};margin-top:-10px;"
                        f"margin-bottom:6px;'>{v.estado.icono} {v.mensaje}</div>",
                        unsafe_allow_html=True,
                    )

                def _leido(nombre: str) -> str:
                    c = por_nombre.get(nombre)
                    return (c.crudo or "—") if c else "—"

                for campo in lectura.campos:
                    esperado = verdad.get(campo.nombre)
                    if esperado is None:
                        continue
                    if campo.valor is None:
                        revisiones += 1
                    elif str(campo.valor).strip() == str(esperado).strip():
                        aciertos += 1
                    else:
                        errores += 1

                col_izq, col_der = st.columns(2, gap="medium")

                # ── Campos con regla propia ─────────────────────────────────
                with col_izq:
                    v_dni = st.text_input(
                        "DNI del paciente", value=por_nombre["dni"].valor or "",
                        key=f"d_dni_{doc_id}", placeholder="8 dígitos",
                        help=f"el modelo leyó: {_leido('dni')}",
                    )
                    ver = validar_dni(v_dni)
                    _pinta("dni", ver)
                    editados["dni"], veredictos["dni"] = (v_dni, por_nombre["dni"].valor), ver

                    v_cel = st.text_input(
                        "Celular de contacto", value=por_nombre["celular"].valor or "",
                        key=f"d_cel_{doc_id}", placeholder="9 dígitos, empieza en 9",
                        help=f"el modelo leyó: {_leido('celular')}",
                    )
                    ver = validar_celular(v_cel)
                    _pinta("celular", ver)
                    editados["celular"], veredictos["celular"] = (v_cel, por_nombre["celular"].valor), ver

                    v_hc = st.text_input(
                        "N.º de historia clínica", value=por_nombre["numero_hc"].valor or "",
                        key=f"d_hc_{doc_id}", placeholder="solo dígitos",
                        help=f"el modelo leyó: {_leido('numero_hc')}",
                    )
                    ver = validar_numero_hc(v_hc)
                    _pinta("numero_hc", ver)
                    editados["numero_hc"], veredictos["numero_hc"] = (v_hc, por_nombre["numero_hc"].valor), ver

                with col_der:
                    # Calendario en vez de texto: una fecha tecleada admite
                    # 31/02 y admite el formato americano. El calendario no.
                    leida = por_nombre["fecha_nacimiento"].valor
                    try:
                        inicial = (
                            datetime.strptime(leida, "%d/%m/%Y").date() if leida else None
                        )
                    except ValueError:
                        inicial = None
                    v_fnac = st.date_input(
                        "Fecha de nacimiento",
                        value=inicial,
                        min_value=date(fecha_evaluacion.year - 100, 1, 1),
                        max_value=fecha_evaluacion,
                        format="DD/MM/YYYY",
                        key=f"d_fn_{doc_id}",
                        help=f"el modelo leyó: {_leido('fecha_nacimiento')}",
                    )
                    ver = validar_fecha_nacimiento(v_fnac, fecha_evaluacion)
                    _pinta("fecha_nacimiento", ver)
                    editados["fecha_nacimiento"] = (
                        v_fnac.strftime("%d/%m/%Y") if v_fnac else "", leida
                    )
                    veredictos["fecha_nacimiento"] = ver

                    for nom, etiq in (
                        ("establecimiento_origen", "Establecimiento de origen"),
                        ("establecimiento_destino", "Establecimiento de destino"),
                    ):
                        # Busqueda sobre el registro nacional (RENIPRESS), no
                        # sobre una lista escrita a mano: un paciente puede venir
                        # referido desde una posta de Ucayali, y obligar a marcar
                        # "Otro" en ese caso llena la base de texto libre.
                        leido_cat = por_nombre[nom].valor or ""
                        consulta = st.text_input(
                            f"{etiq} — busca en el registro nacional",
                            value=leido_cat,
                            key=f"d_{nom}_q_{doc_id}",
                            placeholder="parte del nombre o la sigla (ej. INSN)",
                            help=f"el modelo leyó: {_leido(nom)}",
                        )
                        candidatos = (
                            SISTEMA.buscar_establecimiento(consulta, limite=6)
                            if consulta
                            else ()
                        )
                        if candidatos:
                            etiquetas = [e.etiqueta for e in candidatos] + [ETIQUETA_OTRO]
                            sel = st.radio(
                                f"coincidencias_{nom}",
                                options=etiquetas,
                                key=f"d_{nom}_sel_{doc_id}",
                                label_visibility="collapsed",
                            )
                            if sel == ETIQUETA_OTRO:
                                elegido = consulta
                                st.markdown(
                                    "<div style='font-size:0.72rem;color:#9c4221;"
                                    "margin-top:-6px;'>⚠ no figura en RENIPRESS · "
                                    "pendiente de conciliar</div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                elegido = next(
                                    e.nombre for e in candidatos if e.etiqueta == sel
                                )
                                cod = next(
                                    e.codigo for e in candidatos if e.etiqueta == sel
                                )
                                st.markdown(
                                    f"<div style='font-size:0.72rem;color:#22543d;"
                                    f"margin-top:-6px;'>✅ RENIPRESS {cod}</div>",
                                    unsafe_allow_html=True,
                                )
                        else:
                            elegido = consulta
                            if consulta:
                                st.markdown(
                                    "<div style='font-size:0.72rem;color:#9c4221;"
                                    "margin-top:-10px;'>⚠ sin coincidencias en RENIPRESS · "
                                    "pendiente de conciliar</div>",
                                    unsafe_allow_html=True,
                                )
                        editados[nom] = (elegido, leido_cat)
                        veredictos[nom] = Veredicto(Estado.VALIDO)

                # ── Campos de texto libre ───────────────────────────────────
                col_ap1, col_ap2 = st.columns(2)
                for col, nom, etiq in (
                    (col_ap1, "apellido_paterno", "Apellido paterno"),
                    (col_ap2, "apellido_materno", "Apellido materno"),
                ):
                    with col:
                        val = st.text_input(
                            etiq, value=por_nombre[nom].valor or "",
                            key=f"d_{nom}_{doc_id}",
                            help=f"el modelo leyó: {_leido(nom)}",
                        )
                        editados[nom] = (val, por_nombre[nom].valor)
                        veredictos[nom] = Veredicto(Estado.VALIDO)

                st.divider()
                bloqueantes = [n for n, v in veredictos.items() if v.bloquea_emision]
                incompletos = [
                    n for n, v in veredictos.items() if v.estado is Estado.INCOMPLETO
                ]
                if bloqueantes:
                    st.error(
                        "No se puede emitir el acta: corrige "
                        + ", ".join(f"**{b}**" for b in bloqueantes)
                    )
                elif incompletos:
                    st.warning(
                        "Campos a medio escribir: " + ", ".join(incompletos)
                    )

                revisor = st.text_input(
                    "Nombre de quien revisa (queda registrado en el acta):",
                    key=f"rev_{doc_id}",
                )
                st.caption(
                    "El sistema registra el nombre, la fecha y la hora, pero **no verifica "
                    "la identidad**: eso exige credenciales de acceso o firma digital "
                    "certificada (RENIEC). Pendiente para el piloto."
                )
                confirmar = st.button(
                    "Confirmar digitalización y generar acta",
                    type="primary",
                    disabled=bool(bloqueantes) or not revisor.strip(),
                    key=f"btn_acta_{doc_id}",
                )

                if confirmar:
                    # Toda la logica de clasificar y armar el acta vive en el
                    # caso de uso. Aqui solo se recogen los valores y se pinta.
                    acta, pdf = SISTEMA.confirmar.ejecutar(
                        documento_id=doc_id,
                        valores_finales={n: v for n, (v, _) in editados.items()},
                        valores_leidos={n: leido for n, (_, leido) in editados.items()},
                        revisor=revisor,
                    )
                    st.success(
                        f"Digitalización confirmada por **{acta.revisor}** el "
                        f"{acta.momento.strftime('%d/%m/%Y a las %H:%M')} · "
                        f"{acta.automaticos} campos aceptados de la lectura "
                        f"automática y {acta.corregidos} corregidos a mano."
                    )
                    pendientes = [
                        c.nombre
                        for c in acta.campos
                        if c.nombre.startswith("establecimiento")
                        and c.valor_final
                        and not SISTEMA.establecimiento_en_catalogo(c.valor_final)
                    ]
                    if pendientes:
                        st.warning(
                            "Queda pendiente de conciliar contra RENIPRESS: "
                            + ", ".join(pendientes)
                        )
                    st.session_state[f"acta_{doc_id}"] = pdf

                if st.session_state.get(f"acta_{doc_id}"):
                    st.download_button(
                        "Descargar acta de digitalización (PDF)",
                        data=st.session_state[f"acta_{doc_id}"],
                        file_name=f"acta_digitalizacion_{doc_id}.pdf",
                        mime="application/pdf",
                        width="stretch",
                    )

                total = aciertos + revisiones + errores
                if total:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Capturados", f"{aciertos}/{total}")
                    c2.metric("A revisión humana", f"{revisiones}/{total}")
                    c3.metric("Error no detectado", f"{errores}/{total}")

                st.markdown(
                    "<div style='background:#edf2f7;border-left:4px solid #4a5568;"
                    "padding:10px 14px;margin-top:12px;font-size:0.8rem;color:#2d3748;'>"
                    "<strong>Cómo leer esta tabla.</strong> Un campo en "
                    "<strong>REVISAR</strong> no es un fallo del sistema: es el sistema "
                    "diciendo que no se cree lo que leyó, y pidiendo que una persona lo "
                    "confirme. El único resultado malo es <strong>ERROR</strong> — un dato "
                    "equivocado que pasó como bueno. Hoy, sin este sistema, todos los "
                    "campos entran a REFCON tecleados a mano y sin ninguna verificación."
                    "</div>",
                    unsafe_allow_html=True,
                )

                with st.expander("Ver transcripción completa del documento"):
                    st.text(texto[:4000])

    st.markdown(
        "<div style='background:#f7fafc;border:1px solid #cbd5e0;border-radius:6px;"
        "padding:14px;margin-top:16px;'>"
        "<div style='font-weight:700;color:#1a365d;font-size:0.9rem;'>Las tres verificaciones encadenadas</div>"
        "<div style='font-size:0.82rem;color:#4a5568;margin-top:6px;line-height:1.6;'>"
        "• <strong>Formato:</strong> un DNI de 7 dígitos o un celular que en realidad es "
        "una fecha se rechazan solos.<br/>"
        "• <strong>Catálogo:</strong> «NISN San Borja» supera cualquier formato, pero no "
        "existe en el catálogo de establecimientos.<br/>"
        "• <strong>Doble lectura:</strong> dos modelos distintos leen el mismo documento; "
        "donde discrepan, el campo va a revisión. Es lo único que detecta un dígito "
        "cambiado que deja un número válido."
        "</div></div>",
        unsafe_allow_html=True,
    )


# ───────────────────────────────────────────────────────────────────────────
# TAB 6: CRITERIOS CLÍNICOS E INTEROPERABILIDAD NACIONAL (SIN JSON/YAML EXPUESTO)
# ───────────────────────────────────────────────────────────────────────────
with tab_config:
    st.markdown("#### Criterios Clínicos e Integración Nacional")
    st.caption("Criterios institucionales aprobados por el INSN San Borja e integración con el Ministerio de Salud.")

    col_p1, col_p2 = st.columns(2, gap="large")

    with col_p1:
        st.markdown("##### Criterios Institucionales de Priorización")
        st.write("El orden de atención y prioridad se determina en base a 7 factores clínicos objetivos:")

        criterios = [
            ("1. Tiempo restante para los 18 años (Factor dominante)", "Los pacientes a menos de 6 a 12 meses de cumplir la mayoría de edad tienen prioridad máxima para evitar la interrupción de tratamiento."),
            ("2. Severidad diagnóstica", "Diagnósticos de alto riesgo vital o complejidad según el listado de enfermedades raras y catastróficas (RM 478-2026-MINSA)."),
            ("3. Compromiso multisistémico u órganos afectados", "Pacientes con afección en múltiples sistemas orgánicos (renal, cardiovascular, respiratorio, neurológico)."),
            ("4. Dependencia de tecnología médica", "Pacientes dependientes de diálisis, oxígeno domiciliario, traqueostomía o ventilación mecánica."),
            ("5. Ausencia de contacto familiar actualizado", "Casos donde el teléfono del familiar no se ha verificado en el último año, con riesgo de pérdida de contacto."),
            ("6. Residencia fuera de Lima Metropolitana", "Pacientes de regiones que requieren mayor tiempo de coordinación para traslados y citas."),
            ("7. Riesgo de pérdida de cobertura de seguro", "Adolescentes con regímenes de seguro sujetos a evaluación de incapacidad al cumplir 18 años."),
        ]

        for tit, desc in criterios:
            st.markdown(
                f"""
                <div class="criterion-card">
                    <div class="criterion-title">{tit}</div>
                    <div class="criterion-desc">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_p2:
        st.markdown("##### Integración con el Sistema Nacional de Salud (MINSA - RENHICE)")
        st.write(
            "El sistema Relevo genera automáticamente la información del paciente bajo el estándar clínico nacional "
            "**HL7 FHIR R4 (Perfil CorePE)**, garantizando que el historial de traspaso pueda ser consumido por "
            "cualquier hospital receptor del país o por el Registro Nacional de Historias Clínicas Electrónicas (RENHICE)."
        )

        st.markdown(
            """
            <div style="background:#f7fafc;border:1px solid #cbd5e0;border-radius:6px;padding:14px;margin-bottom:14px;">
                <div style="font-weight:700;color:#1a365d;font-size:0.9rem;">Componentes del Paquete de Interoperabilidad:</div>
                <div style="font-size:0.82rem;color:#4a5568;margin-top:6px;line-height:1.5;">
                    • <strong>Resumen de Paciente:</strong> Identificador seguro y datos demográficos.<br/>
                    • <strong>Diagnósticos Codificados:</strong> Diagnósticos activos en estándar CIE-10 / Orphanet.<br/>
                    • <strong>Esquema Farmacológico:</strong> Lista de medicamentos con posología y vías de administración.<br/>
                    • <strong>Alergias y Advertencias:</strong> Reacciones adversas medicamentosas documentadas.<br/>
                    • <strong>Organización Emisora:</strong> INSN San Borja con firma médica de origen.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Generar archivo JSON estándar para descarga del área de informática si lo necesitan, pero sin mostrar código en pantalla
        fhir_dict = {
            "resourceType": "Bundle",
            "type": "document",
            "meta": {"profile": ["http://minsa.gob.pe/fhir/CorePE/BundleDocumento"]},
            "entry": [
                {"resource": {"resourceType": "Patient", "id": paciente_sel.id, "birthDate": paciente_sel.fecha_nacimiento.isoformat()}},
                {"resource": {"resourceType": "Condition", "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": paciente_sel.diagnostico_principal.codigo.valor if paciente_sel.diagnostico_principal else "ND"}]}}},
            ],
        }
        fhir_json_str = json.dumps(fhir_dict, indent=2, ensure_ascii=False)

        st.download_button(
            label="Descargar Ficha de Interoperabilidad FHIR (Para TI / Sistemas)",
            data=fhir_json_str,
            file_name=f"FHIR_CorePE_{paciente_sel.id}.json",
            mime="application/json",
            use_container_width=True,
        )

# ═══════════════════════════════════════════════════════════════════════════
# PIE DE PÁGINA FORMAL
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
st.caption(
    "Sistema Relevo · Instituto Nacional de Salud del Niño San Borja. "
    "Diseñado conforme a la RM 214-2018-MINSA y la NT 018-MINSA/DGSP-V.01. Todo dato mostrado corresponde a simulación clínica controlada."
)

