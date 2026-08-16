"""Test bloqueante: privacidad absoluta en el canal de WhatsApp.

CLAUDE.md y PLAN_TECNICO §8.4 / FUSION_RELEVO_INSTRUCCIONES §6.3 y §9:
Ningun mensaje de WhatsApp puede contener diagnosticos, codigos CIE-10,
nombres de medicamentos, dosis, resultados de laboratorio ni terminos clinicos
sensibles.

Ademas, comprueba arquitecturalmente que `wa.me` NO se construye en linea en
ningun archivo fuera del adaptador `CanalWhatsAppEnlace`.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from relevo.dominio.entidades.diagnostico import Contacto, TipoContacto
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.dominio.puertos.notificacion import Mensaje, TipoDestinatario
from relevo.infraestructura.notificacion.canal_archivo import CanalWhatsAppEnlace
from relevo.infraestructura.notificacion.plantillas_mensaje import (
    PLANTILLAS,
    TipoMensajeFamilia,
)

# Palabras y patrones prohibidos en cualquier mensaje que salga a una familia
LISTA_NEGRA_CLINICA = [
    # Diagnosticos y terminos clinicos
    "mucopolisacaridosis",
    "fibrosis",
    "quistica",
    "renal",
    "asma",
    "leucemia",
    "cancer",
    "tumor",
    "epilepsia",
    "hemofilia",
    "diabetes",
    "cardiopatia",
    "osteosarcoma",
    "cirrosis",
    "inmunodeficiencia",
    "down",
    "marfan",
    "fallot",
    "duchenne",
    "traqueostomia",
    "gastrostomia",
    "dialisis",
    "insuficiencia",
    "trasplante",
    "grave",
    "cronico",
    "cronica",
    "sindrome",
    # Medicamentos
    "idursulfasa",
    "salbutamol",
    "insulina",
    "prednisona",
    "ciclosporina",
    "enoxaparina",
    "metotrexato",
    "inmunoglobulina",
    "acido folico",
    # Unidades de dosis
    " mg",
    " mcg",
    " ml",
    " ui",
    "mg/kg",
]

PATRON_CIE10 = re.compile(r"\b[A-Z]\d{2}(\.\d{1,2})?\b")


def test_plantillas_no_contienen_terminos_sensibles() -> None:
    """Verifica que todas las plantillas para la familia esten 100% limpias."""
    paciente_id = "PAC-001"
    for tipo, plantilla in PLANTILLAS.items():
        assert not plantilla.contiene_datos_clinicos, (
            f"La plantilla {tipo.value} no debe declarar datos clinicos."
        )
        cuerpo = plantilla.componer(paciente_id).lower()
        texto_sin_id = cuerpo.replace(paciente_id.lower(), "")

        for termino in LISTA_NEGRA_CLINICA:
            assert termino not in texto_sin_id, (
                f"La plantilla {tipo.value} contiene el termino prohibido '{termino}'."
            )

        assert not PATRON_CIE10.search(texto_sin_id.upper()), (
            f"La plantilla {tipo.value} parece contener un codigo CIE-10."
        )


def test_canal_whatsapp_rechaza_mensajes_con_datos_clinicos(tmp_path: Path) -> None:
    """El adaptador rechaza cualquier mensaje marcado con datos clinicos."""
    canal = CanalWhatsAppEnlace(carpeta=tmp_path)
    tel = Telefono(numero="975864664")

    mensaje_invalido = Mensaje(
        destinatario="Familia",
        tipo_destinatario=TipoDestinatario.FAMILIA,
        asunto="Aviso",
        cuerpo="Su tratamiento de idursulfasa esta listo.",
        telefono=tel,
        contiene_datos_clinicos=True,
    )

    resultado = canal.despachar(mensaje_invalido)
    assert not resultado.despachado
    assert "RECHAZADO" in resultado.detalle
    assert not resultado.enlace_generado


def test_canal_whatsapp_despacha_mensaje_seguro_con_enlace(tmp_path: Path) -> None:
    """Un mensaje sin datos clinicos genera un enlace wa.me valido."""
    canal = CanalWhatsAppEnlace(carpeta=tmp_path)
    tel = Telefono(numero="975864664")
    paciente_id = "PAC-001"
    cuerpo = PLANTILLAS[TipoMensajeFamilia.PASAPORTE_LISTO].componer(paciente_id)

    mensaje = Mensaje(
        destinatario="Familia",
        tipo_destinatario=TipoDestinatario.FAMILIA,
        asunto="Pasaporte listo",
        cuerpo=cuerpo,
        telefono=tel,
        contiene_datos_clinicos=False,
    )

    resultado = canal.despachar(mensaje)
    assert resultado.despachado
    assert bool(resultado.enlace_generado)
    assert "https://wa.me/51975864664?text=" in resultado.enlace_generado

    texto_decodificado = unquote(resultado.enlace_generado).lower()
    texto_sin_id = texto_decodificado.replace(paciente_id.lower(), "")
    for termino in LISTA_NEGRA_CLINICA:
        assert termino not in texto_sin_id, (
            f"El enlace de WhatsApp contiene '{termino}'"
        )


def test_wa_me_solo_se_construye_en_el_adaptador() -> None:
    """Test de arquitectura: 'wa.me' NO debe aparecer fuera del adaptador.

    Garantiza que no haya construcciones paralelas en linea que esquiven la
    guarda de privacidad.
    """
    raiz = Path(__file__).resolve().parents[2]
    archivos_fuente = list((raiz / "src").rglob("*.py")) + list((raiz / "src").rglob("*.js"))

    archivos_con_wa_me: list[str] = []
    for archivo in archivos_fuente:
        rel = archivo.relative_to(raiz).as_posix()
        # El unico archivo autorizado a nombrar wa.me
        if rel == "src/relevo/infraestructura/notificacion/canal_archivo.py":
            continue
        contenido = archivo.read_text(encoding="utf-8", errors="ignore")
        if "wa.me/" in contenido or "https://wa.me" in contenido:
            archivos_con_wa_me.append(rel)

    assert not archivos_con_wa_me, (
        f"Se encontraron construcciones de 'wa.me' fuera de canal_archivo.py: {archivos_con_wa_me}. "
        "Todo WhatsApp debe pasar exclusivamente por CanalWhatsAppEnlace."
    )
