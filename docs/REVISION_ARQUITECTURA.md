# Revisión de arquitectura — Relevo

**Fecha:** 15 de agosto de 2026
**Alcance:** estructura completa, modelado de negocio, cobertura de los dolores, contraste con la práctica actual.
**Método:** árbol completo, conteo de líneas por módulo, grafo de importaciones de la interfaz, superficie pública de las entidades de dominio.

---

## Veredicto en una frase

> **El dominio está bien construido. La capa de aplicación es vestigial y la interfaz se la comió. Y el modelo de negocio describe con detalle *el análisis* y casi nada *el acompañamiento*, que es donde viven los dolores que el proyecto dice resolver.**

No es un problema de código: es un problema de qué se modeló y qué no.

---

# PARTE 1 — Lo que está bien, y no es poco

Conviene decirlo antes de la crítica, porque hay decisiones aquí que no son habituales ni siquiera en código profesional.

### El dominio no es anémico

`Paciente` tiene catorce métodos con comportamiento real: `ventana()`, `cohorte()`, `diagnosticos_contables`, `contacto_preferente()`, `tiene_contacto_vigente()`. No es una bolsa de datos con servicios manipulándola desde fuera. Eso es lo contrario del *anemic domain model*, que es la enfermedad más común en proyectos que dicen usar arquitectura limpia.

### Estados ilegales irrepresentables

`IndiceUrgencia` **no se puede construir sin sus aportes**, y valida en `__post_init__` que vengan ordenados. `CampoExtraido` no existe sin motivo declarado. Un campo verde no puede tener valor nulo.

Eso es *make illegal states unrepresentable*, y es práctica de primera línea. La mayoría de proyectos valida en la frontera y confía hacia dentro; aquí el tipo mismo impide el estado inválido.

### Inyección obligatoria de la política clínica

Quitar el `default_factory` de `CalculadoraIUT` fue la decisión más importante del proyecto. Hoy es **imposible** que el sistema calcule con pesos que ningún médico aprobó, porque sin política cargada no arranca. Fallar ruidosamente donde importa la seguridad es exactamente lo correcto.

### Sin reloj en el dominio

`hoy` se pasa siempre por parámetro. Nada consulta la hora del sistema. Por eso los cinco casos del IUT se pueden calcular en papel y comparar. Es *functional core, imperative shell* bien aplicado, y es lo que hace que 500+ líneas de tests de dominio corran en milisegundos sin un solo mock.

### `CicloTransicion` ya registra eventos

`EventoCiclo` con `avanzar()` y `FuenteConfirmacion` — el ciclo lleva su propia historia en vez de tener solo un campo `estado`. Está a un paso de event sourcing y ese paso está bien dado.

### Lenguaje ubicuo real

`cohorte`, `contrarreferencia`, `ventana_transicion`, `diagnosticos_contables`, `fuente_de_confirmacion`. Un médico del INSN puede leer los nombres de las clases y entenderlos. Eso vale más de lo que parece: es lo que permite que el mentor corrija el modelo sin saber programar.

---

# PARTE 2 — Contra la práctica actual

| Patrón | Estado | Juicio |
|---|---|---|
| **Puertos y adaptadores** | ✅ correcto | Y justificado, no por moda: la promesa del pitch es la intercambiabilidad del adaptador. |
| **Objetos de valor inmutables** | ✅ | `frozen=True, slots=True` en todo. |
| **Tipado estricto** | ✅ | `mypy --strict` sobre dominio. |
| **Núcleo funcional / cáscara imperativa** | ✅ | Sin reloj, sin E/S, sin estado global en el dominio. |
| **Repositorios** | ✅ | Puerto definido, adaptador en memoria, SQLite aplazado con criterio. |
| **Entidades ricas** | ✅ | `Paciente` tiene comportamiento. |
| **Agregados con frontera explícita** | ❌ | Ver §3.1. No hay raíz de agregado ni invariantes entre entidades. |
| **Eventos de dominio publicados** | ❌ | Ver §3.2. **El hueco más grande.** |
| **Contextos delimitados** | ❌ | Ver §3.3. Dos subdominios en el mismo paquete. |
| **Capa de aplicación** | 🔴 | Ver §3.4. Prácticamente no existe. |
| **Pirámide de tests** | 🟠 | Dominio excelente, aplicación cero, infraestructura mínima. |
| **CQRS / modelos de lectura** | ⚪ | No hace falta a este volumen. Correcto no tenerlo. |
| **Arquitectura por rebanadas verticales** | ⚪ | Alternativa legítima a hexagonal. La elección actual es defendible. |

**Lectura general:** el proyecto aplica muy bien los patrones *estructurales* (capas, puertos, tipos) y no aplica los patrones *de comportamiento* (agregados, eventos, contextos). Y este dominio es de comportamiento: trata de cosas que pasan en el tiempo y de plazos que vencen.

---

# PARTE 3 — Los cuatro problemas reales

## 3.1 · No hay agregado. `Paciente` y `CicloTransicion` flotan sueltos

Son dos entidades independientes sin frontera que las una. Nada impide, hoy, que un ciclo avance para un paciente que ni siquiera está en la cohorte activa, o que existan dos ciclos abiertos para el mismo paciente.

En un dominio clínico eso no es teoría: **un paciente con dos transiciones abiertas es un paciente que se va a perder dos veces.**

Falta la raíz de agregado. Y el nombre correcto no es ninguno de los dos: es **`TransicionDePaciente`** — la cosa que tiene identidad, ciclo de vida e invariantes.

## 3.2 · El sistema es temporal y reactivo, pero el modelo es estático y consultado

Este es el hueco conceptual grande.

Todo el negocio es que **pasan cosas**: se emite un Pasaporte, se registra una referencia, vence un plazo, alguien confirma una cita. `CicloTransicion` ya lo registra internamente con `EventoCiclo` — pero **esos eventos no salen de la entidad.** Nadie se suscribe. Nada reacciona.

La consecuencia se ve en el código que falta: existe `dominio/puertos/notificacion.py` (107 líneas de puerto) y **no existe ni un solo adaptador que lo implemente.** No existe `correr_noche.py`. El motor del cierre de ciclo está construido y desconectado.

Y no es casualidad: **con un modelo consultado, para enterarte de un vencimiento tienes que ir a preguntar.** Alguien tiene que escribir el bucle que recorre todos los ciclos todos los días. Con eventos de dominio, el vencimiento se publica y la capa de avisos se suscribe — que es exactamente el principio rector del proyecto, *"el sistema busca a la persona"*, expresado en código.

**El principio de diseño ya está escrito en el dossier. Falta en el modelo.**

## 3.3 · Digitalización y transición son dos subdominios en el mismo paquete

`verificador_extraccion.py` son 570 líneas — el archivo más grande del dominio — y **no tiene absolutamente nada que ver con la transición pediátrico-adulto.** Trata de leer documentos. Lo mismo `campo_extraido.py`.

Son dos subdominios distintos:

| | Subdominio | Naturaleza |
|---|---|---|
| **Transición** | Núcleo | Es el problema del reto. Nadie más lo va a resolver igual. |
| **Digitalización** | Soporte | Sirve para cualquier documento de cualquier hospital. Genérico. |

Mezclarlos tiene un costo concreto: el día que quieras usar el módulo de digitalización en otra cosa —o mostrarlo aparte en el pitch— está enredado con `Paciente` y `CicloTransicion`.

## 3.4 · 🔴 La capa de aplicación es vestigial y `app.py` la absorbió

**Los números:**

```
src/relevo/interfaz/web/app.py        1 426 líneas
src/relevo/aplicacion/                  165 líneas   (un solo caso de uso)
                                      ─────────────
                                      razón 8.6 : 1
```

Y `app.py` importa **ocho módulos de infraestructura directamente**, además de `CalculadoraIUT` y `ClasificadorCohorte` del dominio:

```
relevo.infraestructura.llm            (×3)
relevo.infraestructura.configuracion  (×3)
relevo.infraestructura.documentos     (×2)
relevo.infraestructura.persistencia
relevo.infraestructura.fuentes
relevo.dominio.servicios              (×2)
```

Eso significa que **la interfaz sabe *cómo* se prioriza, no solo *que puede pedir* una priorización.** Sabe qué calculadora instanciar, qué catálogo cargar, qué lector elegir, cómo generar el PDF.

Tres consecuencias:

1. **La promesa del pitch se debilita.** Decimos "solo se cambia el adaptador". Cambiar Streamlit por FastAPI hoy obliga a reescribir la orquestación entera, porque vive en el adaptador.
2. **No se puede probar.** `tests/aplicacion/` tiene solo `__init__.py`. Cero tests de casos de uso, porque no hay casos de uso que probar: la lógica está en funciones de Streamlit que necesitan un navegador.
3. **`test_arquitectura.py` no lo ve.** Verifica que el dominio no importe hacia afuera — y eso pasa. **No verifica que la interfaz no salte por encima de la aplicación.** La regla se está rompiendo en la dirección que el test no mira.

**Esto no invalida la arquitectura. Es hexagonal hecho a medias:** un hexágono bien construido con un adaptador conductor monolítico que mete la mano por dentro.

---

# PARTE 4 — ¿Modela el negocio?

Aquí está la crítica de fondo, y es más interesante que las anteriores.

## Lo que el modelo dice del negocio

Leyendo solo el dominio, sin documentación, se entiende que:

- Hay pacientes con diagnósticos, dispositivos, contactos y una fecha de corte
- Hay una forma de puntuar su urgencia, explicable factor por factor
- Hay un ciclo de derivación con estados y plazos
- Hay un documento de traspaso

**Eso es un excelente modelo de un motor de priorización.**

## Lo que el negocio tiene y el modelo no nombra

| Concepto del negocio | ¿Existe en el modelo? |
|---|---|
| **Destino de la derivación** | ❌ No hay `Destino` ni `DirectorioDestinos`. B1 no está ni nombrado. |
| **Plan de transición** | ❌ El Pasaporte es un documento, no un plan. Sin pasos, sin responsable, sin fechas. |
| **Preparación del paciente** | ❌ TRAQ es un `float` dentro de una fórmula. No hay `EvaluacionPreparacion` con fecha, respuestas y evolución. |
| **Quién hace el trabajo** | ❌ No hay `Coordinador` ni responsable. Todo pasa sin que nadie sea dueño de nada. |
| **Capacidad del equipo** | 🟠 Es un parámetro de una función, no un concepto. Y es lo que define el umbral rojo. |
| **El aviso** | 🟠 Hay puerto, no hay entidad ni implementación. |
| **El programa de transición** | ❌ Los Six Core Elements no aparecen por ningún lado. |

## El diagnóstico

> **El modelo describe el estado del paciente con enorme detalle y el proceso de acompañarlo casi nada.**

Y esto explica algo que veníamos arrastrando sin nombrarlo: **B1 y B3 no están "sin implementar". Están sin modelar.** Y eso es peor, porque no se puede implementar lo que no se ha nombrado. Mientras `Destino` no sea una clase, el problema del destino no existe para el software — solo existe en el dossier.

Frase honesta para el equipo:

> Tenemos un motor de priorización excelente vestido de sistema de acompañamiento.

## Y hay algo que el modelo sí capta y merece nota aparte

`Motivo`, `AjusteCatalogo`, `fue_corregido`, `dato_faltante`, `confianza`, `FuenteConfirmacion`.

**El modelo trata la incertidumbre como parte del dominio, no como un detalle técnico.** Eso es raro y es correcto: en medicina, *"lo sé"* y *"lo supongo"* son estados clínicos distintos, y el código los distingue. Un revisor con criterio lo va a notar.

---

# PARTE 5 — ¿Mata los dolores?

| Dolor | Modelado | Implementado | Veredicto |
|---|---|---|---|
| **B1** · No hay destino | ❌ | ❌ | **No lo toca.** Ni siquiera está nombrado en el dominio. |
| **B2** · La información no viaja | ✅ | 🟠 | Pasaporte y Acta sí. **FHIR sigue en cero** — `interoperabilidad/` no existe. |
| **B3** · El paciente no está preparado | ❌ | ❌ | Se **mide** con TRAQ. No se **trabaja**. Medir el dolor no es tratarlo. |
| **B4** · Nadie cierra el ciclo | ✅ | 🔴 | Modelado con excelencia. **Sin avisos, sin proceso nocturno: no se dispara solo.** |

**Uno de cuatro.** Y el que más duele es B4: es el único donde el trabajo difícil ya está hecho —máquina de estados, plazos calibrados con el dato peruano, doble fuente de confirmación— y falta la parte fácil.

Los dos tests bloqueantes que faltan (`test_privacidad_whatsapp`, `test_fhir`) son exactamente los de B2 y B4.

---
---

# PARTE 6 — Correcciones · para el agente de código

Ejecutar en este orden. Cada bloque tiene criterio de aceptación.

**Regla que aplica a todo lo que sigue:** las reglas de `CLAUDE.md` no se tocan. En particular, el dominio sigue sin importar nada externo, y `mypy --strict` sigue limpio.

---

## A1 · 🔴 Cerrar el agujero que el test de arquitectura no ve

**Problema:** `test_arquitectura.py` verifica que el dominio no importe hacia afuera, pero no que la interfaz no salte por encima de la aplicación.

**Añadir a `tests/test_arquitectura.py`:**

```python
def test_la_interfaz_no_importa_infraestructura_directamente() -> None:
    """La interfaz habla con casos de uso, no con adaptadores.

    Excepcion unica: el arranque (composicion de dependencias), que por
    definicion conoce las implementaciones concretas. Vive en
    `interfaz/arranque.py` y en ningun otro sitio.
    """
    PERMITIDOS = {"relevo/interfaz/arranque.py"}
    infracciones = []
    for archivo in Path("src/relevo/interfaz").rglob("*.py"):
        if archivo.as_posix().endswith(tuple(PERMITIDOS)):
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                if nodo.module.startswith("relevo.infraestructura"):
                    infracciones.append(f"{archivo}: {nodo.module}")
    assert not infracciones, (
        "La interfaz importa infraestructura directamente:\n  "
        + "\n  ".join(infracciones)
        + "\n\nEso significa que sabe COMO se hace en vez de QUE pedir. "
        "Mover la orquestacion a un caso de uso en aplicacion/."
    )


def test_la_interfaz_no_usa_servicios_de_dominio_directamente() -> None:
    """Instanciar CalculadoraIUT desde la pantalla es hacer de capa de aplicacion."""
    prohibidos = {"CalculadoraIUT", "ClasificadorCohorte", "MaquinaCiclo",
                  "VerificadorExtraccion"}
    # misma exploracion AST, buscando ImportFrom de relevo.dominio.servicios
```

**Correr y anotar el número de infracciones.** Es la línea base del refactor.

**Criterio:** el test existe, corre y **falla**. Que falle es el punto: hace visible la deuda.

---

## A2 · 🔴 Extraer los casos de uso de `app.py`

`app.py` son 1426 líneas contra 165 de aplicación. Hay que invertir esa razón.

**Crear en `src/relevo/aplicacion/`:**

| Caso de uso | Qué orquesta |
|---|---|
| `digitalizar_documento.py` | imagen → lectores → verificador → reporte |
| `confirmar_digitalizacion.py` | reporte verificado + revisor → `Paciente` + acta |
| `emitir_pasaporte.py` | paciente + versión por edad → documento |
| `evaluar_vencimientos.py` | recorre ciclos, detecta plazos vencidos |
| `despachar_avisos.py` | vencimientos → mensajes por canal |
| `registrar_confirmacion.py` | marca cita cumplida, con su fuente |

Cada uno recibe sus dependencias **por constructor, como puertos**. Ninguno importa Streamlit. Ninguno importa un adaptador concreto.

**Crear `src/relevo/interfaz/arranque.py`** — el único sitio que conoce implementaciones concretas:

```python
@dataclass(frozen=True, slots=True)
class Contenedor:
    """Composicion de dependencias. El unico lugar donde se nombran adaptadores.

    Todo lo demas recibe puertos. Cambiar SQLite por Postgres, Ollama por otro
    lector o Streamlit por FastAPI se hace aqui y en ningun otro archivo — que
    es, literalmente, la promesa que hacemos en el pitch.
    """
    priorizar: PriorizarCohorte
    digitalizar: DigitalizarDocumento
    confirmar: ConfirmarDigitalizacion
    emitir_pasaporte: EmitirPasaporte
    evaluar_vencimientos: EvaluarVencimientos

def construir(config: Path = Path("config")) -> Contenedor:
    ...
```

`app.py` pasa a importar **solo** `arranque.construir()` y los DTO. Nada más.

**Criterio de aceptación:**
- `app.py` por debajo de **500 líneas**
- Sus únicos imports de `relevo` son `interfaz.arranque` y `aplicacion.dto`
- `test_la_interfaz_no_importa_infraestructura_directamente` **pasa**
- Al menos **un test por caso de uso** en `tests/aplicacion/`, con dobles de los puertos
- Todo lo que funcionaba antes sigue funcionando

---

## A3 · 🔴 Eventos de dominio, y conectar B4

Es lo que convierte el principio *"el sistema busca a la persona"* de frase del dossier en código.

**En `dominio/eventos.py`** (sin dependencias externas):

```python
@dataclass(frozen=True, slots=True)
class EventoDominio:
    """Algo que paso. Inmutable, fechado, y con el paciente al que le paso."""
    ocurrido_en: date
    paciente_id: str

@dataclass(frozen=True, slots=True)
class PlazoVencido(EventoDominio):
    """Una etapa del ciclo supero su plazo.

    Es EL evento del proyecto: la contrarreferencia se documenta al 0.55% en el
    Peru, asi que el unico modo de cerrar el ciclo es que el vencimiento avise.
    """
    estado: EstadoCiclo
    dias_transcurridos: int
    destinatario: str

@dataclass(frozen=True, slots=True)
class PacienteEntroEnVentana(EventoDominio): ...

@dataclass(frozen=True, slots=True)
class PasaporteEmitido(EventoDominio):
    version: int          # 14, 16 o 17 anios

@dataclass(frozen=True, slots=True)
class CitaConfirmada(EventoDominio):
    fuente: FuenteConfirmacion
```

**`CicloTransicion.avanzar()` y `evaluar_vencimientos` devuelven eventos.** No los publican: el dominio no conoce el bus. Los devuelve, y el caso de uso los pasa a `despachar_avisos`.

Es lo más simple que funciona y mantiene el dominio puro.

**Y crear `interfaz/cli/correr_noche.py`:**

```python
"""El proceso nocturno. Corre solo, no le pide nada a nadie.

    python -m relevo.interfaz.cli.correr_noche

Lee la cohorte, recalcula el IUT, evalua vencimientos, prepara borradores de
Pasaporte y deja la cola de avisos lista. Nadie tiene que abrir una pantalla:
al dia siguiente llega el correo.
"""
```

**Criterio:** un test que simula el paso del tiempo sobre una cohorte y verifica que se emite `PlazoVencido` con el destinatario correcto por cada transición del §7 de `PLAN_TECNICO`.

---

## A4 · 🟠 Separar el contexto de digitalización

**Mover, sin cambiar una línea de lógica:**

```
dominio/objetos_valor/campo_extraido.py        →  digitalizacion/dominio/campo_extraido.py
dominio/servicios/verificador_extraccion.py    →  digitalizacion/dominio/verificador.py
infraestructura/llm/*                          →  digitalizacion/infraestructura/*
infraestructura/corpus/*                       →  digitalizacion/infraestructura/corpus/*
```

Nueva estructura:

```
src/relevo/
├── transicion/        ← dominio nucleo
│   ├── dominio/
│   ├── aplicacion/
│   └── infraestructura/
├── digitalizacion/    ← subdominio de soporte, reutilizable
│   ├── dominio/
│   └── infraestructura/
└── interfaz/          ← comparte adaptador conductor
```

**La regla entre contextos:** `digitalizacion` **no importa nada de `transicion`.** Publica un `DocumentoDigitalizado` genérico. La traducción de eso a un `Paciente` la hace una capa anticorrupción en `transicion/aplicacion/`.

Así el módulo de digitalización sirve para cualquier documento de cualquier hospital — que es la verdad, y se puede presentar aparte.

**Criterio:** un test que verifique que `digitalizacion/` no importa `transicion/`. `mypy --strict` limpio en ambos.

*(Si el tiempo aprieta antes del pitch, A4 se puede aplazar: es deuda estructural, no un fallo. A1, A2 y A3 no.)*

---

## A5 · 🟠 Nombrar en el dominio lo que el negocio tiene

No hace falta implementarlo todo. **Hace falta nombrarlo**, porque lo que no tiene nombre no existe para el software.

```python
# transicion/dominio/entidades/destino.py
@dataclass(frozen=True, slots=True)
class Destino:
    """Un servicio de adultos que puede recibir a un paciente.

    B1 del dossier. Hoy en el Peru puede sencillamente NO existir un servicio
    adulto para una enfermedad rara, y ese vacio es parte del diagnostico del
    problema — por eso se modela como ausencia posible y no como campo opcional
    olvidado.
    """
    codigo_renaes: str
    nombre: str
    especialidad: str
    cie10_que_atiende: tuple[str, ...]
    contacto: str | None
    confirmado_por: str | None    # quien valido que este destino recibe

@dataclass(frozen=True, slots=True)
class SinDestinoIdentificado:
    """No hay a donde derivar. Es un RESULTADO valido, no un error.

    Que el sistema pueda contar cuantos pacientes salen asi es, por si solo,
    una contribucion: hoy nadie lo sabe porque nadie lo cuenta.
    """
    motivo: str
    cie10: str
```

Y en la misma línea, mínimo viable:

- `EvaluacionPreparacion` — TRAQ con fecha y respuestas, no un `float` suelto. Sin eso, B3 no es un proceso: es un número.
- `CapacidadEquipo` — objeto de valor, no parámetro. Define el umbral rojo; merece nombre.
- `Responsable` — quién es dueño de una transición.

**Criterio:** `Destino` y `SinDestinoIdentificado` existen, y el Radar puede mostrar *"de N transferidos, M salieron sin destino identificado"*. **Ese número es entregable de pitch aunque el directorio esté vacío.**

---

## A6 · 🟠 El agregado

```python
# transicion/dominio/entidades/transicion_paciente.py
@dataclass
class TransicionDePaciente:
    """Raiz de agregado. Une paciente, ciclo, pasaportes y destino.

    Existe para hacer cumplir invariantes que hoy nada protege:
      · un paciente no puede tener dos transiciones abiertas
      · no se emite Pasaporte para quien no esta en cohorte activa
      · el ciclo no avanza si la transicion esta cerrada

    Un paciente con dos transiciones abiertas es un paciente que se pierde dos
    veces. Por eso la frontera del agregado no es academica aqui.
    """
    paciente: Paciente
    ciclo: CicloTransicion | None
    pasaportes: tuple[Pasaporte, ...]
    destino: Destino | SinDestinoIdentificado | None
    responsable: str | None
```

Los repositorios pasan a devolver el agregado, no piezas sueltas.

**Criterio:** tests que comprueben que cada invariante lanza excepción al violarse.

---

## A7 · 🟡 Cerrar los dos tests bloqueantes que faltan

De `CLAUDE.md`, siguen sin existir:

- `tests/infraestructura/test_privacidad_whatsapp.py` — requiere primero el adaptador de notificación
- `tests/infraestructura/test_fhir.py` — requiere el exportador CorePE

Ambos son promesas escritas del proyecto. **FHIR además es el diferenciador número uno del dossier y sigue en cero.**

---

## Orden y criterio de corte

| # | Qué | Bloqueante para el pitch |
|---|---|---|
| A1 | Test que expone la fuga | **Sí** — hace visible el problema |
| A2 | Extraer casos de uso + arranque | **Sí** — sostiene la promesa central |
| A3 | Eventos + `correr_noche` | **Sí** — es B4, y B4 está a medio metro |
| A5 | Nombrar `Destino` | **Sí** — barato, y convierte B1 de agujero en hallazgo |
| A7 | FHIR + privacidad WhatsApp | **Sí** — son promesas escritas |
| A4 | Separar contextos | No — deuda estructural |
| A6 | Agregado | No — pero hacerlo antes de que crezca más |

**Al terminar A1–A3, volver a correr todo:**

```powershell
python -m pytest tests/ -q
python -m mypy --strict src/relevo/
python -m relevo.interfaz.cli.correr_noche
streamlit run src/relevo/interfaz/web/app.py
```

**Verificación final:**

- [ ] `app.py` < 500 líneas y sin imports de infraestructura
- [ ] Al menos un test por caso de uso en `tests/aplicacion/`
- [ ] `correr_noche.py` corre y emite eventos
- [ ] `test_arquitectura.py` pasa con las dos reglas nuevas
- [ ] `mypy --strict` limpio sobre `src/relevo/` completo
- [ ] El Radar muestra el conteo de pacientes sin destino identificado
- [ ] Todo lo que funcionaba sigue funcionando

---

## Cierre

La arquitectura no está mal elegida ni mal entendida. Está **a medio terminar en la dirección menos visible**: hacia afuera del hexágono, no hacia adentro.

El dominio —que es lo difícil y lo que la mayoría hace mal— está bien. Lo que falta es la capa que lo conecta con el mundo, y nombrar en el modelo las tres o cuatro cosas del negocio que hoy solo existen en el dossier.

Con A1, A2, A3 y A5 hechos, la frase del pitch deja de ser una promesa y pasa a ser algo que se puede demostrar abriendo un archivo.
