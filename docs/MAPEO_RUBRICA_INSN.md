# Mapeo contra la rúbrica del INSN

**Documento base:** *Resumen de Desafío: Puente 18+* — Unidad de Atención Integral Especializada, INSN San Borja.

Esto no es un documento más: **es la rúbrica con la que los van a evaluar.** El INSN escribió qué espera, qué no espera, y cinco *insights* de su propio trabajo de campo.

---

# PARTE 1 — Lo que valida el proyecto entero

## El Insight 5 del INSN es, palabra por palabra, nuestra tesis

> *"**Digitalizar sin rediseñar no es suficiente.** Una solución aislada puede aumentar la cantidad de registros sin mejorar la continuidad. La solución debe incorporar responsables, criterios, alertas, flujo de derivación y seguimiento del paciente."*

Llevamos toda la construcción diciendo que el valor no está en el detector sino en el traspaso y el cierre de ciclo. **El cliente lo escribió solo.** Hay que citarlo textualmente en el pitch — nada convence más a un jurado que devolverle su propia frase.

## Y su "Dato o cifra clave" justifica nuestro `SinDestinoIdentificado`

> *"**La falta de datos también es un hallazgo:** si una institución no cuenta con la información necesaria, se evidencia una brecha estructural."*

Es exactamente el argumento de contar los pacientes que salen sin destino. **No es una excusa por no resolver B1: el propio INSN lo declara hallazgo válido.**

## Las dos citas de pacientes que nos faltaban

El INSN las incluye, así que son citables sin haber entrevistado a nadie:

> *"Me dijeron que ya no podía atenderme en pediatría, pero no sabía a dónde ir ni qué documentos llevar."*

> *"Cuando fui al médico del servicio para adultos, no sabía cómo responder a sus preguntas porque mi mamá siempre lo hacía por mí."*

**La primera abre el pitch.** Dice B1 y B2 en una línea, con voz de paciente.
**La segunda justifica el Pasaporte escalonado** mejor que cualquier argumento nuestro.

Esto cierra en parte el vacío que veníamos arrastrando —no hablamos con pacientes— sin fingir que sí lo hicimos. La atribución correcta: *"según el trabajo de campo del propio INSN"*.

---

# PARTE 2 — Los siete entregables que piden, uno por uno

## 1 · Ruta de transición definida — 🟠 **el hueco más importante**

> *"Un modelo que establezca **roles, etapas, responsables, hitos** y criterios mínimos."*

| Piden | Tenemos |
|---|---|
| Etapas | ✅ `EstadoCiclo`, seis estados |
| Hitos | ✅ Pasaporte a los 14, 16, 17 |
| Criterios mínimos | ✅ IUT + clasificador de cohorte |
| **Roles** | ❌ |
| **Responsables** | ❌ |

**Nadie es dueño de nada en nuestro modelo.** Un paciente en rojo no tiene a quién le toque. Y el INSN lo pide dos veces: en el entregable y en el Insight 5.

**Cierre mínimo:** un objeto de valor `Responsable` (nombre, rol, servicio) en la transición, y que cada aviso diga a quién le toca. Es media hora de trabajo y cierra un ítem entero de la rúbrica.

## 2 · Prototipo funcional o mockup navegable — ✅ **fuerte**

> *"Identificar pacientes candidatos, visualizar su estado dentro de la transición y activar alertas ante retrasos o tareas pendientes."*

Las tres cosas están: Radar, estados del ciclo, y `correr_noche` disparando alertas por plazo vencido. **Y no es un mockup: funciona.** Es el ítem donde estamos más fuertes y donde muchos equipos van a llevar solo pantallas dibujadas.

## 3 · Checklist de preparación — 🟠 **hay que alinearlo a sus seis ítems**

Piden evaluar si el adolescente y su familia conocen: **diagnóstico · tratamiento · medicamentos · señales de alerta · documentos · servicio de destino.**

Tenemos `ResultadoTRAQ` modelado, pero **TRAQ no pregunta exactamente eso.** El INSN nombró seis ítems concretos.

**Cierre:** un checklist de seis preguntas con esos nombres literales, que alimente el mismo factor `x5` del índice. Que se vea en pantalla con las seis casillas. Barato y encaja con lo que ya existe.

## 4 · Resumen clínico de transición — ✅ **es el Pasaporte**

> *"Diagnósticos, tratamientos, cirugías, dispositivos, alergias, riesgos, necesidades psicosociales y recomendaciones de continuidad."*

Nuestro Pasaporte cubre casi todo. **Falta: necesidades psicosociales.** La historia clínica del INSN sí trae datos socioeconómicos —vivienda, servicios, hacinamiento— así que hay de dónde sacarlos. Agregar la sección.

## 5 · Tablero de seguimiento — 🟠 **faltan dos estados y son importantes**

Sus estados: **pendiente · en preparación · referido · cita otorgada · primera atención realizada · pérdida de seguimiento · reingreso.**

| INSN | Nosotros |
|---|---|
| pendiente / en preparación | `PASAPORTE_EMITIDO` |
| referido | `REFERENCIA_REGISTRADA` / `REFERENCIA_ACEPTADA` |
| cita otorgada | `CITA_PROGRAMADA` |
| primera atención realizada | `CITA_CUMPLIDA` |
| **pérdida de seguimiento** | ❌ **no existe** |
| **reingreso** | ❌ **no existe** |

**`PERDIDA_DE_SEGUIMIENTO` es el estado que da sentido a todo el proyecto** y no lo tenemos como estado. Es el desenlace que queremos evitar; tiene que ser nombrable.

**`REINGRESO` es más sutil y muy valioso:** el paciente que vuelve después de haberse perdido. Que el modelo lo contemple demuestra que entendemos el proceso real y no una línea recta.

**Cierre:** dos valores más en el enum y sus transiciones. Es de lo más barato de la lista y de lo que más se nota.

## 6 · Contenido educativo accesible — 🟠 **parcial**

> *"Material claro y comprensible que ayude a adolescentes y cuidadores a conocer el proceso y asumir progresivamente nuevas responsabilidades."*

Las versiones v1 y v2 del Pasaporte apuntan ahí, pero son un resumen clínico simplificado, **no material educativo sobre el proceso**. Falta el "qué te va a pasar y qué tienes que aprender a hacer".

**Cierre barato:** una cara adicional en la v1 y la v2 — *"Lo que vas a aprender a hacer este año"* — con tres o cuatro puntos por edad. Sale del mismo generador.

## 7 · Transferencia cálida — ❌ **no lo tenemos, y es un término suyo**

> *"Un flujo de comunicación entre el equipo pediátrico y el servicio receptor, **al menos para uno o dos servicios que funcionen como piloto**."*

Aparece dos veces en el documento y es vocabulario del cliente: **"transferencia cálida"** o *warm handoff*. Hay que adoptar la palabra.

Nuestro modelo pasa de `REFERENCIA_REGISTRADA` a `REFERENCIA_ACEPTADA` sin que exista contacto humano entre equipos. Eso es transferencia **fría**, que es justo lo que dicen que falla.

**Cierre mínimo, y es más de diseño que de código:** un estado o campo `CONTACTO_ENTRE_EQUIPOS` con fecha, quién habló con quién y por qué medio. Aunque sea una llamada registrada a mano. **Lo que importa es que el modelo la exija antes de dar por buena la transferencia.**

Y nombrar el piloto: *"proponemos empezar con dos servicios — por ejemplo Neumología y Nefrología"*. Ellos mismos acotan a uno o dos.

---

# PARTE 3 — Lo que NO entra en el alcance

## Cuatro que cumplimos, y uno que hay que blindar

| Fuera de alcance | Nosotros |
|---|---|
| Historia clínica electrónica completa | ✅ No la hicimos. Solo lectura, nunca escribimos en su sistema. |
| Solución a la falta estructural de citas | ✅ No la tocamos. |
| Modificación de normas o convenios | ✅ Al contrario: **nos apoyamos en las que ya existen** (NT 018, RM 214-2018, RM 478-2026). |
| **Uso de información clínica identificable** | ✅✅ **Datos 100 % sintéticos.** Lo cumplimos de forma verificable. |

## ⚠️ Y el que hay que blindar antes del pitch

> *"**Inteligencia artificial sin supervisión clínica:** No se espera una herramienta que diagnostique, **priorice pacientes de manera autónoma** o reemplace la decisión médica."*

**Nuestro sistema calcula un índice y ordena una lista.** Leído rápido, eso es "priorizar pacientes". Hay que blindarlo, y tenemos con qué:

1. **El sistema ordena una lista; no decide nada.** Quien decide a quién se atiende es el equipo clínico, mirando la lista.
2. **Los pesos los define un médico, no un algoritmo.** Están en un archivo de configuración que el hospital firma y versiona. Sin ese archivo el sistema no arranca — es imposible que calcule con valores que nadie aprobó.
3. **Cada puntaje muestra de dónde sale**, factor por factor. Un médico puede discutirlo y corregirlo. **Eso es supervisión clínica, no un número opaco.**
4. **El Pasaporte no se emite sin firma médica.** Nunca.
5. **No diagnosticamos.** Los diagnósticos vienen codificados en CIE-10 desde la historia clínica; el sistema no propone ninguno.

**La frase para el pitch, y conviene decirla sin que la pregunten:**

> *"Su documento dice que no esperan una IA que priorice de manera autónoma, y estamos de acuerdo. Nuestro sistema **no prioriza: ordena y explica**. Los pesos los pone un médico del INSN en un archivo que el hospital versiona, cada puntaje muestra sus factores, y nada clínico sale sin firma. La decisión siempre es de una persona."*

Dicho así, un supuesto riesgo se convierte en una demostración de que leímos el alcance.

---

# PARTE 4 — Detalles que hay que corregir

## La ventana de edad: ellos dicen 15 a 21

En "Dato o cifra clave" piden línea basal de *"pacientes de 15 a 21 años"*. Nuestra cohorte activa es 14–18 más seguimiento posterior.

**No es un conflicto: es el mismo rango dicho distinto.** Nosotros arrancamos antes (14, siguiendo Got Transition) y seguimos después del corte. Vale la pena decirlo así:

> *"Ustedes plantean 15 a 21. Nosotros abrimos a los 14 porque los programas internacionales recomiendan empezar cuatro años antes del corte, y seguimos al paciente después de los 18 hasta confirmar que llegó. Nuestra ventana contiene la suya."*

## El desafío es más amplio de lo que veníamos leyendo

Su enunciado incluye *"superando la fragmentación **clínica, administrativa y comunicacional**"*. Tres fragmentaciones, no una. Conviene mapear los entregables a las tres en el pitch: el Pasaporte ataca la clínica, la digitalización y REFCON la administrativa, la capa de avisos la comunicacional.

## Y nombran cinco grupos afectados

Adolescentes · familias · equipos pediátricos · servicios de adultos · áreas asistenciales y administrativas.

**El quinto es el que solemos olvidar** y es el que más se beneficia de la digitalización: admisión, citas, referencias, trabajo social, farmacia, laboratorio. Mencionarlos explícitamente demuestra que leímos el documento.

---

# PARTE 5 — Qué hacer antes del pitch

Ordenado por relación esfuerzo/rúbrica.

| # | Qué | Cierra | Esfuerzo |
|---|---|---|---|
| 1 | **Agregar `PERDIDA_DE_SEGUIMIENTO` y `REINGRESO`** al enum de estados | Entregable 5 | 20 min |
| 2 | **`Responsable`** en la transición, y que cada aviso diga a quién le toca | Entregable 1 + Insight 5 | 30 min |
| 3 | **Checklist de seis ítems** con los nombres literales del INSN | Entregable 3 | 45 min |
| 4 | **Registro de transferencia cálida** — fecha, quién, con quién, medio | Entregable 7 | 30 min |
| 5 | **Sección psicosocial** en el Pasaporte | Entregable 4 | 20 min |
| 6 | **Cara educativa** en las versiones v1 y v2 | Entregable 6 | 30 min |
| 7 | Blindar el discurso del IUT contra "priorización autónoma" | Fuera de alcance | 0 — es guion |

**Con las siete, se cubre la rúbrica completa.** Las cuatro primeras son las que más se notan.

## Y una lámina que vale la pena armar

Una tabla de dos columnas: **lo que el INSN pidió** ← → **lo que entregamos**, con los siete ítems marcados.

Mostrarle a un jurado que leíste su documento y lo cumpliste punto por punto es más persuasivo que cualquier demostración técnica. Es la lámina que dice *"los escuchamos"*.

---

# PARTE 6 — El pitch, reajustado

## Abre con su cita, no con la nuestra

**Antes:** *"Ana, 17 años, fibrosis quística…"* — un caso inventado.

**Ahora:**

> *"Me dijeron que ya no podía atenderme en pediatría, pero no sabía a dónde ir ni qué documentos llevar."*
>
> *"Eso no lo escribimos nosotros. Está en el documento que el INSN nos entregó, y es la voz de un paciente de esta casa."*

Empezar con la voz del paciente que ellos mismos recogieron es más fuerte que cualquier estadística. Y demuestra en la primera frase que leímos su trabajo.

## Cierra con la segunda cita

> *"Cuando fui al médico del servicio para adultos, no sabía cómo responder a sus preguntas porque mi mamá siempre lo hacía por mí."*
>
> *"Por eso el Pasaporte empieza a los 14 y no a los 18. A los 18 ya es tarde para aprender."*

## Y una frase que devuelve su propio insight

> *"Su documento dice que digitalizar sin rediseñar no es suficiente. Estamos de acuerdo, y por eso no construimos un detector de cumpleaños: construimos la ruta —con responsables, criterios, alertas y seguimiento— que su Insight 5 pide."*

---

## Una nota de método

Este documento cambia el orden de prioridades que veníamos siguiendo. **FHIR baja de nivel:** no aparece en ninguno de los siete entregables. Sigue siendo un buen diferenciador técnico y una lámina de "hacia dónde va esto", pero **si hay que elegir entre FHIR y los cuatro cierres de la Parte 5, se eligen los cierres.** La rúbrica es la rúbrica.
