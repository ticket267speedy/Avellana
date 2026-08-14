# PLAN TÉCNICO — Proyecto Relevo
### Documento de guía para el agente de código · v2

**Proyecto:** Relevo — sistema de acompañamiento de la transición pediátrico-adulto
**Contexto:** Reto 1, Hackathon INSN San Borja ("Puente 18+")
**Equipo:** Avellana
**Fecha:** 14 de agosto de 2026

> **Cambios respecto de la v1:** se adoptó **arquitectura hexagonal (puertos y adaptadores)** con regla de dependencia explícita; se incorporó el hecho confirmado de que **el INSN no atiende mayores de 18 años bajo ninguna circunstancia**; se agregó el manejo de abreviaturas clínicas locales.

---

## 0. Instrucciones para el agente

Este documento es la especificación de trabajo. Léelo completo antes de escribir código.

**Reglas inviolables:**

1. **Nunca usar, generar ni versionar datos de pacientes reales.** Todo dato es sintético.
2. **Nada que cueste dinero.** Sin APIs de pago, sin licencias.
3. **Todo debe poder correr sin internet.** El wifi del evento va a fallar.
4. **El médico siempre firma.** Ninguna salida clínica se emite sin revisión humana explícita.
5. **Respetar la regla de dependencia de la §3.** Es el corazón del diseño, no una preferencia estética.
6. **Identificadores en español, sin tildes ni ñ.** Comentarios en español.
7. **Cada umbral y cada constante va comentada con su fuente.** Si un plazo es de 120 días, el comentario dice de dónde salió.

**Si algo de este plan choca con la realidad al implementarlo, detente y repórtalo antes de improvisar.**

---

## 1. Restricción de contexto confirmada

> **El INSN no atiende a mayores de 18 años bajo ninguna circunstancia.** Es regla institucional, no costumbre.

Esto no es un detalle: define el sistema entero.

| Consecuencia | Implicación técnica |
|---|---|
| El corte es **duro y en fecha exacta** | No hay estado "vencido pero todavía en pediatría". Al cumplir 18 el paciente ya está fuera. |
| No hay red de seguridad | Si el traspaso no se preparó antes del cumpleaños, **el paciente queda sin ningún servicio**. No es una demora, es una interrupción. |
| La ventana de trabajo es finita e improrrogable | El sistema es de **prevención de daño**, no de mejora de calidad. Los plazos se cuentan hacia atrás desde el cumpleaños 18. |
| El día 18 es una frontera, no un hito | `x1` (urgencia temporal) satura en 1 y **el paciente sale de la cohorte activa**, pasando a la cohorte de seguimiento post-alta. |

Modelar dos cohortes distintas:

- **Cohorte activa** (14 años ≤ edad < 18): se prioriza, se prepara, se emite Pasaporte.
- **Cohorte de seguimiento** (edad ≥ 18): ya no es paciente del INSN, pero **el ciclo de transición sigue abierto** hasta confirmar que llegó al servicio de adultos. Es aquí donde el sistema aporta lo que hoy no existe.

---

## 2. Qué se está construyendo

Un sistema que corre al lado del hospital, sin tocar su software:

1. **Detecta y prioriza** con un índice explicable.
2. **Genera** el Pasaporte de Salud 18+, escalonado a los 14, 16 y 17 años.
3. **Avisa** por correo al equipo y prepara mensajes de WhatsApp para la familia.
4. **Sigue el ciclo** con una máquina de estados y alerta cuando una etapa se vence.

**Principio rector:** el sistema busca a la persona; la persona no busca al sistema. Ninguna pantalla es de revisión obligatoria diaria.

---

## 3. Arquitectura — Hexagonal (puertos y adaptadores)

### 3.1 Por qué este patrón y no otro

No es una elección de moda. **La arquitectura es el argumento del pitch.**

Nuestra promesa central ante el jurado es: *"el núcleo no cambia; solo se cambia el adaptador de entrada según el sistema del hospital."* La arquitectura hexagonal, propuesta por Alistair Cockburn, es exactamente la formalización de esa promesa: el dominio no conoce a nadie, y todo lo externo entra por una interfaz que el dominio define.

Si dijéramos eso en el pitch y el código fuera un montón de módulos que se importan entre sí, la afirmación sería falsa. Aquí el código **demuestra** la afirmación.

**Honestidad sobre el trade-off:** para un hackathon puro, esto es sobreingeniería — bastaría una estructura plana. Se justifica *únicamente* porque la intercambiabilidad del adaptador es parte del valor que vendemos. Si no lo fuera, no lo haría.

### 3.2 La regla de dependencia

```
        interfaz  ──────┐
                        ├──►  aplicacion  ──►  dominio
   infraestructura ─────┘                        ▲
                                                 │
                        (define los puertos que ambos implementan)
```

**Las dependencias apuntan hacia adentro. Siempre.**

- `dominio` **no importa nada** de las otras capas. Ni SQLAlchemy, ni FastAPI, ni `requests`. Solo la librería estándar y `dataclasses`.
- `aplicacion` importa `dominio`. Nada más.
- `infraestructura` e `interfaz` importan `aplicacion` y `dominio`, e implementan las interfaces que el dominio declaró.

**Verificación automática:** incluir un test que recorra los imports de `dominio/` y falle si aparece cualquier paquete externo. Es una regla que se rompe sola si no se vigila.

```python
# tests/test_arquitectura.py
def test_dominio_no_depende_de_nada_externo():
    """La regla de dependencia es parte del diseño, no una sugerencia."""
```

### 3.3 Estructura

```
avellana/
├── README.md
├── PLAN_TECNICO.md
├── pyproject.toml
├── .env.example
├── .gitignore                          # incluye data/ y .env
│
├── config/                             # política clínica, no código
│   ├── reglas_transicion.yaml
│   ├── plazos_ciclo.yaml
│   ├── cie10_raras_rm478.csv           # RM 478-2026-MINSA
│   ├── ccc_v2_categorias.csv           # Complex Chronic Conditions v2
│   ├── abreviaturas_clinicas.yaml      # glosario local, ver §8.3
│   └── destinos.csv                    # PENDIENTE MENTOR
│
├── data/                               # nunca se versiona
│
├── src/relevo/
│   │
│   ├── dominio/                        # ── NÚCLEO. Cero dependencias externas.
│   │   ├── entidades/
│   │   │   ├── paciente.py
│   │   │   ├── diagnostico.py
│   │   │   ├── pasaporte.py
│   │   │   └── ciclo_transicion.py
│   │   ├── objetos_valor/
│   │   │   ├── codigo_cie10.py
│   │   │   ├── telefono.py
│   │   │   ├── indice_urgencia.py      # el IUT y su desglose
│   │   │   └── ventana_transicion.py
│   │   ├── servicios/                  # reglas de negocio puras
│   │   │   ├── calculadora_iut.py
│   │   │   ├── clasificador_cohorte.py
│   │   │   └── maquina_ciclo.py
│   │   ├── puertos/                    # ── INTERFACES (los "ports")
│   │   │   ├── repositorios.py         # RepositorioPacientes, RepositorioCiclos
│   │   │   ├── fuente_datos.py         # FuenteDatosClinicos
│   │   │   ├── generacion.py           # GeneradorResumen, GeneradorDocumento
│   │   │   ├── notificacion.py         # CanalNotificacion
│   │   │   └── exportacion.py          # ExportadorInteroperable
│   │   └── excepciones.py
│   │
│   ├── aplicacion/                     # ── CASOS DE USO. Orquestan el dominio.
│   │   ├── priorizar_cohorte.py
│   │   ├── emitir_pasaporte.py
│   │   ├── evaluar_vencimientos.py
│   │   ├── despachar_avisos.py
│   │   ├── registrar_confirmacion.py   # marca "cita cumplida"
│   │   └── dto.py                      # objetos de transporte hacia la interfaz
│   │
│   ├── infraestructura/                # ── ADAPTADORES. Implementan los puertos.
│   │   ├── persistencia/
│   │   │   ├── modelos_orm.py          # SQLAlchemy
│   │   │   ├── repositorio_sqlite.py
│   │   │   └── mapeadores.py           # ORM ↔ entidades de dominio
│   │   ├── fuentes/
│   │   │   ├── csv_sintetico.py        # implementa FuenteDatosClinicos
│   │   │   └── sisgalen_stub.py        # placeholder documentado
│   │   ├── interoperabilidad/
│   │   │   └── fhir_corepe.py          # implementa ExportadorInteroperable
│   │   ├── llm/
│   │   │   ├── sin_llm.py              # respaldo determinístico — SE CONSTRUYE PRIMERO
│   │   │   ├── groq.py
│   │   │   ├── gemini.py
│   │   │   ├── ollama.py
│   │   │   ├── plantillas_prompt.py
│   │   │   └── normalizador_abreviaturas.py
│   │   ├── documentos/
│   │   │   ├── pdf_weasyprint.py       # implementa GeneradorDocumento
│   │   │   ├── qr.py
│   │   │   └── plantillas/
│   │   │       ├── pasaporte_v1_14.html
│   │   │       ├── pasaporte_v2_16.html
│   │   │       └── pasaporte_v3_17.html
│   │   ├── notificacion/
│   │   │   ├── correo_smtp.py          # implementa CanalNotificacion
│   │   │   ├── whatsapp_enlace.py      # implementa CanalNotificacion
│   │   │   └── plantillas_mensaje.py
│   │   └── configuracion/
│   │       ├── cargador_yaml.py
│   │       └── contenedor.py           # inyección de dependencias
│   │
│   └── interfaz/                       # ── ADAPTADORES DE ENTRADA
│       ├── web/
│       │   ├── app.py
│       │   └── paginas/
│       └── cli/
│           ├── correr_noche.py
│           ├── generar_cohorte.py
│           └── validar_fhir.py
│
└── tests/
    ├── dominio/                        # unitarios puros, sin mocks ni base de datos
    │   ├── test_calculadora_iut.py     # 5 casos calculados a mano
    │   ├── test_clasificador.py
    │   └── test_maquina_ciclo.py
    ├── aplicacion/                     # con dobles de prueba de los puertos
    ├── infraestructura/
    │   ├── test_fhir.py
    │   └── test_privacidad_whatsapp.py # BLOQUEANTE
    └── test_arquitectura.py            # verifica la regla de dependencia
```

### 3.4 Beneficio concreto, no teórico

| Beneficio | Cómo se ve en la práctica |
|---|---|
| El dominio se prueba **sin base de datos, sin red y sin mocks** | `test_calculadora_iut.py` es aritmética pura contra casos hechos a mano |
| Cambiar SQLite por PostgreSQL toca **un archivo** | `repositorio_sqlite.py` → `repositorio_postgres.py` |
| Cambiar el proveedor de modelo de lenguaje toca **una variable de entorno** | Los cuatro implementan `GeneradorResumen` |
| Conectar SisGalenPlus el día que se pueda toca **un archivo** | `sisgalen_stub.py` → implementación real de `FuenteDatosClinicos` |
| **La afirmación del pitch es verificable** | "El núcleo no cambia" se puede demostrar mostrando que `dominio/` no importa nada |

Ese último punto es el que vale.

---

## 4. Python o Java

Preguntaste y la respuesta honesta tiene dos partes.

### Para este hackathon: Python, sin discusión

| Criterio | Python | Java |
|---|---|---|
| Velocidad de desarrollo en 48 h | ✅ Decisiva | ❌ Ceremonia, compilación, verbosidad |
| Ecosistema FHIR | `fhir.resources`, suficiente | ✅ **HAPI FHIR es la implementación de referencia** |
| Modelos de lenguaje | ✅ Todo el ecosistema está aquí | Clientes de segunda |
| Generación de PDF | ✅ WeasyPrint | Aceptable (iText, PDFBox) |
| Datos sintéticos, análisis | ✅ Faker, pandas | Más trabajo |
| Prototipo de interfaz | ✅ Streamlit: interfaz en minutos | Semanas |

En 48 horas Python gana por goleada. No es cercano.

### Para producción en un hospital: el argumento de Java es real

Y conviene conocerlo porque te lo pueden preguntar:

- **HAPI FHIR**, el servidor y librería FHIR de referencia mundial, es Java. Si el INSN algún día monta un servidor FHIR, casi seguro es HAPI.
- Muchos sistemas hospitalarios institucionales corren sobre JVM, y las áreas de TI suelen tener personal de Java, no de Python.
- Tipado estático y herramientas de mantenimiento a largo plazo.

**La respuesta que da la arquitectura hexagonal:** como el dominio no depende de nada, **portarlo es traducir aritmética y reglas, no reescribir el sistema.** Los adaptadores se rehacen; el núcleo se traduce casi literalmente. Elegir Python hoy no cierra la puerta de Java mañana. Eso es un argumento para el pitch, no una excusa.

### Nota para ti específicamente

Vienes de C, así que el tipado dinámico de Python te va a incomodar. Mitigación obligatoria en este proyecto:

- **Anotaciones de tipo en todo** — sin excepciones
- **Pydantic v2** para validar todo lo que cruza una frontera
- **`mypy --strict`** sobre `src/relevo/dominio/` y `src/relevo/aplicacion/`
- **`dataclasses` con `frozen=True`** para los objetos de valor: inmutabilidad por defecto

Con eso Python se comporta bastante más como un lenguaje tipado, y el dominio queda blindado.

---

## 5. Modelo de dominio

```python
# src/relevo/dominio/entidades/paciente.py
# Sin imports externos. Solo librería estándar.

@dataclass
class Paciente:
    id: str                          # identificador interno, NUNCA el DNI
    fecha_nacimiento: date
    sexo: str
    procedencia: str
    tipo_seguro: TipoSeguro
    diagnosticos: list[Diagnostico]
    medicamentos: list[Medicamento]
    dispositivos: list[Dispositivo]
    alergias: list[str]
    cirugias: list[Cirugia]
    contactos: list[Contacto]
    ultima_consulta: date | None
    traq: float | None               # 1.0 a 5.0
    texto_libre: dict[str, str]

    def meses_hasta_corte(self, hoy: date) -> int:
        """Meses hasta el cumpleaños 18. Puede ser negativo."""

    def cohorte(self, hoy: date) -> Cohorte:
        """ACTIVA si 14 <= edad < 18. SEGUIMIENTO si >= 18.
        El INSN no atiende mayores de 18: el corte es duro."""
```

```python
# src/relevo/dominio/objetos_valor/indice_urgencia.py

@dataclass(frozen=True)
class AporteFactor:
    nombre: str
    x: float                         # valor normalizado [0,1]
    beta: float
    dato_faltante: bool = False

    @property
    def aporte(self) -> float:
        return self.beta * self.x

@dataclass(frozen=True)
class IndiceUrgencia:
    valor: float                     # [0,1]
    z: float                         # log-odds
    aportes: tuple[AporteFactor, ...]  # ordenados desc por aporte
    estado: EstadoSemaforo
```

**Requisito de aceptación:** `IndiceUrgencia` **no puede construirse sin sus aportes**. El desglose no es un extra de la interfaz: es parte del valor. Un índice sin explicación es un dato inválido en este dominio.

**Nota sobre contactos:** verificamos la plantilla oficial (RD N° 000109-2021-DG-INSN-SB) — **no tiene campo de teléfono ni correo en ninguna de sus seis páginas**. `Contacto.verificado_en` existe porque el teléfono registrado cuando el paciente tenía tres años probablemente ya no funciona. La captura progresiva en los hitos de 14, 16 y 17 años es funcionalidad central.

---

## 6. Motor de reglas

### 6.1 Tres fuentes, ninguna inventada por nosotros

| Fuente | Cubre | Archivo |
|---|---|---|
| **RM 478-2026-MINSA** — 558 diagnósticos raros en CIE-10 (11 may 2026) | Raras | `cie10_raras_rm478.csv` |
| **Complex Chronic Conditions v2** (Feudtner, BMC Pediatrics) — 10 categorías sobre CIE-10, incluye dependencia tecnológica y trasplante | Complejas | `ccc_v2_categorias.csv` |
| Códigos crónicos agregados por el médico del INSN | Crónicas locales | `reglas_transicion.yaml` |

Para el MVP: las 10 categorías de CCC v2 con ~40 códigos representativos, **declarando explícitamente en la interfaz que el listado completo es cargable**. No fingir cobertura que no está.

### 6.2 El IUT

$$\mathrm{IUT} = \sigma\!\left(\beta_0 + \sum_i \beta_i x_i\right), \qquad \sigma(z)=\frac{1}{1+e^{-z}}$$

| Factor | Definición | Nota |
|---|---|---|
| `x1` urgencia temporal | `clamp(1 - t_r/48, 0, 1)` | `t_r` = meses hasta los 18. **Satura en 1 y el paciente pasa a cohorte de seguimiento.** |
| `x2` complejidad | `min(K/5, 1)` | El 5 sale de las casillas de dx secundario de la HC |
| `x3` severidad | Σ pesos / peso máximo | Pesos del YAML |
| `x4` dependencia tecnológica | suma normalizada | |
| `x5` brecha de preparación | `(5 - TRAQ)/4` | Sin TRAQ: imputar 0.5 **y marcar `dato_faltante=True`** |
| `x6` riesgo de pérdida | `clamp(Δ/(2θ), 0, 1)` | |
| `x7` barrera de acceso | 1 si fuera de Lima Metropolitana | |
| `x8` continuidad de seguro | 1 si el régimen cambia a los 18 | Ver §6.3 |

**Calibración de umbrales:** implementar `calibrar_umbral_rojo(cohorte, capacidad_mensual) -> float`. No es un adorno: es un argumento del pitch. El umbral se deriva de la capacidad real del equipo, no de un número inventado.

### 6.3 Seguro

Verificado: en **EsSalud**, los hijos dejan de ser derechohabientes a los 18 salvo que acrediten **incapacidad total y permanente** ante la Comisión Médica Evaluadora. Un crónico que no califica como discapacitado total pierde cobertura.

No verificado: qué pasa con el **SIS**. Marcar `# TODO: verificar con Servicio Social INSN` y no afirmar nada sin confirmar.

---

## 7. Máquina de estados del ciclo

Calibrada con datos peruanos reales (estudio DIRIS Lima Norte, Revista Médica Herediana, 19 951 referencias).

```python
class EstadoCiclo(Enum):
    PASAPORTE_EMITIDO      = 1
    REFERENCIA_REGISTRADA  = 2
    REFERENCIA_ACEPTADA    = 3
    CITA_PROGRAMADA        = 4
    CITA_CUMPLIDA          = 5
    CONTRARREFERENCIA      = 6
```

| Transición | Plazo | Justificación |
|---|---|---|
| 1 → 2 | 7 días | Trámite administrativo |
| 2 → 3 | 30 días | Solo 23.14 % se acepta en 24 h; 13.6 % vuelve por información incompleta |
| 3 → 4 | **120 días** | La **mediana** aceptación→cita es de **80–85 días**. Un umbral de 90 dispararía alerta en la mitad de los casos sanos. |
| 4 → 5 | 30 días post-cita | |
| 5 → 6 | 30 días | |

**Doble fuente para el estado 5.** El mismo estudio documenta **110 contrarreferencias sobre 19 951 = 0.55 %**. La vía formal no funciona empíricamente:

```python
class FuenteConfirmacion(Enum):
    CONTRARREFERENCIA    = "formal"       # ~0.55% de los casos
    CONFIRMACION_FAMILIA = "pragmatica"   # WhatsApp o llamada
```

El indicador debe desagregarse por fuente: **la proporción de cada una es en sí misma un hallazgo del piloto.**

Los plazos van en `config/plazos_ciclo.yaml`.

---

## 8. Procesamiento de lenguaje

### 8.1 Puerto y adaptadores

```python
# src/relevo/dominio/puertos/generacion.py
class GeneradorResumen(ABC):
    @abstractmethod
    def extraer_estructurado(self, texto: str) -> DatosExtraidos: ...
    @abstractmethod
    def resumir_clinico(self, historia: HistoriaCompleta) -> str: ...
    @abstractmethod
    def traducir_ciudadano(self, resumen: str, edad: int) -> str: ...
```

Adaptadores: `SinLLM`, `Groq`, `Gemini`, `Ollama`. Selección por `RELEVO_LLM_PROVIDER`.

**`SinLLM` se construye primero y debe funcionar sin red.** Arma el contenido por plantilla desde los campos ya estructurados. Es el respaldo cuando falle el wifi, y es lo que se demuestra si todo lo demás se cae.

### 8.2 Tres tareas, tres prompts

| # | Tarea | Salida | Tolerancia |
|---|---|---|---|
| 1 | Extracción | JSON validado con Pydantic | **Baja** — descartar lo que no valide |
| 2 | Resumen clínico | Una página, lenguaje técnico, para el médico receptor | Media — el médico firma |
| 3 | Traducción ciudadana | Texto para el paciente según edad (14/16/17) | Media — el médico firma |

**Verificación antifabulación, obligatoria:** toda dosis extraída debe aparecer **literalmente** en el texto fuente. Si no aparece, se descarta y se marca "requiere completar manualmente". Inventar una dosis es el peor fallo posible de este sistema.

### 8.3 Abreviaturas clínicas — el riesgo real, acotado

Tienes razón en lo esencial: si un médico escribe una abreviatura, otro médico debe poder leerla, así que no son códigos privados y un modelo de lenguaje razonable las maneja. El riesgo es menor de lo que planteé.

Pero queda un residuo, y es específico y peligroso. **Las abreviaturas del español clínico peruano son locales, y algunas son ambiguas.** Ejemplo tomado del propio formulario del INSN que leímos:

> **`PC`** aparece en la sección de Examen Físico junto a Peso y Talla: significa **perímetro cefálico**.
> Pero `PC` es también la abreviatura habitual de **parálisis cerebral**.

Un modelo entrenado mayormente en texto clínico en inglés puede confundirlas. Y confundir un perímetro cefálico con un diagnóstico de parálisis cerebral en un Pasaporte que un médico va a firmar rápido es exactamente el tipo de error que no podemos permitir.

Otras del mismo formulario: `SOMA` (sistema osteomuscular), `TCSC` (tejido celular subcutáneo), `MTD` / `MTI` (miembro torácico derecho / izquierdo), `LME` (lactancia materna exclusiva), `HGT` (hemoglucotest), `RAM` (reacción adversa a medicamentos), `FUR` (fecha de última regla), `CPN` (control prenatal).

**Mitigación, barata y efectiva:**

1. `config/abreviaturas_clinicas.yaml` — glosario local que se **inyecta en el prompt** como contexto. Un diccionario de cincuenta entradas resuelve casi todo.
2. Las entradas ambiguas se marcan `ambigua: true` y el prompt instruye a **resolverlas por contexto de sección o dejarlas sin expandir**, nunca a adivinar.
3. `normalizador_abreviaturas.py` expande las inequívocas **antes** de llamar al modelo, para no depender de que acierte.
4. Un caso de la cohorte sintética debe llevar `PC` en sentido de perímetro cefálico, como test de regresión.

**Alcance de la demo:** historias tipeadas. La manuscrita queda declarada fuera de alcance, con la ruta de OCR mencionada pero no construida. Es honesto y nadie va a objetarlo.

---

## 9. El Pasaporte escalonado

| Versión | Edad | Extensión | Contenido |
|---|---|---|---|
| v1 | 14 | Media página | Qué tengo, qué tomo, a qué soy alérgico |
| v2 | 16 | 1 página | v1 + cómo pedir cita, qué hacer si me siento mal, qué preguntar |
| v3 | 17–18 | 2 páginas, doble versión | Completo: dx con CIE-10, cirugías, medicación, alergias, dispositivos, especialistas, qué vigilar, contactos, situación de seguro |

**Obligatorio en las tres:**

1. QR a la versión digital
2. Bloque de captura y verificación de contacto (en v2 y v3, **el teléfono propio del paciente**)
3. El aviso normativo al pie, textual:

> *"Documento informativo complementario para la transición asistencial. No reemplaza la historia clínica ni el resumen de historia clínica normado (RM 214-2018-MINSA). Elaborado con apoyo automatizado, revisado y firmado por el médico tratante."*

4. Marca de agua **"DATOS SINTÉTICOS — DEMO"** mientras dure el hackathon. No negociable.

---

## 10. Capa de avisos

### Correo

```python
def armar_correo_semanal(nuevos_prioridad_alta) -> Correo | None:
    """None si no hay nada nuevo. Un aviso que llega siempre deja de leerse."""
```

Asunto con el número: `Relevo · 3 pacientes en prioridad alta esta semana`. El cuerpo se lee sin abrir enlaces.

### WhatsApp

Genera enlaces `wa.me`; no envía nada. Un humano hace clic y despacha desde su propio WhatsApp.

**Regla de privacidad, verificada por test bloqueante:** ningún mensaje puede contener diagnósticos, códigos CIE-10, nombres de medicamentos, dosis ni resultados.

`tests/infraestructura/test_privacidad_whatsapp.py` recorre todas las plantillas y todos los mensajes generados para la cohorte sintética, y falla si aparece cualquier término de una lista negra construida desde los CSV de diagnósticos y medicamentos.

---

## 11. Exportación FHIR

Bundle tipo `document` conforme a los perfiles CorePE del MINSA (`dyaku.minsa.gob.pe/guides/`, FHIR R4, basado en International Patient Summary).

Recursos: `Composition`, `Patient`, `Condition`, `MedicationStatement`, `AllergyIntolerance`, `Organization`, `Practitioner`.

`validar_fhir.py` valida contra el validador público de HAPI FHIR. **Si no valida, no es entregable.** Es uno de nuestros diferenciadores y tiene que funcionar de verdad.

---

## 12. Orden de construcción

De adentro hacia afuera, siguiendo la arquitectura.

| # | Bloque | Capa | Criterio de aceptación | Est. |
|---|---|---|---|---|
| 1 | Entidades y objetos de valor | dominio | `mypy --strict` limpio; sin imports externos | 1 h |
| 2 | Puertos (interfaces) | dominio | Definidos y documentados | 0.5 h |
| 3 | `CalculadoraIUT` | dominio | **5 casos calculados a mano en papel coinciden** | 2 h |
| 4 | `ClasificadorCohorte` | dominio | 10 casos de prueba escritos a mano | 1 h |
| 5 | `MaquinaCiclo` | dominio | Test que simula el paso del tiempo por cada plazo | 1.5 h |
| 6 | `test_arquitectura.py` | tests | Falla si `dominio` importa algo externo | 0.5 h |
| 7 | Repositorio SQLite + mapeadores | infra | Ida y vuelta entidad ↔ ORM sin pérdida | 1.5 h |
| 8 | `generar_cohorte.py` | interfaz | 300 pacientes con distribución realista **y ruido de abreviaturas** | 2 h |
| 9 | Casos de uso | aplicación | Priorización end-to-end sobre la cohorte | 1.5 h |
| 10 | `SinLLM` | infra | Pasaporte completo **sin red** | 1 h |
| 11 | PDF + QR (v3) | infra | PDF legible, QR funcional, aviso normativo | 2.5 h |
| 12 | Exportador FHIR | infra | **Valida contra HAPI sin errores** | 2 h |
| 13 | Avisos + test de privacidad | infra | El test bloqueante pasa | 1.5 h |
| 14 | Interfaz web | interfaz | El caso de Ana se recorre completo sin tocar código | 3 h |
| 15 | Pasaporte v1 y v2 | infra | Las tres versiones según edad | 1.5 h |
| 16 | Proveedores de modelo | infra | Groq y Ollama funcionan; se cambian por variable de entorno | 2 h |
| 17 | `correr_noche.py` | interfaz | Un comando ejecuta el ciclo completo | 1 h |

**Los bloques 1 a 6 son el núcleo y no dependen de nada.** Se pueden construir y probar completos antes de decidir una sola cosa de infraestructura. Eso es el beneficio real del patrón.

---

## 13. Lo que NO se construye, y por qué

| No se construye | Por qué |
|---|---|
| Adaptador real a SisGalenPlus | No sabemos si hay HCE, esquema o API. Queda `sisgalen_stub.py` con la interfaz documentada. |
| Chatbot de WhatsApp | `wa.me` abre conversaciones pero **no recibe mensajes**. Recibir exige la API de pago de Meta. Restricción del canal, no decisión nuestra. |
| OCR de historias manuscritas | Fuera de alcance declarado. Ruta mencionada, no construida. |
| Asignación automática de destino | Clínica y legalmente inaceptable. El sistema propone; una persona firma. |
| Modelo de aprendizaje automático | No existen las etiquetas. El sistema las produce; el modelo viene después. |
| SMS | Cuesta por mensaje en el Perú. Fuera del presupuesto cero. |
| Escritura en el sistema del hospital | Rompe la promesa central: solo lectura. |

---

## 14. Verificación antes de presentar

- [ ] `mypy --strict` limpio sobre `dominio/` y `aplicacion/`
- [ ] `test_arquitectura.py` pasa — el dominio no importa nada externo
- [ ] Cinco casos de IUT calculados a mano coinciden con el código
- [ ] El Bundle FHIR valida contra HAPI sin errores
- [ ] `test_privacidad_whatsapp.py` pasa
- [ ] **El sistema completo corre con el wifi apagado** usando `SinLLM`
- [ ] El caso de `PC` como perímetro cefálico no se confunde con parálisis cerebral
- [ ] Los tres Pasaportes se generan y son legibles impresos en blanco y negro
- [ ] El QR escanea desde un teléfono real
- [ ] Ningún dato real en el repositorio; todos los PDF con marca "DATOS SINTÉTICOS"
- [ ] El recorrido completo del caso de Ana se hace sin tocar la terminal
- [ ] `README.md` levanta el proyecto en menos de cinco comandos
