# Instrucciones para el agente de código — Proyecto Relevo

Este archivo se lee automáticamente al inicio de cada sesión. **`docs/PLAN_TECNICO.md` es la especificación completa: léelo antes de escribir código.**

---

## Qué es esto

**Relevo** — sistema de acompañamiento de la transición pediátrico-adulto para el INSN San Borja.
Reto 1 del Hackathon INSN ("Puente 18+"). Equipo Avellana.

Detecta pacientes crónicos, raros o complejos que se acercan a los 18 años; genera un documento de traspaso impreso; avisa por correo y WhatsApp; y sigue el ciclo de la derivación hasta confirmar que el paciente llegó al servicio de adultos.

**Restricción de contexto que define todo:** el INSN **no atiende a mayores de 18 años bajo ninguna circunstancia**. El corte es duro y en fecha exacta. Esto no es una demora de atención: es una interrupción total.

---

## Reglas inviolables

1. **Nunca datos reales de pacientes.** Todo sintético. `data/` no se versiona.
2. **Nada que cueste dinero.** Sin APIs de pago, sin licencias.
3. **Todo debe correr sin internet.** El wifi del evento va a fallar. `SinLLM` es el respaldo y se construye antes que cualquier proveedor de modelo.
4. **El médico siempre firma.** Ninguna salida clínica se emite sin revisión humana explícita.
5. **La regla de dependencia se respeta siempre.** Ver abajo.
6. **Identificadores y comentarios en español**, sin tildes ni ñ en identificadores.
7. **Cada umbral va comentado con su fuente.** Si un plazo es 120 días, el comentario dice de dónde salió.
8. **Nunca inventar una dosis.** Toda dosis extraída por el modelo debe aparecer literalmente en el texto fuente, o se descarta.

---

## Arquitectura: hexagonal (puertos y adaptadores)

```
   interfaz ────────┐
                    ├──►  aplicacion  ──►  dominio
   infraestructura ─┘                        ▲
                                             │
                    (define los puertos que ambos implementan)
```

**Las dependencias apuntan hacia adentro. Siempre.**

- `dominio/` — **no importa nada externo.** Ni SQLAlchemy, ni FastAPI, ni `requests`. Solo librería estándar y `dataclasses`.
- `aplicacion/` — importa `dominio`. Nada más.
- `infraestructura/` e `interfaz/` — importan hacia adentro e implementan los puertos que el dominio declaró.

`tests/test_arquitectura.py` verifica esta regla y **debe pasar siempre**.

**Por qué importa:** nuestra promesa ante el jurado es *"el núcleo no cambia, solo se cambia el adaptador de entrada"*. La arquitectura es lo que hace esa afirmación verificable en vez de retórica.

---

## Calidad de código

- Anotaciones de tipo en todo, sin excepciones
- `mypy --strict` limpio sobre `src/relevo/dominio/` y `src/relevo/aplicacion/`
- Pydantic v2 para validar todo lo que cruza una frontera
- `@dataclass(frozen=True)` para objetos de valor
- Tests del dominio sin mocks, sin base de datos, sin red

---

## Orden de construcción

Ver `docs/PLAN_TECNICO.md` §12. Resumen: **de adentro hacia afuera.**

Los bloques 1 a 6 son todo dominio y no dependen de nada externo — se construyen y prueban completos antes de decidir cualquier cosa de infraestructura.

**Criterio de aceptación no negociable del bloque 3:** cinco casos del Índice de Urgencia calculados a mano en papel deben coincidir con el código.

---

## Tests bloqueantes

| Test | Qué verifica |
|---|---|
| `tests/test_arquitectura.py` | El dominio no importa nada externo |
| `tests/dominio/test_calculadora_iut.py` | Los 5 casos hechos a mano coinciden |
| `tests/infraestructura/test_privacidad_whatsapp.py` | **Ningún mensaje de WhatsApp contiene diagnósticos, códigos CIE-10, medicamentos, dosis ni resultados** |
| `tests/infraestructura/test_fhir.py` | El Bundle valida contra HAPI FHIR |

---

## Lo que NO se construye

| No construir | Por qué |
|---|---|
| Adaptador real a SisGalenPlus | No sabemos si hay HCE, esquema o API. Solo el stub documentado. |
| Chatbot de WhatsApp | `wa.me` abre conversaciones pero no recibe mensajes. Recibir exige la API de pago de Meta. |
| OCR de historias manuscritas | Fuera de alcance declarado. |
| Asignación automática de hospital destino | Clínica y legalmente inaceptable. El sistema propone; una persona firma. |
| Modelo de aprendizaje automático | No existen las etiquetas. El sistema las produce; el modelo viene después. |
| Envío de SMS | Cuesta por mensaje en el Perú. |
| Cualquier escritura en el sistema del hospital | Rompe la promesa central: solo lectura. |

---

## Datos pendientes de confirmación

No inventar valores para estos. Dejar `# TODO: confirmar con mentor` y usar valores marcados como provisionales:

- Pesos `beta` de los diagnósticos — los definirá un médico del INSN
- Capacidad mensual del equipo — define el umbral del semáforo rojo
- Directorio de destinos (CIE-10 → servicio adulto)
- Qué pasa con el SIS al cumplir 18 años
- Criterio de prevalencia vigente para enfermedad rara en el Perú
- Si la HC del INSN está en HCE o sigue en PDF

---

## Documentos de referencia

| Archivo | Contenido |
|---|---|
| `docs/PLAN_TECNICO.md` | **La especificación.** Arquitectura, modelo de dominio, fórmulas, orden de construcción |
| `docs/DOSSIER.md` | El proyecto completo: problema, evidencia, normativa, diseño |
| `docs/VACIOS_ORIGINALIDAD_IMPACTO.md` | Reflexión crítica: qué no sabemos, qué es original, cuánto impacta |
| `docs/PREGUNTAS_MENTOR.md` | Preguntas abiertas al mentor del INSN |
| `docs/maqueta_mvp.html` | Maqueta visual de las pantallas |
