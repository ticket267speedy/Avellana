"""Tests para el exportador FHIR R4 conforme a CorePE (MINSA) / IPS.

CLAUDE.md y PLAN_TECNICO §11:
- El Bundle FHIR valida estructura R4 CorePE.
- Ningun Bundle se exporta sin firma médica (Regla 4).
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from relevo.dominio.entidades.diagnostico import Diagnostico, Medicamento, PerfilPsicosocial
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import Firma, Pasaporte, PasaporteSinFirma, VersionPasaporte
from relevo.dominio.objetos_valor.codigo_cie10 import CodigoCIE10
from relevo.infraestructura.interoperabilidad.fhir_corepe import ExportadorFHIRCorePE


@pytest.fixture
def paciente_demo() -> Paciente:
    p = Paciente(
        id="SINT-HUNTER-001",
        fecha_nacimiento=date(2008, 10, 15),
        sexo="M",
        procedencia="Lima",
    )
    p.diagnosticos.append(
        Diagnostico(
            codigo=CodigoCIE10("E76.1"),
            descripcion="Mucopolisacaridosis tipo II (Síndrome de Hunter)",
            es_principal=True,
        )
    )
    p.medicamentos.append(
        Medicamento(
            nombre="Idursulfasa",
            dosis="0.5 mg/kg",
            via="Intravenosa",
            frecuencia="Semanal",
            verificada_en_fuente=True,
        )
    )
    p.psicosocial = PerfilPsicosocial(
        apoyo_familiar="Madre cuidadora principal y red de apoyo activa",
        escolaridad_ocupacion="Secundaria completa en curso",
        autonomia_autocuidado="Toma medicación bajo supervisión",
    )
    return p


def test_exportar_sin_firma_lanza_excepcion(paciente_demo: Paciente) -> None:
    """Regla 4: El medico siempre firma antes de generar un documento oficial."""
    exportador = ExportadorFHIRCorePE()
    pasaporte_borrador = Pasaporte(
        paciente_id=paciente_demo.id,
        version=VersionPasaporte.V3_17,
        fecha_emision=date(2026, 8, 16),
    )

    with pytest.raises(PasaporteSinFirma):
        exportador.exportar_paciente(paciente_demo, pasaporte_borrador)


def test_exportar_bundle_fhir_completo(paciente_demo: Paciente) -> None:
    """Un pasaporte firmado genera un Bundle FHIR document valido."""
    exportador = ExportadorFHIRCorePE()
    pasaporte = Pasaporte(
        paciente_id=paciente_demo.id,
        version=VersionPasaporte.V3_17,
        fecha_emision=date(2026, 8, 16),
    )
    pasaporte.firmar(
        Firma(
            nombre_medico="Dra. Carmen Valdez",
            colegiatura="CMP 45120",
            fecha=date(2026, 8, 16),
        )
    )

    bundle_json = exportador.exportar_paciente(paciente_demo, pasaporte)
    assert isinstance(bundle_json, str)

    datos = json.loads(bundle_json)
    assert datos["resourceType"] == "Bundle"
    assert datos["type"] == "document"
    assert "http://minsa.gob.pe/fhir/CorePE/StructureDefinition/BundleDocumento" in datos["meta"]["profile"]

    entries = datos["entry"]
    assert len(entries) >= 5

    # Entrada 0 debe ser Composition
    comp = entries[0]["resource"]
    assert comp["resourceType"] == "Composition"
    assert comp["status"] == "final"

    # Validar que los recursos clave existen en el Bundle
    tipos = [e["resource"]["resourceType"] for e in entries]
    assert "Patient" in tipos
    assert "Practitioner" in tipos
    assert "Organization" in tipos
    assert "Condition" in tipos
    assert "MedicationStatement" in tipos

    # Validar codigo CIE-10
    condition = next(e["resource"] for e in entries if e["resource"]["resourceType"] == "Condition")
    assert condition["code"]["coding"][0]["system"] == "http://hl7.org/fhir/sid/icd-10"
    assert condition["code"]["coding"][0]["code"] == "E76.1"


def test_validacion_local_de_estructura(paciente_demo: Paciente) -> None:
    """El validador local comprueba la integridad del documento."""
    exportador = ExportadorFHIRCorePE()
    pasaporte = Pasaporte(
        paciente_id=paciente_demo.id,
        version=VersionPasaporte.V3_17,
        fecha_emision=date(2026, 8, 16),
    )
    pasaporte.firmar(
        Firma(
            nombre_medico="Dra. Carmen Valdez",
            colegiatura="CMP 45120",
            fecha=date(2026, 8, 16),
        )
    )

    bundle_json = exportador.exportar_paciente(paciente_demo, pasaporte)
    resultado = exportador.validar(bundle_json)

    assert resultado.valido is True
    assert len(resultado.errores) == 0
    assert "local" in resultado.validador


def test_validador_rechaza_documentos_mal_formados() -> None:
    exportador = ExportadorFHIRCorePE()
    res_invalido = exportador.validar('{"resourceType": "Patient"}')
    assert res_invalido.valido is False
    assert len(res_invalido.errores) > 0
