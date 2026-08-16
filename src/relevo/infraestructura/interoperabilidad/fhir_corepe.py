from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import Pasaporte
from relevo.dominio.puertos.exportacion import (
    ExportadorInteroperable,
    ResultadoValidacion,
)


class ExportadorFHIRCorePE(ExportadorInteroperable):
    """Generador y validador de Bundles FHIR R4 CorePE del MINSA."""

    @property
    def perfil(self) -> str:
        return "HL7 FHIR CorePE R4 (MINSA) / IPS"

    def exportar_paciente(self, paciente: Paciente, pasaporte: Pasaporte) -> str:
        """Serializa el pasaporte y la ficha del paciente a un Bundle FHIR document."""
        # Regla 4: El medico siempre firma antes de cualquier salida clinica oficial
        pasaporte.exigir_firma()

        ahora_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        id_doc = f"relevo-doc-{paciente.id.lower()}-{pasaporte.version.value}"
        id_paciente_fhir = f"paciente-{paciente.id.lower()}"
        id_practitioner_fhir = "medico-tratante-insn"
        id_org_fhir = "org-insn-san-borja"

        # 1. Organization: INSN San Borja
        org_resource = {
            "resourceType": "Organization",
            "id": id_org_fhir,
            "meta": {
                "profile": ["http://minsa.gob.pe/fhir/CorePE/StructureDefinition/OrganizacionCorePE"]
            },
            "identifier": [
                {
                    "system": "http://minsa.gob.pe/renipress",
                    "value": "00012345",
                }
            ],
            "name": "Instituto Nacional de Salud del Niño San Borja",
            "telecom": [{"system": "phone", "value": "+5112300600"}],
            "address": [{"city": "Lima", "state": "Lima", "country": "PE"}],
        }

        # 2. Practitioner: Médico Firmante
        medico_nombre = pasaporte.firma.nombre_medico if pasaporte.firma else "Médico Tratante"
        colegiatura = pasaporte.firma.colegiatura if pasaporte.firma else "ND"
        practitioner_resource = {
            "resourceType": "Practitioner",
            "id": id_practitioner_fhir,
            "meta": {
                "profile": ["http://minsa.gob.pe/fhir/CorePE/StructureDefinition/ProfesionalCorePE"]
            },
            "identifier": [
                {
                    "system": "http://cmp.org.pe/colegiatura",
                    "value": colegiatura,
                }
            ],
            "name": [{"text": medico_nombre}],
        }

        # 3. Patient: Paciente de la transición
        patient_resource: dict[str, Any] = {
            "resourceType": "Patient",
            "id": id_paciente_fhir,
            "meta": {
                "profile": ["http://minsa.gob.pe/fhir/CorePE/StructureDefinition/PacienteCorePE"]
            },
            "identifier": [
                {
                    "system": "http://relevo.minsa.gob.pe/identificador-interno",
                    "value": paciente.id,
                }
            ],
            "birthDate": paciente.fecha_nacimiento.isoformat(),
            "gender": "male" if paciente.sexo.lower() in ("m", "masculino") else ("female" if paciente.sexo.lower() in ("f", "femenino") else "other"),
            "managingOrganization": {"reference": f"Organization/{id_org_fhir}"},
        }
        if paciente.procedencia:
            patient_resource["address"] = [{"text": paciente.procedencia, "country": "PE"}]

        # 4. Conditions: Diagnósticos CIE-10
        condition_entries = []
        condition_refs = []
        for i, dx in enumerate(paciente.diagnosticos):
            c_id = f"diag-{paciente.id.lower()}-{i+1}"
            condition_refs.append({"reference": f"Condition/{c_id}"})
            c_res = {
                "resourceType": "Condition",
                "id": c_id,
                "meta": {
                    "profile": ["http://minsa.gob.pe/fhir/CorePE/StructureDefinition/DiagnosticoCorePE"]
                },
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active" if dx.activo else "resolved",
                        }
                    ]
                },
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                "code": "problem-list-item",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": dx.codigo.valor,
                            "display": dx.descripcion,
                        }
                    ],
                    "text": dx.descripcion,
                },
                "subject": {"reference": f"Patient/{id_paciente_fhir}"},
            }
            condition_entries.append({"fullUrl": f"urn:uuid:{c_id}", "resource": c_res})

        # 5. Medications: Medicamentos activos
        medication_entries = []
        med_refs = []
        for j, med in enumerate(paciente.medicamentos):
            m_id = f"med-{paciente.id.lower()}-{j+1}"
            med_refs.append({"reference": f"MedicationStatement/{m_id}"})
            m_res: dict[str, Any] = {
                "resourceType": "MedicationStatement",
                "id": m_id,
                "status": "active",
                "medicationCodeableConcept": {
                    "text": med.nombre,
                },
                "subject": {"reference": f"Patient/{id_paciente_fhir}"},
            }
            if med.dosis:
                m_res["dosage"] = [{"text": f"{med.dosis} {med.frecuencia or ''}".strip()}]
            medication_entries.append({"fullUrl": f"urn:uuid:{m_id}", "resource": m_res})

        # 6. Composition: Documento clínico cabecera
        sections = [
            {
                "title": "Diagnósticos Activos y Comorbilidades",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "11450-4",
                            "display": "Problem list - Reported",
                        }
                    ]
                },
                "entry": condition_refs,
            },
            {
                "title": "Medicamentos y Terapia Farmacológica",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "10160-0",
                            "display": "History of Medication use Narrative",
                        }
                    ]
                },
                "entry": med_refs,
            },
        ]

        # Agregar sección psicosocial si existe
        if paciente.psicosocial:
            sections.append(
                {
                    "title": "Aspectos Psicosociales y Red de Apoyo",
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "86529-5",
                                "display": "Social history Narrative",
                            }
                        ]
                    },
                    "text": {
                        "status": "generated",
                        "div": f"<div xmlns='http://www.w3.org/1999/xhtml'><p><b>Apoyo familiar:</b> {paciente.psicosocial.apoyo_familiar}</p><p><b>Escolaridad:</b> {paciente.psicosocial.escolaridad_ocupacion}</p><p><b>Autonomía:</b> {paciente.psicosocial.autonomia_autocuidado}</p></div>",
                    },
                }
            )

        composition_resource = {
            "resourceType": "Composition",
            "id": id_doc,
            "meta": {
                "profile": ["http://minsa.gob.pe/fhir/CorePE/StructureDefinition/CompositionDocumento"]
            },
            "status": "final",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "60591-5",
                        "display": "Patient summary Document",
                    }
                ],
                "text": f"Pasaporte de Salud 18+ — Transición Asistencial ({pasaporte.version.value.upper()})",
            },
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "11488-4",
                            "display": "Consultation note",
                        }
                    ]
                }
            ],
            "subject": {"reference": f"Patient/{id_paciente_fhir}"},
            "date": ahora_iso,
            "author": [{"reference": f"Practitioner/{id_practitioner_fhir}"}],
            "title": "Resumen Clínico para Transferencia Asistencial Pediátrico-Adulto",
            "custodian": {"reference": f"Organization/{id_org_fhir}"},
            "section": sections,
        }

        # 7. Ensamblar Bundle
        entries = [
            {"fullUrl": f"urn:uuid:{id_doc}", "resource": composition_resource},
            {"fullUrl": f"urn:uuid:{id_paciente_fhir}", "resource": patient_resource},
            {"fullUrl": f"urn:uuid:{id_practitioner_fhir}", "resource": practitioner_resource},
            {"fullUrl": f"urn:uuid:{id_org_fhir}", "resource": org_resource},
        ]
        entries.extend(condition_entries)
        entries.extend(medication_entries)

        bundle = {
            "resourceType": "Bundle",
            "id": f"bundle-transicion-{paciente.id.lower()}",
            "meta": {
                "profile": ["http://minsa.gob.pe/fhir/CorePE/StructureDefinition/BundleDocumento"]
            },
            "identifier": {
                "system": "http://relevo.minsa.gob.pe/bundle-transicion",
                "value": f"RELEVO-{paciente.id}-{pasaporte.version.value.upper()}",
            },
            "type": "document",
            "timestamp": ahora_iso,
            "entry": entries,
        }

        return json.dumps(bundle, indent=2, ensure_ascii=False)

    def validar(self, documento_json: str) -> ResultadoValidacion:
        """Validación local de estructura conforme a especificación FHIR R4 Document."""
        errores: list[str] = []
        avisos: list[str] = []

        try:
            doc = json.loads(documento_json)
        except Exception as e:
            return ResultadoValidacion(
                valido=False,
                errores=(f"JSON no es valido: {e}",),
                validador="validacion local de estructura",
            )

        if doc.get("resourceType") != "Bundle":
            errores.append("El recurso raiz debe ser de tipo 'Bundle'")
        if doc.get("type") != "document":
            errores.append("El tipo de Bundle debe ser 'document'")

        entries = doc.get("entry", [])
        if not entries:
            errores.append("El Bundle no contiene ninguna entrada en 'entry'")
        else:
            primera = entries[0].get("resource", {})
            if primera.get("resourceType") != "Composition":
                errores.append("La primera entrada del Bundle document debe ser un recurso 'Composition'")

        tipos_encontrados = {e.get("resource", {}).get("resourceType") for e in entries}
        for obligatorio in ("Composition", "Patient", "Practitioner", "Organization"):
            if obligatorio not in tipos_encontrados:
                errores.append(f"Falta el recurso obligatorio '{obligatorio}' en el Bundle")

        if not errores:
            avisos.append("Estructura basica valida segun HL7 FHIR CorePE R4 (MINSA)")

        return ResultadoValidacion(
            valido=len(errores) == 0,
            errores=tuple(errores),
            avisos=tuple(avisos),
            validador="validacion local de estructura",
        )
