# Arquitectura de Relevo — guía para el equipo

**Para quién es esto:** cualquiera del equipo Avellana que vaya a tocar el código, o que tenga que explicarlo delante del jurado. No hace falta saber Python de antes; sí ayuda haber programado orientado a objetos.

**Cómo está organizado:** cada pieza se explica con tres cosas — qué hace, cómo funciona por dentro, y **qué dolor concreto cubre**. Esa tercera parte es la que importa. Un sistema se defiende por los problemas que resuelve, no por las clases que tiene.

---

## 0 · Un puente desde lo que ya conoces

Si vienes del prototipo en Java, ya usaste esta arquitectura sin llamarla así:

```
Java (prototipo)          Python (este repo)         qué es
─────────────────         ──────────────────         ──────────────────────────
model/Paciente.java   →   dominio/entidades/     →   las cosas del problema
service/*.java        →   dominio/servicios/     →   las reglas que operan sobre ellas
ui/ConsoleMenu.java   →   interfaz/web/          →   por dónde entra un humano
```

La diferencia es una sola, y es la que da el nombre: aquí `dominio/` **no puede importar nada externo**. Ni base de datos, ni framework web, ni librería de red. Solo Python estándar.

Esa restricción no es capricho. Es lo que hace verificable la frase que decimos al jurado: *"el núcleo no cambia, solo se cambia el adaptador de entrada según el sistema del hospital."* Si el dominio importara la librería de base de datos, la frase sería mentira y tendrían razón en no creernos.

---

## 1 · El hecho que define todo el sistema

> **El INSN San Borja no atiende a mayores de 18 años bajo ninguna circunstancia.**

No es una demora de atención. Es una **interrupción total, en fecha exacta**.

Un paciente con cardiopatía congénita que lleva quince años en control, el día que cumple 18 deja de tener dónde ir. Hoy simplemente desaparece del sistema: nadie sabe si llegó a un hospital de adultos, si abandonó el tratamiento o si murió.

Todo lo que sigue existe por esa frase. Cuando algo del diseño parezca raro, la explicación casi siempre es esta.

---

## 2 · La arquitectura: hexagonal (puertos y adaptadores)

```
        interfaz ────────┐
                         ├──►  aplicacion  ──►  dominio
   infraestructura ──────┘                        ▲
                                                  │
                     (define los puertos que ambos implementan)
```

**Las flechas apuntan hacia adentro. Siempre.** Esa es toda la regla.

| Capa | Puede importar | Contiene |
|---|---|---|
| `dominio/` | **nada externo** | Entidades, objetos de valor, reglas, puertos |
| `aplicacion/` | solo `dominio` | Casos de uso que orquestan |
| `infraestructura/` | hacia adentro | Adaptadores: archivos, PDF, modelos, memoria |
| `interfaz/` | hacia adentro | Streamlit, línea de comandos |

**El dolor que cubre:** no sabemos si el INSN tiene historia clínica electrónica, ni si hay API, ni con qué esquema. Si el núcleo dependiera de esa respuesta, tendríamos que esperar a saberla para programar. Con esta separación, el núcleo se construyó completo sin conocerla, y el día que se sepa se escribe un adaptador nuevo sin tocar una sola regla clínica.

Y hay un segundo dolor, más inmediato: **el wifi del evento va a fallar**. Un núcleo sin dependencias externas corre igual con el cable desenchufado.

---

## 3 · El dominio, pieza por pieza

### 3.1 · `VentanaTransicion` — el tiempo que queda

```python
VentanaTransicion(fecha_nacimiento, hoy).meses_restantes  # → 14
```

Cuenta **hacia atrás** desde el cumpleaños 18. Expone `edad`, `dias_restantes`, `meses_restantes`, `cohorte`, `esta_cerrada`.

Reparte a los pacientes en tres grupos:

| Cohorte | Edad | Qué se hace |
|---|---|---|
| `PREVIA` | < 14 | Se registra, no se trabaja |
| `ACTIVA` | 14–17 | Se prioriza, se prepara, se emite Pasaporte |
| `SEGUIMIENTO` | ≥ 18 | Ya no es paciente del INSN, pero el ciclo sigue abierto |

**Detalles que parecen menores y no lo son:**

- Quien nació el 29 de febrero cumple el **1 de marzo** en años no bisiestos, no el 28. Se resolvió así porque el corte es una restricción de acceso: adelantarlo un día le quita un día de atención al que el paciente tiene derecho.
- `meses_restantes` cuenta meses de calendario, no días entre 30. El equipo razona en meses y las citas se programan en meses; un redondeo de 30.44 confunde más de lo que precisa.

**El dolor que cubre:** la cohorte `SEGUIMIENTO` es la razón de ser del proyecto. Hoy no existe — al cumplir 18 el paciente se esfuma de los registros. Es exactamente ahí donde el sistema aporta lo que no hay.

### 3.2 · `Paciente` — la entidad raíz

Mutable a propósito, al revés que los objetos de valor: un paciente acumula diagnósticos, contactos y consultas a lo largo de los cuatro años que dura la ventana. Lo inmutable es su `id` y su fecha de nacimiento.

**`id` NUNCA es el DNI ni el número de historia clínica.** Es un identificador interno. El sistema corre al lado del hospital y no necesita el documento nacional para nada; guardarlo solo agregaría riesgo legal sin aportar función.

Propiedades que el resto del sistema consulta:

- `diagnosticos_contables` — solo los crónicos activos. Vive aquí y no en la calculadora para que el Pasaporte y la exportación usen **el mismo criterio** y no cada uno el suyo.
- `medicamentos_por_completar` — los que no tienen dosis verificada. Se imprimen como hueco en blanco para que el médico los llene a mano.
- `dias_desde_ultima_consulta` — devuelve `None` si no hay registro. **`None` no es cero**: es ausencia de dato, y se trata distinto.
- `contacto_preferente` — a quién se le escribe. Desde los 16 se prefiere al propio paciente, porque a los 18 el vínculo con el cuidador puede haberse roto.

### 3.3 · `ClasificadorCohorte` — quién entra al sistema

Responde **dos preguntas que conviene no mezclar**:

1. ¿Es un paciente crónico, raro o complejo? → *elegibilidad*, por criterio clínico
2. ¿En qué momento de la ventana está? → *cohorte*, por edad

Alguien puede ser elegible y tener 12 años, o estar en la ventana y venir por una fractura. **El sistema solo trabaja con quien cumple las dos.**

Las fuentes de elegibilidad, ninguna inventada por nosotros:

| Fuente | Qué aporta |
|---|---|
| RM 478-2026-MINSA | 558 diagnósticos raros en CIE-10 |
| Complex Chronic Conditions v2 | 10 categorías (Feudtner, *BMC Pediatrics* 2014) |
| Códigos crónicos del INSN | Los agrega un médico en `reglas_transicion.yaml` |
| Dependencia tecnológica | Tiene dispositivos médicos |
| Polimedicación | ≥ 5 medicamentos *(provisional)* |

Se guardan **todos** los motivos, no solo el primero: "raro" y "complejo" no llevan al mismo servicio de adultos, y el equipo filtra por motivo.

**El dolor que cubre:** una lista sin motivo se deja de mirar. `ResultadoClasificacion.explicacion` es lo que el equipo lee para entender por qué alguien apareció en su bandeja.

### 3.4 · `CalculadoraIUT` — el Índice de Urgencia de Transición

El corazón del sistema. Una regresión logística **con los pesos puestos a mano por criterio clínico**, no aprendidos:

```
IUT = sigmoide(β₀ + Σ βᵢ · xᵢ)
```

Los ocho factores, todos normalizados a `[0, 1]`:

| | Factor | Cómo se calcula |
|---|---|---|
| x₁ | Urgencia temporal | `1 − meses_restantes/48`, satura el día del corte |
| x₂ | Complejidad | **categorías** CCC distintas / 5 |
| x₃ | Severidad | severidad **máxima** / 3 |
| x₄ | Dependencia tecnológica | suma de pesos de dispositivos / techo |
| x₅ | Brecha de preparación | `(5 − TRAQ)/4` |
| x₆ | Riesgo de pérdida | `días_sin_consulta / 360` |
| x₇ | Barrera de acceso | 1 si vive fuera de Lima Metropolitana |
| x₈ | Continuidad del seguro | riesgo de perder cobertura a los 18 |

**Por qué x₂ cuenta categorías y x₃ toma el máximo.** Antes x₂ contaba diagnósticos, y crecía con el número de códigos igual que x₃. El desglose los presentaba como dos razones independientes cuando eran **la misma señal contada dos veces**. Si un médico lee "complejidad" y "severidad" como dos motivos distintos y en realidad hay uno, la promesa de explicabilidad está rota. Hoy x₂ mide *extensión* (cuántos sistemas) y x₃ mide *gravedad* (cuán grave el peor). Tres códigos cardiovasculares son **un** sistema, no tres.

**Reglas duras de esta clase:**

- **No hay valor por defecto.** `CalculadoraIUT()` no existe: hay que decir con qué política clínica se construye. Un defecto silencioso produciría números con aspecto legítimo calculados con pesos que ningún médico aprobó.
- **No lee archivos.** Los `ParametrosIUT` llegan ya cargados; quien lee el YAML es un adaptador.
- **No consulta el reloj.** `hoy` siempre se pasa por parámetro. Un dominio que lee la hora no se puede probar contra casos hechos a mano en papel.

### 3.5 · `IndiceUrgencia` — por qué el número no viaja solo

**No se puede construir sin sus aportes.** Un índice sin explicación lanza `IndiceSinExplicacion` y no se crea.

```
IUT 0.870 [rojo] — Queda poco tiempo antes de cumplir 18 años (2.38),
                   Condición clínica de alta severidad (1.13),
                   Riesgo de pérdida de cobertura (0.90)
```

Los aportes vienen **ordenados de mayor a menor, y el orden es parte del contrato**: si llegan desordenados, el objeto se niega a construirse. Quien lee el desglose lee primero lo que más pesa.

**El dolor que cubre:** un médico que ve "0.87" no puede hacer nada con eso. Un médico que ve *por qué* es 0.87 sabe a quién llamar y para qué. **El desglose es el producto; el número es solo el orden.**

Dos propiedades que valen oro ante un jurado:

- **`confianza`** — qué fracción del peso del modelo se apoya en datos reales y no en supuestos. No es lo mismo decidir sobre un dato con un hueco que sobre un tercio de suposiciones. Por debajo de 0.70 la insignia pasa de "Prioridad alta" a "Prioridad alta · **datos insuficientes**".
- **`factores_imputados`** — cuáles se rellenaron. Si un supuesto empuja a alguien a rojo, quien firma tiene derecho a saberlo.

### 3.6 · `calibrar_umbral_rojo` — la idea más original del proyecto

El umbral del semáforo rojo **no es un número fijo**. Se deriva de la capacidad mensual real del equipo: es el IUT del paciente que ocupa el último lugar atendible.

**El dolor que cubre:** marcar en rojo a más pacientes de los que el equipo puede atender **no prioriza nada — solo reparte culpa**. Si el equipo atiende 20 al mes, el rojo son los 20 primeros. Ni 19 ni 60.

Si no hay capacidad configurada devuelve `math.nextafter(1.0, 2.0)`, el primer número por encima de 1.0. No devuelve 1.0 porque la comparación es `valor >= rojo` y la sigmoide llega a 1.0 exacto por redondeo — un umbral de 1.0 dejaría pasar a rojo justo a los casos más extremos.

### 3.7 · `CicloTransicion` y `MaquinaCiclo` — de "lo derivamos" a "sabemos que llegó"

Seis estados, estrictamente lineales:

```
1 Pasaporte emitido → 2 Referencia registrada → 3 Referencia aceptada
  → 4 Cita programada → 5 Cita cumplida → 6 Contrarreferencia
```

`avanzar()` rechaza saltos, retrocesos, repeticiones y fechas hacia atrás. **Un salto significa que alguien no registró un paso, y perder ese registro es perder justo el dato que el piloto viene a medir.**

**El hallazgo que cambió el diseño.** El estudio de DIRIS Lima Norte documenta **110 contrarreferencias sobre 19 951 referencias — 0.55 %**. La vía formal no funciona en la práctica. Esperar la contrarreferencia para cerrar el ciclo es esperar algo que en 99 de cada 100 casos no llega.

Por eso `CITA_CUMPLIDA` **exige declarar cómo se supo**: contrarreferencia formal o confirmación de la familia. Si no se dice, la transición se rechaza. La proporción entre ambas vías es, en sí misma, un resultado del piloto.

De ahí que existan dos propiedades distintas:

- `esta_cerrado` — llegó la contrarreferencia. La versión burocrática, que casi nunca se cumple.
- `esta_confirmado` — el paciente llegó, por la vía que sea. **La pregunta que de verdad importa.**

`MaquinaCiclo` está separada de la entidad a propósito: avanzar es un hecho que alguien registra; evaluar plazos es una lectura que se recalcula. Mezclarlas haría que consultar el estado tuviera efectos.

**Los plazos están calibrados con datos peruanos, no con intuición.** El más importante es el de 120 días entre aceptación y cita: la mediana observada es de 80–85 días, así que un umbral de 90 dispararía alerta en la mitad de los casos que van perfectamente bien. **Un sistema que avisa cuando no pasa nada deja de leerse, y uno que no se lee no sirve para nada.**

### 3.8 · `Pasaporte` — el documento que el paciente se lleva

Tres versiones escalonadas por edad: a los 14 media página, a los 16 una, a los 17 dos.

**El escalonamiento no es cosmético:** a los 14 el paciente no necesita saber cómo pedir una cita — necesita saber qué tiene y qué toma. Darle las dos páginas de la v3 a los 14 garantiza que no lea ninguna.

Reglas que atraviesan la entidad:

- **El médico siempre firma.** Un pasaporte sin firma es un borrador, y un borrador no se entrega.
- Lleva al pie el aviso normativo **textual**, que lo declara complementario y no sustituto del resumen de historia clínica normado (RM 214-2018-MINSA).
- Durante el hackathon todo documento sale con marca de agua `DATOS SINTETICOS — DEMO`. Un PDF con aspecto clínico y sin marca puede terminar en manos de quien lo tome por real.

---

## 4 · Los puertos: dónde el sistema toca el mundo

Un **puerto** es una interfaz abstracta que el dominio declara y que alguien de afuera implementa. El dominio dice *qué necesita*; no le importa *quién* lo hace.

| Puerto | Para qué |
|---|---|
| `RepositorioPacientes` / `Ciclos` / `Pasaportes` | Guardar y recuperar |
| `FuenteDatosClinicos` | De dónde salen los pacientes |
| `DirectorioDestinos` | Qué servicio de adultos **proponer** |
| `GeneradorResumen` | Redactar y extraer con modelo de lenguaje |
| `GeneradorDocumento` / `GeneradorCodigoQR` | Producir el PDF |
| `CanalNotificacion` | Correo y WhatsApp |
| `ExportadorInteroperable` | Bundle FHIR |

`test_arquitectura.py` verifica que **ningún puerto se pueda instanciar**: un puerto instanciable no es un puerto, es una clase que alguien va a usar directamente, y ahí se acaba la intercambiabilidad.

### La regla de privacidad de WhatsApp

Está en `puertos/notificacion.py` y la vigila un test bloqueante:

> **Ningún mensaje de WhatsApp puede contener diagnósticos, códigos CIE-10, nombres de medicamentos, dosis ni resultados.**

**El dolor que cubre:** un WhatsApp queda en la pantalla de bloqueo de un teléfono que puede estar en manos de cualquiera, y se reenvía sin pensarlo. El canal no es confidencial, así que el contenido tampoco puede serlo. El mensaje dice *"hay algo que atender y dónde"*; el qué se lee en el papel.

La comprobación vive **en el adaptador**, no solo en quien arma el mensaje, para que la regla se sostenga aunque un caso de uso futuro se equivoque.

---

## 5 · La capa de aplicación: `PriorizarCohorte`

Un solo caso de uso, y hace exactamente esto:

1. Pide los pacientes al repositorio *(a través del puerto — no sabe si es memoria, CSV o base de datos)*
2. Descarta a quien no es elegible
3. Si le dan la capacidad del equipo, hace **una primera pasada solo para conocer la distribución** y recalibra el umbral rojo
4. Calcula el IUT de cada uno y ordena

Devuelve `ResultadoPriorizacion`, que además de la lista trae vistas ya listas: `rojos`, `ambares`, `con_datos_insuficientes`, `sin_contacto_vigente`.

**`con_datos_insuficientes` es una lista de trabajo distinta**, y por eso va aparte: a esos pacientes no hay que atenderlos clínicamente, hay que **ir a buscar el dato que falta**.

---

## 6 · Infraestructura e interfaz

| Adaptador | Qué hace |
|---|---|
| `cargador_yaml` | Lee `config/*.yaml` y construye `ParametrosIUT` y `PoliticaPlazos` |
| `cohorte_sintetica` | Genera pacientes de prueba con `random` de la librería estándar — **sin red, sin archivos** |
| `repositorio_memoria` | Repositorio en memoria |
| `pdf_reportlab` | El Pasaporte impreso |
| `interfaz/web/app.py` | Streamlit. **Toda la lógica clínica está detrás; esto solo pinta** |

Los umbrales viven en `config/`, **no en el código**, y cada uno lleva comentada su fuente. Si un plazo es de 120 días, el comentario dice de dónde salió. Lo que aún no está confirmado lleva `TODO: confirmar con mentor` — no se inventa un valor y se disimula.

---

## 7 · La capa de digitalización *(rama `digitalizacion`)*

> Vive en una rama aparte. `main` sirve la demo desplegada y no importa nada de esto.

Lee Hojas de Referencia escaneadas con modelos de visión **locales** (Ollama), y extrae los campos a JSON.

**Por qué local y no una API:** un escaneo real trae DNI, partida de nacimiento, afiliación al SIS y el DNI del tutor. Mandarlo a un servicio externo deja de ser una decisión de arquitectura y pasa a ser un problema legal.

**Sin plantillas ni coordenadas.** En vez de preguntar *"¿qué dice el rectángulo (1300, 470, 340, 55)?"* — que depende del maquetado — se pregunta *"¿cuál es el DNI del paciente en este documento?"*. El sistema **no depende de que el hospital estandarice sus formularios**.

**La doble lectura.** Dos modelos **distintos** leen la misma imagen. Donde coinciden hay acuerdo independiente; donde discrepan, el campo va a ámbar. Es la doble digitación de los servicios de transcripción profesionales, pero gratis. Resuelve además que los modelos locales no expongan probabilidades: la señal de confianza sale del desacuerdo.

`elegir_lectores()` exige que el contraste sea de una **familia distinta** a la del principal. Dos tamaños del mismo modelo comparten arquitectura y datos de entrenamiento: se equivocan en los mismos sitios, coinciden en el error y le ponen sello verde a un campo mal leído — peor que no contrastar, porque fabrica confianza injustificada. Si solo hay una familia instalada, devuelve un lector y `None`.

### Por qué esto existe: una medición real

Sobre nuestro propio corpus, con verdad conocida, un modelo leyó:

| Campo | Verdad | Leído | |
|---|---|---|---|
| DNI | `72319111` | `7231911` | 7 dígitos → **inválido, se detecta solo** |
| N.º HC | `30389` | `30889` | **error silencioso** |

El `30889` tiene pinta perfectamente válida. Entraría al expediente sin que nadie lo note. **Ese es el fallo que esta capa existe para impedir**, y por eso el sistema no automatiza la transcripción: la verifica.

El corpus se genera sintético (`generar_corpus`) porque el hospital no puede entregarnos Hojas de Referencia llenas — son datos personales y la negativa es correcta. Generarlas nosotros sale mejor: no hay dato de nadie, se pueden versionar, y **la verdad viene gratis** porque nosotros escribimos cada campo. Eso convierte la evaluación en una función en vez de una tarde de trabajo.

> **Limitación que hay que decir en el pitch:** la letra renderizada con fuente es más regular que la humana. La exactitud medida sobre este corpus es **optimista** respecto de la letra real. Lo que el corpus sí valida honestamente es el pipeline completo y la detección de errores.

### Degradación en tres escalones

1. **Dos modelos locales** → doble lectura con señal de confianza
2. **Un modelo local** → lectura simple, sin esa señal
3. **Sin modelo (`LectorNulo`)** → captura manual asistida

**El escalón 3 sigue aportando valor real:** hoy en el INSN alguien tipea esos campos en REFCON sin ninguna validación. Con el escalón 3 los tipea con el catálogo CIE-10 corrigiéndole y la coherencia cruzada avisándole. Funciona sin GPU, sin internet y sin modelo.

---

## 8 · Los tests que bloquean

| Test | Qué garantiza |
|---|---|
| `test_arquitectura.py` | El dominio no importa nada externo |
| `test_calculadora_iut.py` | Cinco casos hechos **a mano en papel** coinciden con el código |
| `test_privacidad_whatsapp.py` | Ningún WhatsApp lleva datos clínicos |
| `test_fhir.py` | El Bundle valida contra HAPI FHIR |

El de arquitectura merece una nota: es una regla que **se rompe sola si nadie la vigila**. Basta un `import yaml` puesto con prisa a las tres de la mañana. El test convierte la afirmación del pitch en algo demostrable en treinta segundos delante de quien pregunte.

---

## 9 · Deuda técnica conocida

Se documenta en vez de disimularse. Un jurado premia más una deuda identificada y explicada que una escondida.

### 9.1 · Dos abstracciones compitiendo para el modelo de lenguaje

El dominio declara `GeneradorResumen` en `dominio/puertos/generacion.py`, y su docstring promete cuatro adaptadores: `SinLLM`, `Groq`, `Gemini` y `Ollama`.

**Ninguno existe.** `grep -rn "GeneradorResumen" src/` devuelve solo su propia definición.

En paralelo, la capa de digitalización define **otro** seam, en `infraestructura/llm/extractor.py`:

```python
class LectorDocumento(Protocol):
    def leer(self, imagen: bytes, instruccion: str) -> str: ...
```

Ese vive en infraestructura, no en el dominio. La capa externa define su propia abstracción y se la implementa a sí misma; el dominio no sabe que existe un lector de documentos.

**El problema real no es la pureza arquitectónica** — es defendible que leer documentos sea enteramente asunto de infraestructura y que al dominio solo lleguen `CampoExtraido` ya formados. **El problema es que hay dos seams para lo mismo**: uno prometido y vacío, otro improvisado y en uso. Hay que decidir cuál sobrevive.

### 9.2 · `SinLLM` no existe, y la regla dice que iba primero

`CLAUDE.md`, regla 3: *"`SinLLM` es el respaldo y se construye **antes** que cualquier proveedor de modelo."*

Se construyó `LectorOllama` primero. **El orden se invirtió.** Y duele justo donde se prometió que no dolería: sin GPU, la lectura con modelo tarda minutos por documento, y `SinLLM` — extracción por reglas y expresiones regulares — es lo que habría funcionado en cualquier máquina.

### 9.3 · El test que lo habría detectado no está escrito

`test_arquitectura.py` verifica que el dominio no importe hacia afuera y que los puertos sean abstractos. **No** verifica que cada puerto del dominio tenga al menos un adaptador, ni que la infraestructura se abstenga de declarar puertos propios. Por eso las dos deudas anteriores pasan en verde.

### 9.4 · Dependencias sin declarar

`numpy`, `PIL` y `requests` los usa el generador de corpus, pero no figuran en `pyproject.toml`. Localmente funcionan porque entraron de arrastre con `pandas`, `qrcode[pil]` y `streamlit`. **Un clon limpio se rompe.**

---

## 10 · Lo que deliberadamente NO se construye

| No se construye | Por qué |
|---|---|
| Adaptador real a SisGalenPlus | No sabemos si hay HCE, esquema ni API. Solo el stub documentado. |
| Chatbot de WhatsApp | `wa.me` abre conversaciones pero no recibe. Recibir exige la API de pago de Meta. |
| OCR de historias manuscritas | Fuera de alcance declarado. |
| **Asignación automática de hospital destino** | **Clínica y legalmente inaceptable. El sistema propone; una persona firma.** |
| Modelo de aprendizaje automático | No existen las etiquetas. El sistema las produce; el modelo viene después. |
| Envío de SMS | Cuesta por mensaje en el Perú. |
| **Cualquier escritura en el sistema del hospital** | **Rompe la promesa central: solo lectura.** |

Las dos en negrita son las que conviene tener en la punta de la lengua: son las que un jurado suele preguntar, y la respuesta *"decidimos no hacerlo, y por esto"* es más fuerte que haberlo hecho.

---

## 11 · Cómo correrlo

```bash
# la aplicación web
streamlit run src/relevo/interfaz/web/app.py

# los tests
pytest

# solo los bloqueantes
pytest -m bloqueante

# digitalización (rama digitalizacion)
python -m relevo.interfaz.cli.descargar_fuentes
python -m relevo.interfaz.cli.generar_corpus --n 200
python -m relevo.interfaz.cli.evaluar_corpus --corpus data/corpus          # lector simulado
python -m relevo.interfaz.cli.evaluar_corpus --corpus data/corpus --ollama # modelos reales
```

`evaluar_corpus` reporta tres números, y **el que importa es el segundo**:

- exactitud bruta — cuántos campos quedaron correctos
- **error NO detectado** — campos mal leídos que quedaron en verde
- carga de revisión — qué fracción tiene que mirar una persona

> Un sistema con 88 % de exactitud y 0 % de error no detectado es utilizable en un hospital. Uno con 97 % de exactitud y 3 % de error no detectado, no: significa que tres de cada cien datos entran mal al expediente sin que nadie se entere.

---

## 12 · Lo que aún no sabemos

No se inventan valores para esto. Llevan `TODO: confirmar con mentor`:

- Los pesos β de los diagnósticos — los define un médico del INSN
- La capacidad mensual del equipo — define el umbral rojo
- El directorio de destinos (CIE-10 → servicio adulto)
- Qué pasa con el SIS al cumplir 18 años
- El criterio de prevalencia vigente para enfermedad rara en el Perú
- Si la historia clínica del INSN está en HCE o sigue en PDF

Que la lista exista y esté a la vista **es parte del diseño**, no una carencia. Un sistema clínico que rellena huecos con supuestos disfrazados de datos es peligroso; uno que los marca como huecos es auditable.
