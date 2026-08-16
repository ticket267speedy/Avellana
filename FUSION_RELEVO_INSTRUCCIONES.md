# Relevo — Instrucciones de fusión para Claude Code

**Destinatario:** Claude Code, trabajando sobre el repositorio local de Relevo.
**Fecha:** 16 ago 2026
**Autoridad:** este documento manda sobre cualquier decisión previa **salvo** las reglas inviolables de `CLAUDE.md`, que siguen intactas y no se negocian.

---

## 0. Lee esto antes de tocar nada

1. Lee `CLAUDE.md` completo. Las 8 reglas inviolables aplican a todo lo que sigue.
2. Lee `docs/PLAN_TECNICO.md`.
3. Lee `docs/ESTADO_DOLORES.md` y `docs/MAPEO_RUBRICA_INSN.md`.
4. Lee `docs/CIERRE_MVP.md` — las tareas T2–T8 siguen pendientes y están incorporadas al plan de abajo.

**No empieces a escribir código hasta haber corrido la suite completa y confirmado que los 93 tests existentes están en verde.** Si alguno está rojo, arréglalo y haz commit de esa corrección **antes** de empezar la fusión. Un punto de partida rojo hace imposible saber qué rompió qué.

---

## 1. Qué está pasando y por qué

El equipo presentó en paralelo un segundo MVP (Vanilla JS + LocalStorage, sin arquitectura). Ese código **no se reutiliza**: tres archivos de ~2000 líneas sin capas no se pueden integrar limpiamente y el costo de desenredarlo supera el de reescribirlo.

Lo que **sí** se toma de ese trabajo son **decisiones de producto**, que son buenas y cubren huecos reales del núcleo actual:

| Concepto que aportan | Dolor que mueve |
|---|---|
| Ruta de Aprendizaje "Entrénate" | **B3** — hoy en ~10 %: medíamos con TRAQ pero no interveníamos |
| Hospital receptor como actor con acciones propias | **B4** — el receptor era un dato, no un usuario |
| "¿Quién tiene el turno ahora?" | Pendiente #2 de la rúbrica INSN (`Responsable` en la transición) |
| Conciliación de medicación paciente ↔ receptor | **B2** — mecanismo nuevo, no lo teníamos |
| Vista del apoderado + derechos a los 18 | Hueco legal real (Ley 29733, mayoría de edad) |
| 7 etapas de la ruta de referencia | Refinamiento de nuestras 6 |

Lo que se conserva del núcleo actual, sin excepción: **arquitectura hexagonal, IUT, verificador anti-error-silencioso, SQLite, cadena de hash de auditoría, Ollama local, Pasaporte escalonado, DirectorioDestinos.**

**Decisiones ya tomadas por Luis Felipe — no las reabras:**

- Interfaz de producto **se reescribe desde cero**, con arquitectura.
- Caso protagonista: **Síndrome de Hunter**, no asma.
- Contenido educativo: **1 módulo completo + 6 esqueletos marcados** como pendientes de validación clínica.
- **El IUT se mantiene**, con el blindaje discursivo de §4.7.
- Trabajo en **rama nueva**, sin tocar `main`.

---

## 2. Rama y seguridad del trabajo

```bash
git status                      # debe estar limpio; si no, commitea o guarda antes
git branch --show-current       # anota la rama actual (la que tiene el trabajo de Ollama)
git switch -c fusion/entrenate-receptor
```

- Todo el trabajo va en `fusion/entrenate-receptor`.
- **No hagas merge a `main` ni a la rama de Ollama.** Solo `git push -u origin fusion/entrenate-receptor` cuando el checkpoint C4 esté verde.
- Un commit por checkpoint, con mensaje que diga qué checkpoint cierra.
- `data/` sigue sin versionarse (regla 1).

---

## 3. Dos principios que deben quedar escritos en el código

### 3.1 · Corte etario y reingreso

Esto resuelve una confusión que ya costó tiempo. Escríbelo como docstring del módulo de estados.

**Cumplir 18 años NO es el fracaso del sistema.** La primera cita en el hospital de adultos ocurre, por definición, después de los 18. El corte etario del INSN impide la *atención pediátrica*, no la continuidad del trámite.

**El fracaso es cumplir 18 sin destino asegurado**, es decir con el ciclo en un estado anterior a `ACEPTADO_CON_SERVICIO`. Esa es la métrica estrella de fracaso y va arriba de todo en el radar.

**REINGRESO es un estado del ciclo de transición, no un reingreso al INSN.** El ciclo es un artefacto administrativo que vive en Relevo. Que se reabra no implica ninguna atención clínica pediátrica. Con el paciente ≥18 años, un ciclo reabierto **solo habilita acciones administrativas** (reenviar Pasaporte, contactar al receptor, contactar a la familia) y **nunca** acciones clínicas del INSN. Esto debe estar impedido por código, no solo documentado.

```python
# TODO: confirmar con mentor — si el equipo de transicion del INSN esta
# facultado para gestion administrativa de un ex-paciente mayor de 18 anios.
# Provisional: se asume que si, porque la NT 018-MINSA obliga a la
# contrarreferencia y esa obligacion no caduca con la edad del paciente.
```

### 3.2 · Cero doble digitación — **restricción de producto, no preferencia**

Esto es lo que mata a los proyectos de salud digital y hay que blindarlo con código, no con buenas intenciones.

**El INSN ya tiene SisGalenPlus. Nadie va a teclear los mismos datos dos veces.** Si Relevo pide que el personal vuelva a escribir diagnóstico, tratamiento o filiación, el sistema se abandona en la segunda semana por muy bien construido que esté. Este es el motivo real por el que el extractor y el verificador existen.

**Principio, textual, para el docstring y para el dossier:**

> **Relevo no pide datos. Pide decisiones.**

El dato clínico entra por exactamente tres puertas, y **ninguna es el teclado del personal de salud**:

1. **Digitalización** de un documento que ya existe (hoja de referencia, epicrisis) → extractor → verificador → firma.
2. **Lectura** del sistema del hospital, el día que exista el adaptador. Solo lectura, nunca escritura (ya está en la tabla de "no construir" de `CLAUDE.md`).
3. **El propio paciente** sobre sí mismo. No es doble digitación: ese dato nadie más lo tenía.

Lo único que hace el profesional es **confirmar, corregir o firmar** (VERDE / ÁMBAR / ROJO) y **avanzar el ciclo**, que es un clic.

**Consecuencias obligatorias de diseño:**

- **Cero formularios clínicos de texto libre** en las vistas de personal de salud (INSN y receptor).
- Las 6 acciones del receptor son **un clic cada una**, no formularios.
- "Solicitar información complementaria" es una **lista cerrada de opciones** (falta epicrisis, falta resultado de laboratorio, falta consentimiento, falta dato de contacto, otro). El texto libre es opcional y complementario, nunca el portador del dato clínico.
- La ruta de aprendizaje la alimenta el paciente, no el personal.

**Test bloqueante nuevo:** `tests/interfaz/test_sin_captura_clinica_por_personal.py` — recorre los esquemas Pydantic de los endpoints bajo `/api/insn/` y `/api/receptor/` y falla si alguno acepta un campo clínico de escritura libre. Los únicos campos de escritura admitidos para personal son veredictos de verificación, selecciones de lista cerrada y notas administrativas explícitamente marcadas como no clínicas.

**Métrica de pitch derivada:** cuenta y muestra los **clics por paciente** que le cuesta a un profesional del INSN llevar un ciclo de punta a punta. Es un número que ningún otro grupo va a poder dar.

---

## 4. Cambios en `dominio/`

Recordatorio: `dominio/` no importa nada externo. Solo librería estándar y `dataclasses`. `mypy --strict` limpio.

### 4.1 · `EstadoCiclo` — reemplazar por 9 estados

Archivo: `src/relevo/dominio/objetos_valor/estado_ciclo.py`

```python
class EstadoCiclo(Enum):
    PREPARACION = "preparacion"
    REFERENCIA_ENVIADA = "referencia_enviada"
    RECEPCION_CONFIRMADA = "recepcion_confirmada"
    EN_EVALUACION = "en_evaluacion"
    ACEPTADO_CON_SERVICIO = "aceptado_con_servicio"
    CITA_PROGRAMADA = "cita_programada"
    PRIMERA_ATENCION_CONFIRMADA = "primera_atencion_confirmada"
    PERDIDA_DE_SEGUIMIENTO = "perdida_de_seguimiento"
    REINGRESO = "reingreso"
```

Notas de diseño obligatorias:

- La separación `RECEPCION_CONFIRMADA` / `EN_EVALUACION` **no es cosmética**: ahí exactamente vive el 0.55 % de contrarreferencia del estudio de DIRIS Lima Norte. Comenta esa fuente en el enum.
- `PRIMERA_ATENCION_CONFIRMADA` es terminal-exitoso pero **no inmutable**: puede pasar a `REINGRESO`.
- `REINGRESO` es **transitorio**. Un ciclo no puede quedarse ahí: exige reclasificación explícita a uno de los 7 estados de trámite dentro del plazo de §4.3.

Migra los estados antiguos con un mapa explícito `ESTADOS_LEGADO: dict[str, EstadoCiclo]` y un test que verifique que cada valor viejo persistido en SQLite tiene destino. **No borres datos existentes para simplificar la migración.**

### 4.2 · `Responsable` — nuevo objeto de valor

Archivo: `src/relevo/dominio/objetos_valor/responsable.py`

```python
class Responsable(Enum):
    EQUIPO_INSN = "equipo_insn"
    HOSPITAL_RECEPTOR = "hospital_receptor"
    PACIENTE = "paciente"
    APODERADO = "apoderado"
    NADIE = "nadie"          # solo para PRIMERA_ATENCION_CONFIRMADA
```

Función pura, sin estado:

```python
def responsable_de(estado: EstadoCiclo) -> Responsable: ...
```

Esta función es la respuesta a **"¿Quién tiene el turno ahora?"**. Usa ese nombre literal en la interfaz — es la mejor pieza de comunicación del proyecto.

### 4.3 · Tabla de transiciones con responsable y plazo

Archivo: `src/relevo/dominio/servicios/maquina_ciclo.py`

Cada plazo va comentado con su fuente (regla 7). Los que no tienen fuente van marcados como provisionales.

| Estado | Responsable | Plazo | Fuente |
|---|---|---|---|
| `PREPARACION` | EQUIPO_INSN | 30 d | Provisional. `# TODO: confirmar con mentor` |
| `REFERENCIA_ENVIADA` | HOSPITAL_RECEPTOR | 7 d | Acuse de recepción. Provisional, alineado al espíritu de NT 018-MINSA/DGSP-V.01 |
| `RECEPCION_CONFIRMADA` | HOSPITAL_RECEPTOR | 15 d | Provisional |
| `EN_EVALUACION` | HOSPITAL_RECEPTOR | 30 d | Provisional |
| `ACEPTADO_CON_SERVICIO` | HOSPITAL_RECEPTOR | **120 d** | Calibrado sobre mediana 80–85 d aceptación→cita (DIRIS Lima Norte, Rev Med Hered). Un umbral de 90 d dispararía en la mitad de los casos sanos |
| `CITA_PROGRAMADA` | PACIENTE | fecha de cita + 7 d | El receptor confirma asistencia |
| `PRIMERA_ATENCION_CONFIRMADA` | NADIE | — | Terminal-exitoso |
| `PERDIDA_DE_SEGUIMIENTO` | EQUIPO_INSN | 15 d | Provisional |
| `REINGRESO` | EQUIPO_INSN | 7 d para reclasificar | Provisional |

Transiciones permitidas: define un `dict[EstadoCiclo, frozenset[EstadoCiclo]]` explícito. Cualquier transición fuera de ese mapa levanta `TransicionInvalida`. Test obligatorio: recorrer el grafo y verificar que desde cada estado se puede alcanzar `PRIMERA_ATENCION_CONFIRMADA`.

### 4.4 · Reingreso

Archivo: `src/relevo/dominio/objetos_valor/reingreso.py`

```python
class MotivoReingreso(Enum):
    REAPARECE_TRAS_PERDIDA = "reaparece_tras_perdida"
    NO_ASISTIO_A_PRIMERA_CITA = "no_asistio_a_primera_cita"
    ATENDIDO_SIN_CONTINUIDAD = "atendido_sin_continuidad"
    CAMBIO_DE_DESTINO = "cambio_de_destino"
```

Regla que debe estar **impedida por código**, con test propio:

```python
def acciones_permitidas(ciclo: Ciclo, hoy: date) -> frozenset[AccionCiclo]:
    """Con el paciente >= 18, un ciclo reabierto solo habilita acciones
    administrativas. Ninguna accion clinica del INSN es posible: el INSN
    no atiende mayores de 18 bajo ninguna circunstancia (CLAUDE.md)."""
```

Test bloqueante nuevo: `tests/dominio/test_reingreso_no_reabre_atencion.py` — construye un ciclo con paciente de 18 años y 1 día en `REINGRESO`, verifica que ninguna acción clínica del INSN está en el conjunto permitido.

### 4.5 · Corte etario — la métrica estrella de fracaso

Archivo: `src/relevo/dominio/servicios/corte_etario.py`

```python
ESTADOS_CON_DESTINO_ASEGURADO: frozenset[EstadoCiclo] = frozenset({
    EstadoCiclo.ACEPTADO_CON_SERVICIO,
    EstadoCiclo.CITA_PROGRAMADA,
    EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
})

@dataclass(frozen=True)
class CumplioDieciochoSinDestino:
    """Evento de dominio. El unico fracaso que el sistema existe para evitar."""
    id_paciente: str
    fecha_cumpleanios: date
    estado_al_cumplir: EstadoCiclo
    dias_en_ese_estado: int

def dias_para_corte(fecha_nacimiento: date, hoy: date) -> int: ...
def evaluar_corte_etario(ciclo: Ciclo, hoy: date) -> CumplioDieciochoSinDestino | None: ...
```

Y la métrica agregada, que va arriba de todo en el radar:

```python
@dataclass(frozen=True)
class MetricaCorteEtario:
    en_riesgo_90_dias: int      # cumplen 18 en <90 d sin destino asegurado
    ya_cumplieron_sin_destino: int
    total_cohorte: int
```

### 4.6 · Ruta de Aprendizaje "Entrénate"

Archivos nuevos en `src/relevo/dominio/`:

```
objetos_valor/franja_etaria.py
objetos_valor/habilidad.py
entidades/leccion.py
entidades/progreso_aprendizaje.py
servicios/recomendador_leccion.py
```

> **Nota de vocabulario, obligatoria en todo el proyecto.** Las compañeras las llamaron "módulos". **No uses esa palabra.** En software "módulo" significa otra cosa y ya causó confusión en el equipo. Se llaman **lecciones** (`Leccion`), y son las unidades del recorrido educativo Entrénate: siete lecciones, una por habilidad, cada una con la estructura *aprender → practicar → desafío → tarea de la vida real → retroalimentación*. Renombra cualquier `modulo` que encuentres.

```python
class FranjaEtaria(Enum):
    EXPLORA = "explora"        # 11-12
    PREPARADOS = "preparados"  # 13-14
    LISTOS = "listos"          # 15-16
    YA = "ya"                  # 17-18

class EstadoHabilidad(Enum):
    POR_INICIAR = "por_iniciar"
    EN_PRACTICA = "en_practica"
    LOGRADA = "lograda"
    NECESITA_REFUERZO = "necesita_refuerzo"

class EstadoContenido(Enum):
    COMPLETO = "completo"
    ESQUELETO_PENDIENTE_VALIDACION = "esqueleto_pendiente_validacion"
```

Las 7 habilidades, una por lección:

1. `CONOZCO_MI_CONDICION`
2. `MANEJO_MI_TRATAMIENTO`
3. `HABLO_CON_MI_EQUIPO`
4. `NAVEGO_EL_SISTEMA`
5. `CUIDO_MIS_DOCUMENTOS`
6. `CONOZCO_MIS_DERECHOS`
7. `ENTIENDO_LA_TRANSICION`

Mapeo del Pasaporte escalonado existente sobre las franjas — **no dupliques el concepto, mapéalo**:

| Franja | Versión de Pasaporte |
|---|---|
| EXPLORA (11–12) | — (previa a V1) |
| PREPARADOS (13–14) | `V1_14` |
| LISTOS (15–16) | `V2_16` |
| YA (17–18) | `V3_17` |

**Invariante no negociable, con test bloqueante propio.** Esta es la mejor decisión de diseño que trajeron las compañeras y hay que blindarla:

> La ruta de aprendizaje **nunca** bloquea, retrasa ni condiciona una transición de la ruta de referencia. No existe un readiness score que autorice la transferencia.

Test: `tests/dominio/test_aprendizaje_no_bloquea_referencia.py` — construye un paciente con las 7 habilidades en `POR_INICIAR` y verifica que **todas** las transiciones del ciclo siguen permitidas.

El recomendador es una función pura, **sin LLM**:

```python
def recomendar_leccion(
    traq: ResultadoTRAQ | None,
    edad_anios: int,
    progreso: ProgresoAprendizaje,
) -> Leccion | None: ...
```

Con esto el TRAQ deja de ser un número de reporte y pasa a ser el diagnóstico que decide la intervención. Ese es el cierre del bucle medir → intervenir → volver a medir, y es la frase que va en el pitch.

**Contenido de las lecciones.** Una completa, seis esqueletos.

- **Completa: Lección 6, "Qué cambia cuando cumplo 18".** Se elige esta y no "Mi condición" por cuatro razones que se apilan: (a) es la única de las siete que habla del acantilado legal que le da nombre al reto; (b) es contenido **jurídico y administrativo, no clínico**, así que podemos escribir y defender cada frase sin la firma de un médico (regla 4); (c) tiene carga emocional real — el adolescente descubre que su madre ya no puede pedir sus resultados y que ahora decide él; (d) es la única cuyo contenido se conecta con un mecanismo que ya construimos, la compuerta de consentimiento del apoderado de §4.8. Contenido y código cuentan la misma historia.

  Cubre: mayoría de edad y capacidad de ejercicio, confidencialidad médica frente a los padres, consentimiento informado propio, qué pasa con el SIS al cumplir 18 (`# TODO: confirmar con mentor`), y Ley 29733 sobre datos sensibles de salud. **Cada afirmación con su fuente citada dentro del contenido**, visible para el usuario.

- **Esqueletos (1–5 y 7):** título, objetivo de aprendizaje, habilidad asociada, y la estructura *aprender → practicar → desafío → tarea de la vida real → retroalimentación* vacía, con el sello visible **"Contenido pendiente de validación clínica del INSN"**.

- Si durante la hackathon un médico del INSN valida contenido, la lección 1 ("Mi condición") puede completarse también. Es ganancia extra, no requisito.

No inventes contenido clínico sobre Hunter. Un esqueleto honesto es más fuerte ante un jurado clínico que siete módulos que nadie del equipo puede defender.

### 4.7 · Conciliación de medicación

Archivos: `objetos_valor/origen_dato.py`, `entidades/conciliacion.py`, `servicios/conciliador.py`

```python
class OrigenDato(Enum):
    VERIFICADO_INSN = "verificado_insn"              # ~ EstadoCampo.VERDE
    INFORMADO_POR_PACIENTE = "informado_por_paciente" # ~ EstadoCampo.AMBAR
    PENDIENTE_DE_COTEJO = "pendiente_de_cotejo"       # ~ EstadoCampo.ROJO

class TipoDiscrepancia(Enum):
    FALTA_EN_PASAPORTE = "falta_en_pasaporte"
    FALTA_EN_DECLARACION = "falta_en_declaracion"
    DOSIS_DISTINTA = "dosis_distinta"
    FRECUENCIA_DISTINTA = "frecuencia_distinta"
```

`OrigenDato` es la capa de presentación de `EstadoCampo`. **No reemplaces `EstadoCampo`** — el dominio sigue en VERDE/ÁMBAR/ROJO y la interfaz traduce.

Reglas con test propio cada una:

- Lo que declara el paciente **nunca** sobrescribe el Pasaporte. Genera un `CasoDeConciliacion` asignado a `EQUIPO_INSN` (reglas 4 y 8).
- El sistema **nunca** decide cuál versión es la correcta. Solo reporta la discrepancia.
- Test bloqueante: `tests/dominio/test_conciliacion_no_modifica_pasaporte.py`.

### 4.8 · Consentimiento del apoderado

Archivo: `entidades/acceso_apoderado.py`

Antes de los 18: acceso por patria potestad. Desde el día del cumpleaños: **el acceso se corta automáticamente** y solo continúa si existe `ConsentimientoExplicito` otorgado por el paciente, con fecha y asiento en la cadena de auditoría.

Test bloqueante: `tests/dominio/test_acceso_apoderado_caduca_a_los_18.py`.

Esto convierte una pantalla en un mecanismo, y es lo que un jurado de salud reconoce como serio.

### 4.9 · Blindaje discursivo del IUT

El documento de las compañeras dice "la IA nunca determina urgencia ni decide prioridad clínica". Eso choca con el IUT solo en la redacción, pero un jurado puede usarlo para partirnos. Cierra el pendiente #7 de la rúbrica escribiendo esto como docstring de `calculadora_iut.py` y reproduciéndolo en el dossier:

> El IUT **no prioriza pacientes; ordena la cola de trabajo del equipo de transición**. No decide quién se atiende primero en un hospital: decide a quién llama primero la trabajadora social. Es transparente — `∂z/∂xᵢ = βᵢ`, cada factor con su peso visible y `e^βᵢ` interpretable como razón de momios —, es auditable, y **cualquier persona puede reordenar la cola a mano**, quedando ese reordenamiento registrado.

No toques los betas ni la fórmula. Los 5 casos hechos a mano deben seguir coincidiendo.

---

## 5. Cambios en `aplicacion/`

Casos de uso nuevos, uno por archivo, cada uno importando solo `dominio`:

```
aplicacion/avanzar_ciclo.py            # aplica transicion, valida, emite eventos
aplicacion/acciones_receptor.py        # las 6 acciones del hospital receptor
aplicacion/registrar_reingreso.py
aplicacion/evaluar_corte_etario.py     # metrica estrella
aplicacion/avanzar_aprendizaje.py
aplicacion/conciliar_medicacion.py
aplicacion/gestionar_acceso_apoderado.py
```

Las 6 acciones del receptor, cada una es una transición con responsable y plazo:

1. Confirmar recepción → `REFERENCIA_ENVIADA` → `RECEPCION_CONFIRMADA`
2. Iniciar evaluación → `RECEPCION_CONFIRMADA` → `EN_EVALUACION`
3. Solicitar información complementaria → no cambia estado; devuelve el turno al `EQUIPO_INSN` y reinicia el plazo. **Esta es la acción más importante de las seis**: es lo único que convierte un rechazo silencioso en una petición trazable.
4. Aceptar y asignar servicio/médico → `EN_EVALUACION` → `ACEPTADO_CON_SERVICIO`
5. Programar cita → `ACEPTADO_CON_SERVICIO` → `CITA_PROGRAMADA`
6. Confirmar primera atención → `CITA_PROGRAMADA` → `PRIMERA_ATENCION_CONFIRMADA`
   - Variante no-asistió → `REINGRESO` con motivo `NO_ASISTIO_A_PRIMERA_CITA`

Crea `tests/aplicacion/` con tests reales — hoy solo tiene `__init__.py`.

---

## 6. Cambios en `infraestructura/` — incluye la deuda pendiente

### 6.1 · Persistencia (cierra T3 y T4)

- Escribe los mappers `paciente_a_documento` / `paciente_desde_documento` y equivalentes para `Ciclo`, `ProgresoAprendizaje`, `CasoDeConciliacion`, `AccesoApoderado`.
- Conecta SQLite en `interfaz/arranque.py`. Hoy `app.py` importa **cero** módulos de infraestructura: eso significa que nada de lo construido está realmente enchufado.
- Implementa `contenedor.sembrar_demo(...)`, que `interfaz/cli/sembrar.py` ya llama y **no existe**.
- Test de ida y vuelta con 50 semillas: guardar, leer, comparar por igualdad estructural.
- Migración de esquema: sube `esquema_version` y escribe la migración de los estados legado de §4.1.

### 6.2 · Auditoría (cierra T5)

Conecta `RegistroAuditoria` a cada acción que cambie estado clínico o de acceso. Mínimo: transición de ciclo, verificación de campo digitalizado, resolución de conciliación, otorgamiento y revocación de consentimiento del apoderado.

La cadena de hash ya funciona y está probada (editar una fila por SQL devolvió `(False, 1)`). Falta que alguien la llame.

### 6.3 · WhatsApp: una sola ruta (cierra T6)

`app.py:890` construye `https://wa.me/51{telefono}?text={quote(cuerpo)}` **en línea**, saltándose el guardián de privacidad de `CanalWhatsAppEnlace`. Hay dos implementaciones paralelas y `test_privacidad_whatsapp` está certificando la que no se usa.

Borra la construcción en línea. Todo WhatsApp pasa por `CanalWhatsAppEnlace`. Después verifica que el test bloqueante realmente cubre la ruta viva — añade un test que falle si aparece la cadena `wa.me` en cualquier archivo fuera de ese adaptador.

El comportamiento visible no cambia: sigue abriendo la conversación con el texto preescrito, listo para enviar.

### 6.4 · PDF del acta (cierra T2, tercer intento)

En `acta_digitalizacion.py`:

- Línea ~110: `filas: list[list[str]]` usa cadenas planas. **Envuelve cada celda en `Paragraph`** con un `ParagraphStyle` de `wordWrap="CJK"` — `Paragraph` ya está importado y se usa para el título, pero no para las celdas.
- `colWidths=[42, 52, 52, 28] mm = 174 mm` **excede** los 170 mm útiles de A4 con márgenes. Bájalo a `[40, 50, 50, 30] = 170 mm`.
- Aplica `xml.sax.saxutils.escape()` a todo texto que entre a un `Paragraph`, o un `&` en el nombre de un establecimiento rompe el render.
- Prueba con el caso que falló: `Establecimiento` largo, y `Hospital Regional de Ucayali`.

### 6.5 · Destinos en el radar (cierra T7)

Conecta `DirectorioDestinos` al radar. Con el directorio vacío ya devuelve *"10 de 10 sin destino identificado (100 %)"*, y **esa cifra es el entregable de B1**. No la escondas: es la evidencia de brecha de oferta que el INSN puede llevar a una mesa de gestión. El sistema no inventa destinos; mide su ausencia.

### 6.6 · Datos de demostración — caso Hunter

Todo sintético (regla 1). En `config/semilla_demo.yaml`:

**Caso protagonista:** Mateo Silva Quispe, **17 años y 4 meses** — un único valor de edad en todos los documentos, código y diapositivas. Diagnóstico: Mucopolisacaridosis tipo II (Síndrome de Hunter), **CIE-10 E76.1**. Tratamiento: idursulfasa, infusión intravenosa semanal.

> **Regla 8.** No inventes la dosis. El campo de dosis va marcado `origen: SINTETICO_DEMO` y con `# TODO: confirmar con mentor`. Ninguna dosis de la semilla se presenta como referencia clínica en la interfaz.

Destino: `SinDestinoIdentificado`, motivo `NO_EXISTE_SERVICIO_ADULTO_EQUIVALENTE`, `es_brecha_de_oferta = True`. **Ese es el punto de elegir Hunter**: la demo muestra que el sistema no puede inventar un servicio de adultos que no existe, y en cambio produce la evidencia de que falta.

**Caso de contraste:** un paciente con asma persistente que **sí** tiene destino, para que en el radar se vea la diferencia de IUT y de disponibilidad de destino lado a lado.

**Cohorte de fondo:** 40 pacientes sintéticos con distribución de IUT que produzca semáforo rojo/ámbar/verde no trivial.

Verifica que todos los establecimientos citados existan en el catálogo oficial. En una iteración previa se inventaron nombres, lo que desincronizó el corpus del catálogo y contaminó las métricas.

---

## 7. `interfaz/` — API nueva y frontend nuevo

### 7.1 · Por qué API

Añadir `interfaz/api/` sin tocar una línea de `dominio/` ni `aplicacion/` **es** la demostración en vivo de la promesa del pitch: *"el núcleo no cambia, solo se cambia el adaptador de entrada"*. Deja constancia en el commit: el diff debe mostrar cero cambios en el núcleo entre el checkpoint C3 y el C4.

### 7.2 · FastAPI

`src/relevo/interfaz/api/` — un router por área, ninguno con lógica de negocio. Los handlers solo traducen HTTP ↔ casos de uso. Pydantic v2 en la frontera (regla de calidad existente).

```
GET  /api/pacientes                       # radar, con IUT y semaforo
GET  /api/pacientes/{id}
GET  /api/pacientes/{id}/ciclo            # estado, responsable, plazo, evidencia
POST /api/pacientes/{id}/ciclo/avanzar
GET  /api/pacientes/{id}/pasaporte
GET  /api/pacientes/{id}/aprendizaje
POST /api/pacientes/{id}/aprendizaje/avanzar
GET  /api/pacientes/{id}/lecciones/{n}
POST /api/pacientes/{id}/medicacion/declarar
GET  /api/pacientes/{id}/conciliacion
GET  /api/receptor/bandeja
POST /api/receptor/{id_ciclo}/{accion}
GET  /api/metricas/corte-etario           # la metrica estrella
GET  /api/metricas/cobertura-destinos
POST /api/demo/reiniciar                  # barra de control demo
POST /api/demo/avanzar-etapa
POST /api/demo/cambiar-rol
```

Tests de contrato: cada endpoint con al menos un caso feliz y uno de error, y verificación de que el código de estado HTTP corresponde.

FastAPI sirve también los estáticos, para que el despliegue sea un solo proceso.

### 7.3 · Frontend desde cero, con arquitectura

`src/relevo/interfaz/web/` — sin framework, sin paso de compilación, pero **con capas**.

```
web/
  index.html                 # unico HTML, contenedor y punto de montaje
  estatico/css/
    base.css                 # variables, tipografia, reset
    componentes.css
    vistas.css
  estatico/js/
    api.js                   # UNICO lugar con fetch(). Una funcion por endpoint
    estado.js                # store en memoria. Sin datos clinicos en el navegador
    enrutador.js             # router por hash
    componentes/             # turno.js, semaforo.js, badge_origen.js, linea_tiempo.js
    vistas/                  # una vista por archivo, cada una exporta render()
```

**Reglas duras del frontend, verificadas por script:**

- **Ningún archivo `.js` supera las 200 líneas.** Script `scripts/verificar_tamano_archivos.py` que falla el build si alguno lo hace. Esto es la respuesta directa y verificable a lo que salió mal en el otro MVP.
- **`fetch()` solo aparece en `api.js`.** Test que lo verifique por grep.
- **Prohibido `localStorage` / `sessionStorage` para datos clínicos.** Test `tests/interfaz/test_sin_almacenamiento_navegador.py` que falle si aparecen en cualquier archivo. Único uso tolerado: el rol seleccionado en la demo, y aun así prefiere memoria.

Motivo escrito en el código: la Ley 29733 clasifica los datos de salud como datos sensibles. Guardarlos en el navegador, sin cifrado, sin control de acceso y sin registro de quién los tocó, no es una implementación incompleta — es una que no se puede desplegar.

### 7.4 · Las 7 vistas

| # | Ruta | Contenido |
|---|---|---|
| 1 | `#/entrar` | Selección de rol: Paciente / Profesional INSN / Profesional receptor / Apoderado |
| 2 | `#/paciente` | Estado en lenguaje llano ("Tu nuevo hospital está revisando tu información"), próxima actividad recomendada, acceso al Pasaporte, tareas pendientes |
| 3 | `#/paciente/ruta` | Línea de tiempo de 7 etapas + **"¿Quién tiene el turno ahora?"** + "¿Qué tengo que hacer yo?" |
| 4 | `#/paciente/entrenate` | Franja etaria, mapa de 7 habilidades con sus estados, **lección 6 completa**, 6 lecciones esqueleto con su sello visible |
| 5 | `#/pasaporte/{id}` | Pasaporte 18+ con badges de origen, exportable a PDF por el endpoint existente |
| 6 | `#/insn/radar` | **Métrica de corte etario arriba de todo**, cohorte ordenada por IUT con semáforo, cobertura de destinos, filtros: requieren acción INSN / esperando al receptor / sin actualización reciente / completadas |
| 7 | `#/receptor/bandeja` | Referencias entrantes y las 6 acciones del receptor |

Vista del apoderado: **no** es una octava vista. Es la vista 2 con permisos recortados y el aviso de caducidad a los 18. Reutiliza, no dupliques.

Componente fijo en todas: **Barra de Control Demo** — cambiar rol, avanzar etapa, reiniciar. Consume `/api/demo/*`, que por debajo es lo que `sembrar.py` ya hace por CLI.

### 7.5 · Streamlit se queda como consola técnica — no es el producto

**No borres `app.py`.** Reenfócalo a lo que ya hace bien y no se va a reimplementar: digitalización con verificador, generación y evaluación de corpus, métricas del extractor, inspección de la cadena de auditoría.

Dos beneficios: (1) si la interfaz nueva no llega a tiempo, la demo técnica sigue en pie; (2) dos adaptadores distintos sobre un mismo núcleo, misma base de datos y misma auditoría **es la diapositiva de arquitectura** — no hay que explicarla, se muestra.

**Deja escrito en el `README` cuál es cuál, porque ya se confundieron una vez:**

| Cosa | Qué es | Cuándo se usa |
|---|---|---|
| Interfaz nueva (FastAPI + web) | **El producto.** Lo que ven paciente, INSN, receptor y apoderado | Toda la demo del pitch |
| Streamlit (`app.py`) | **La sala de máquinas.** Digitalización, corpus, métricas, auditoría | 30 segundos, solo si el jurado de software pide la prueba de arquitectura |
| `cloudflared` | Un cable prestado para compartir la demo | Solo entre el equipo, se apaga al terminar |

Quítale a `app.py` todo lo que la interfaz nueva cubre, y quítale la construcción en línea de `wa.me` de §6.3.

---

## 8. Postura de seguridad y comunicación con el modelo

### 8.1 · Cómo se enuncia el modelo de despliegue

La palabra correcta **no es "local en una laptop"** sino **on-premise: dentro de la red del hospital**. La laptop es la maqueta de ese modelo, no el modelo. En producción es un servidor institucional del INSN. Corrige esto en todo texto que digas lo contrario.

Lo que on-premise nos da frente a los grupos que usan API de OpenAI o Google: ellos realizan una **transferencia internacional de datos sensibles de salud** a un encargado de tratamiento fuera del Perú (Ley 29733). Nosotros no, porque el dato nunca sale de la red.

**Lo que sí tenemos resuelto:** integridad (cadena de hash que detecta manipulación, verificada), trazabilidad (auditoría por acción), cero terceros, cero costo por paciente.

**Brechas declaradas — escríbelas en `docs/INFORME_FUSION.md` y en el dossier, no las escondas:**

| Brecha | Estado | Respuesta de una línea si preguntan |
|---|---|---|
| TLS / HTTPS | No en la demo | La demo corre en red local. En piloto, certificado del servidor institucional. No cambia una línea de código |
| SQLite sin cifrar en disco | Pendiente | Se resuelve con cifrado de volumen o SQLCipher; no toca el dominio |
| Sin política de respaldos | Pendiente | Responsabilidad del área de TI del INSN sobre el servidor institucional |
| Sin integración con el directorio institucional | Pendiente | Los usuarios se crean a mano en el piloto; LDAP/AD es un adaptador más |

En C6, escribe esta tabla en el `README`. **Declarar una brecha conocida da seriedad; que la encuentre el jurado, no.**

### 8.3 · Roles y autenticación

**Cinco roles: cuatro de negocio y uno técnico.**

```python
class Rol(Enum):
    PACIENTE = "paciente"
    APODERADO = "apoderado"
    PROFESIONAL_INSN = "profesional_insn"
    PROFESIONAL_RECEPTOR = "profesional_receptor"
    ADMINISTRADOR = "administrador"
```

Decisiones que hay que respetar, cada una con su motivo:

- **`PROFESIONAL_INSN` y `PROFESIONAL_RECEPTOR` no son el mismo rol.** Están en instituciones distintas. El del INSN ve su cohorte; el receptor ve **únicamente las referencias dirigidas a su establecimiento**. Unificarlos daría al receptor visibilidad sobre toda la cohorte pediátrica del INSN, que es exactamente el problema de protección de datos que decimos evitar. Test: `tests/interfaz/test_aislamiento_por_rol.py` — un receptor pidiendo un paciente que no le fue referido recibe `404`, **no `403`** (un 403 confirma que el paciente existe).
- **`APODERADO` es `PACIENTE` con permisos recortados** y la caducidad de §4.8. No dupliques vistas ni lógica.
- **`ADMINISTRADOR` no tiene lectura clínica en la interfaz.** Puede sembrar, reiniciar, ver logs, ver métricas agregadas y verificar la cadena de auditoría. No puede abrir un Pasaporte ni una historia. En la práctica quien administre el servidor tendrá acceso al archivo SQLite —eso es inevitable—, y por eso **la cadena de hash existe**: si toca una fila por fuera, `verificar_cadena()` lo delata. Escribe ese razonamiento como docstring del rol; es la respuesta a "¿quién vigila al vigilante?".

**Autenticación — qué se implementa y por qué, en C6:**

| Necesidad | Solución | Por qué esta y no otra |
|---|---|---|
| Quién eres | Usuario + contraseña con hash **argon2id** (o bcrypt) | Nunca contraseñas en claro ni SHA plano |
| Mantener la sesión | **Cookie de sesión de servidor**, `HttpOnly`, `SameSite=Strict` | Ver abajo |
| Qué puedes ver | Comprobación de rol en cada endpoint + filtro por establecimiento | Autorización, distinta de autenticación |
| Confidencialidad en tránsito | TLS en el piloto | Brecha declarada en la demo |
| Confidencialidad en reposo | Cifrado de volumen / SQLCipher | Brecha declarada |

> **Aclaración que hay que tener firme antes del pitch: JWT no es encriptación.** Un JWT va **firmado**, no cifrado — su contenido es base64 y cualquiera lo lee. Aporta integridad y autenticidad, no confidencialidad. La confidencialidad en tránsito la da TLS, y la de reposo el cifrado del almacenamiento.
>
> **Elegimos sesión de servidor y no JWT** porque la ventaja del JWT es no guardar estado entre varios servicios, y aquí hay uno solo; y porque **un JWT no se puede revocar** sin una lista negra que ya es estado del servidor, o sea que se pierde lo único que se ganaba. Con sesión, expulsar a un usuario es borrar una fila. Deja este párrafo como docstring del módulo de autenticación: es la respuesta correcta si el jurado pregunta.

Cada inicio y cierre de sesión, y cada intento fallido, entra a la cadena de auditoría.

La frase que resume la postura y que debe aparecer en el dossier:

> Nuestro modelo puede equivocarse; nuestro sistema no puede equivocarse en silencio.

### 8.2 · Comunicación con el modelo

En el dossier y en la documentación de software, describe esto correctamente porque va a ser objeto de pregunta:

**No hay ningún túnel.** La aplicación hace un `POST` HTTP plano a `http://localhost:11434/api/generate` contra Ollama corriendo en la misma máquina. Nada sale de la red local, no hay API de pago, no hay dependencia de internet. Eso es precisamente lo que hace cierta la regla 3.

`cloudflared` es otra cosa y para otro momento: sirve **solo** para exponer la demo a las compañeras por un rato. Es un cable prestado, no arquitectura. No forma parte del sistema y **no debe aparecer en ningún diagrama**.

Y el modelo nunca decide: extrae. Toda extracción pasa por el verificador anti-error-silencioso (VERDE/ÁMBAR/ROJO) y toda salida clínica la firma una persona (regla 4).

---

## 9. Tests bloqueantes — la tabla actualizada

Los 4 existentes de `CLAUDE.md` siguen. Se agregan 6:

| Test | Qué verifica |
|---|---|
| `tests/test_arquitectura.py` | El dominio no importa nada externo |
| `tests/dominio/test_calculadora_iut.py` | Los 5 casos hechos a mano coinciden |
| `tests/infraestructura/test_privacidad_whatsapp.py` | Ningún mensaje contiene diagnósticos, CIE-10, medicamentos, dosis ni resultados — **y ahora sobre la ruta viva** |
| `tests/infraestructura/test_fhir.py` | El Bundle valida contra HAPI FHIR |
| `tests/dominio/test_aprendizaje_no_bloquea_referencia.py` | Ninguna habilidad pendiente impide una transición |
| `tests/dominio/test_reingreso_no_reabre_atencion.py` | Con ≥18 años, ninguna acción clínica del INSN es posible |
| `tests/dominio/test_conciliacion_no_modifica_pasaporte.py` | Lo declarado por el paciente nunca sobrescribe el dato verificado |
| `tests/dominio/test_acceso_apoderado_caduca_a_los_18.py` | Sin consentimiento explícito, el acceso se corta |
| `tests/interfaz/test_sin_almacenamiento_navegador.py` | Ningún dato clínico en `localStorage` |
| `tests/interfaz/test_tamano_archivos_js.py` | Ningún `.js` supera 200 líneas |
| `tests/interfaz/test_sin_captura_clinica_por_personal.py` | **Ningún endpoint de personal acepta campo clínico de escritura libre** (§3.2) |
| `tests/interfaz/test_aislamiento_por_rol.py` | El receptor solo ve las referencias dirigidas a su establecimiento; lo demás es `404` |

Actualiza la tabla de `CLAUDE.md` con las 6 nuevas.

---

## 10. Orden de construcción y puntos de control

De adentro hacia afuera, como siempre. **No avances con la suite en rojo.** Cada checkpoint es un commit.

| CP | Qué | Verde cuando |
|---|---|---|
| **C0** | Rama creada, suite existente en verde | 93 tests pasan |
| **C1** | Dominio: 9 estados, `Responsable`, tabla de transiciones, reingreso, corte etario | Tests de grafo + reingreso pasan; `mypy --strict` limpio; `test_arquitectura` verde |
| **C2** | Dominio: aprendizaje, conciliación, consentimiento | Los 3 tests bloqueantes nuevos de dominio pasan |
| **C3** | Infra: mappers, `sembrar_demo`, auditoría conectada, semilla Hunter, migración de estados | Ida y vuelta de 50 semillas; cadena de hash verifica; `sembrar.py` corre de punta a punta |
| **C4** | API FastAPI + tests de contrato | Todos los endpoints responden; **diff del núcleo entre C3 y C4 = 0 líneas**. `git push -u origin fusion/entrenate-receptor` |
| **C5** | Frontend: 7 vistas + barra demo | Recorrido completo de las 7 etapas visible desde 3 roles; tests de tamaño y de `localStorage` pasan |
| **C6** | **Autenticación y roles (§8.3)**, deudas: PDF (T2), WhatsApp (T6), destinos en radar (T7), Streamlit reenfocado, brechas declaradas en README (§8.1), pendientes 3 y 5 de rúbrica | Login funciona con los 5 roles; `test_aislamiento_por_rol` pasa; el acta se genera sin desborde; `wa.me` solo en el adaptador |
| **C7** | FHIR CorePE (T8) y ajustes finales de rúbrica | `test_fhir` pasa |

Si el tiempo se acaba, **C0–C5 es un sistema presentable y coherente**. C6 es deuda visible que ya está diagnosticada. C7 es diferenciador, no requisito.

---

## 11. Pendientes de rúbrica que quedan cubiertos y los que no

De `MAPEO_RUBRICA_INSN.md`:

| # | Pendiente | Estado tras esta fusión |
|---|---|---|
| 1 | `PERDIDA_DE_SEGUIMIENTO` y `REINGRESO` en el enum | **Cubierto** (§4.1) |
| 2 | `Responsable` en la transición | **Cubierto** (§4.2) |
| 3 | Checklist con los seis ítems literales del INSN | **Pendiente** — hazlo en C6 si hay tiempo |
| 4 | Registro de "transferencia cálida" | **Cubierto** por las acciones del receptor (§5) |
| 5 | Sección psicosocial del Pasaporte | **Pendiente** — 20 min, hazlo en C6 |
| 6 | Página educativa en Pasaporte V1/V2 | **Cubierto** por Entrénate (§4.6) |
| 7 | Blindar el discurso del IUT | **Cubierto** (§4.9) |

---

## 12. Lo que NO se construye en esta fusión

Además de la tabla que ya está en `CLAUDE.md`:

- **No** se reutiliza ni se porta el JS de las compañeras. Se reescribe.
- **No** se usa `localStorage` para nada clínico.
- **No** se escribe contenido clínico sobre Hunter. Esqueletos sellados.
- **No** se inventan dosis, ni en la semilla, ni en la interfaz, ni en la extracción.
- **No** se toca `main` ni la rama de Ollama.
- **No** se cambian los betas del IUT ni la fórmula.
- **No** aparece `cloudflared` en el diagrama de arquitectura.
- **No** se borra `app.py`.
- **No** se usa la palabra "módulo" para las lecciones de Entrénate.
- **No** se ocultan las brechas de seguridad de §8.1. Se declaran.
- **No** se pide al personal de salud teclear ningún dato clínico (§3.2). Ni uno.
- **No** se unifican los roles de profesional INSN y profesional receptor.
- **No** se guarda dato clínico en el JWT ni en ningún token — de hecho no se usa JWT (§8.3).
- **No** se le da lectura clínica al rol `ADMINISTRADOR` en la interfaz.

---

## 13. Cómo se comparte con el equipo cuando esté listo

```bash
uvicorn relevo.interfaz.api.principal:app --host 0.0.0.0 --port 8000
```

Para que las compañeras lo vean desde sus máquinas, sin desplegar nada y sin costo:

```bash
cloudflared tunnel --url http://localhost:8000
```

Todos los datos son sintéticos, así que exponerlo temporalmente no viola la regla 1. Aun así, apaga el túnel al terminar la sesión de revisión.

---

## 14. Al terminar, deja un informe

Escribe `docs/INFORME_FUSION.md` con: qué checkpoints cerraste, qué tests nuevos hay y qué cubren, qué quedó pendiente y por qué, y qué `# TODO: confirmar con mentor` nuevos aparecieron. Ese archivo es el insumo directo de la documentación de software que viene después.
