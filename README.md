# Relevo

**Sistema de acompañamiento de la transición pediátrico-adulto**
Reto 1 — Hackathon INSN San Borja · *"Puente 18+"* · **Equipo Avellana**

---

## El problema en una frase

El INSN San Borja no atiende a mayores de 18 años bajo ninguna circunstancia. Cada año, del orden de doscientos pacientes con enfermedades crónicas, raras o complejas cruzan esa frontera — y nadie sabe cuántos llegan al otro lado.

> El problema no se ve porque pasa de a uno. Se pierde un paciente por día. Nadie lo nota. A fin de año son doscientas personas sin continuidad de atención.

---

## Qué hace el sistema

1. **Un proceso nocturno** que corre solo, prioriza la cohorte de 14 a 18 años con un índice explicable, y prepara lo que haga falta.
2. **Avisos que llegan solos** — correo al equipo clínico, mensajes de WhatsApp listos para enviar a la familia. Nadie tiene que revisar una pantalla nueva.
3. **El Pasaporte de Salud 18+** — un documento impreso que el paciente se lleva, generado en tres versiones escalonadas a los 14, 16 y 17 años.
4. **Seguimiento del ciclo** hasta confirmar que el paciente efectivamente llegó al servicio de adultos.

**No toca el sistema del hospital.** Solo lectura, por un adaptador intercambiable.

---

## Principios

| Principio | Qué significa |
|---|---|
| **El sistema busca a la persona** | Ninguna pantalla es de revisión obligatoria diaria. Los avisos llegan. |
| **Determinístico donde importa la seguridad** | La detección es un motor de reglas auditable, no un modelo opaco. |
| **El médico siempre firma** | Ninguna salida clínica se emite sin revisión humana. |
| **Cero pesos** | Sin APIs de pago, sin licencias, sin proceso de adquisición. |
| **Ningún dato real** | Todo sintético mientras dure el hackathon. |

---

## Estado

🚧 En construcción. Ver `docs/PLAN_TECNICO.md` §12 para el orden de trabajo.

---

## Documentación

| Archivo | Para qué |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Reglas operativas para el agente de código |
| [`docs/PLAN_TECNICO.md`](docs/PLAN_TECNICO.md) | **La especificación técnica completa** |
| [`docs/DOSSIER.md`](docs/DOSSIER.md) | El proyecto completo, con glosario — para compartir con el equipo |
| [`docs/VACIOS_ORIGINALIDAD_IMPACTO.md`](docs/VACIOS_ORIGINALIDAD_IMPACTO.md) | Reflexión crítica interna |
| [`docs/PREGUNTAS_MENTOR.md`](docs/PREGUNTAS_MENTOR.md) | Preguntas abiertas al mentor del INSN |
| [`docs/maqueta_mvp.html`](docs/maqueta_mvp.html) | Maqueta visual de las pantallas |

---

## Cómo levantarlo

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
python -m relevo.interfaz.cli.generar_cohorte --n 300
python -m relevo.interfaz.cli.correr_noche
streamlit run src/relevo/interfaz/web/app.py
```

---

## Fuentes que sostienen el diseño

- **RM 478-2026-MINSA** (11 may 2026) — listado vigente de enfermedades raras: 558 diagnósticos en CIE-10
- **Complex Chronic Conditions v2** (Feudtner, *BMC Pediatrics*) — clasificación de condiciones crónicas complejas sobre CIE-10
- **HL7 FHIR CorePE** — guía de implementación nacional del MINSA, FHIR R4
- **NT 018-MINSA/DGSP-V.01** — Sistema de Referencia y Contrarreferencia
- **RM 214-2018-MINSA** — Gestión de la Historia Clínica
- **Got Transition — Six Core Elements** y **Ready Steady Go** (NHS)
- **TRAQ** — cuestionario de preparación, versión en español validada
- Estudio DIRIS Lima Norte (*Revista Médica Herediana*) — 19 951 referencias analizadas; **0.55 % de contrarreferencias**; mediana de espera aceptación→cita de **80–85 días**
