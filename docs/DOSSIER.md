

# RELEVO
## Dossier del proyecto — Reto 1, Hackathon INSN

**Reto:** *"Puente 18+: rediseñando la transición en salud del paciente pediátrico a adulto"*
**Equipo Avellana** · Nombre de propuesta (provisional): **Relevo**
**Versión 3** · 14 de agosto de 2026

---

## Cómo usar este documento

Está escrito para que **cualquier persona que conozca el contexto del hackathon pueda entenderlo completo, sin haber estado en ninguna de nuestras conversaciones.** No asume conocimientos de informática médica ni de normativa peruana: todo lo que hace falta está explicado aquí adentro.

**Orden sugerido de lectura:**

- Si tienes 5 minutos → **Partes 1 y 2**.
- Si vas a discutir la propuesta → agrega la **Parte 3**.
- Si vas a programar → **Partes 4 y 5**.
- Si vas a presentar → **Parte 6**.
- Si te topas con una sigla → **Anexo A (glosario)**.

**Qué cambió respecto de la versión 2:**

1. **Se rediseñó cómo llega la información a las personas.** Antes el sistema era "una página web que el equipo revisa". Ahora es "avisos que llegan solos". Cambio de fondo, explicado en la Parte 3.
2. **Se agregó la capa de avisos** con su matriz de canales, incluyendo WhatsApp a la familia, y con las reglas de privacidad que la acompañan.
3. **Se descartó el pop-up del sistema operativo** como canal, con la razón.
4. Se explicó con más cuidado **qué es el Pasaporte** (respuesta corta: una hoja de papel).

---

# PARTE 1 — El problema

## 1.1 Qué pide el reto

> *¿Cómo podríamos mejorar el proceso de transición de pacientes con enfermedades crónicas, raras o complejas desde la atención pediátrica hacia los servicios de adultos, para que reciban una atención continua y segura, logrando disminuir el riesgo de interrupciones en su seguimiento y tratamiento, así como las brechas de información en pacientes, familias y equipos de salud?*

Fíjate en las dos cosas que el enunciado pide explícitamente: **que no se interrumpa el seguimiento** y **que no se pierda la información**. Nuestra propuesta ataca esas dos, en ese orden de importancia.

## 1.2 La trampa en la que no hay que caer

La idea que a todo el mundo se le ocurre primero es:

> *"Una IA que detecte a los pacientes que van a cumplir 18 años y agende su transición."*

Hay que descartarla, porque cualquier jurado la desarma en treinta segundos:

> **Detectar quién va a cumplir 18 años no es un problema de inteligencia artificial. Es una resta de fechas.**

La fecha de nacimiento ya está escrita en la historia clínica. El hospital **ya sabe** quién cumple 18. Y el paciente igual se pierde.

Entonces la pregunta correcta no es *¿cómo detectamos?* sino:

> **¿Por qué, sabiendo perfectamente que el paciente cumple 18, el sistema igual lo suelta?**

## 1.3 Los cuatro cuellos de botella reales

| # | Cuello de botella | Qué falta hoy |
|---|---|---|
| **B1** | **No hay destino** | Nadie sabe a qué hospital o servicio de adultos mandarlo. Para enfermedades raras, el servicio adulto equivalente puede sencillamente no existir en el país. |
| **B2** | **La información no viaja** | La historia clínica del INSN son doce páginas, mucho de ello texto libre escrito a mano o tipeado. Lo que cruza al hospital de adultos es una hoja de referencia de una carilla. Quince años de historia se comprimen en un párrafo. |
| **B3** | **El paciente no está preparado** | A los 17, la madre sabe todo y el paciente nada: no conoce el nombre de su diagnóstico, no sabe sus dosis, nunca pidió una cita solo. |
| **B4** | **Nadie cierra el ciclo** | Existe una norma que obliga a confirmar qué pasó con el paciente derivado. En la práctica se emite la derivación y se asume que funcionó. Nadie verifica que llegó. |

**Nuestro reencuadre:** el valor no está en el detector. Está en **el documento de traspaso (B2)** y en **la confirmación de llegada (B4)**. La detección es solo el disparador, y debe ser lo más barata y auditable posible.

Frase para el pitch:

> *"No estamos construyendo un detector de cumpleaños. Estamos construyendo el puente que hoy no existe: el paquete de información que cruza con el paciente, y la confirmación de que llegó al otro lado."*

## 1.4 Por qué nadie ve el problema

Estimemos cuántos pacientes hacen esta transición cada año. El único dato público duro que tenemos: **3 727 niños con enfermedades raras atendidos en el INSN San Borja en 2023**.

Si la población atendida cubre edades de 0 a 17 años — o sea 18 cohortes anuales — y suponemos que están repartidos de forma más o menos pareja entre esas edades, entonces cada año le toca cumplir 18 a aproximadamente una de esas dieciocho partes:

$$N_{\text{transición}} \approx \frac{N_{\text{cohorte}}}{\text{span}} = \frac{3\,727}{18} \approx 207 \ \text{pacientes por año}$$

Repartido sobre unos 250 días hábiles:

$$\frac{207}{250} \approx 0.8 \ \text{pacientes por día hábil}$$

**Los supuestos, que hay que declarar siempre que se use este número:**

- "Atendidos" cuenta atenciones, no personas únicas; una misma persona puede aparecer varias veces al año.
- La distribución por edad **no** es realmente pareja: las poblaciones pediátricas con enfermedades raras se concentran en edades bajas, tanto por el momento en que se hace el diagnóstico como, tristemente, por mortalidad. Esto hace que el cálculo **sobreestime**.
- Solo cuenta enfermedades raras, y el reto incluye también crónicas y complejas. Esto hace que **subestime** el alcance total.

Los dos últimos sesgos empujan en direcciones opuestas y se cancelan en parte. **Conclusión defendible: del orden de 10² pacientes al año, aproximadamente uno por día hábil.** No afirmar más precisión que esa; hay que pedirle el número real al mentor.

Ese número hace dos trabajos para nosotros:

**Primero, mata la objeción de costo.** Un paciente al día por diez minutos de revisión médica son diez minutos diarios. No es un puesto de trabajo nuevo, es un café.

**Segundo, y más importante, explica por qué el problema es invisible:**

> *"El problema no se ve porque pasa de a uno. Se pierde un paciente por día. Nadie lo nota. A fin de año son doscientas personas sin continuidad de atención."*

## 1.5 Qué dice la evidencia internacional

- Los programas de transición **estructurados** reducen las interrupciones de atención de **36.2 % a 12.7 %** frente a la atención habitual (revisión en cardiopatías congénitas). Sin programa, casi 1 de cada 3 pacientes queda descolgado; con programa, 1 de cada 8.
- En Inglaterra, con servicios organizados, la pérdida de seguimiento baja a **1.3 %** en los casos severos y **6.0 %** en los moderados. Se puede llegar ahí: es cuestión de proceso, no de tecnología cara.
- Solo el **41 %** de 96 centros europeos ofrecía programas de transición estructurados. **Esto no es un problema resuelto en el primer mundo.** No estamos copiando algo viejo; estamos implementando algo que sigue siendo frontera.
- Consecuencia clínica documentada: el paciente perdido **reaparece en Emergencia** con deterioro severo, a veces irreversible, y pierde procedimientos que tenía programados.

---

# PARTE 2 — La solución, sin jerga

## 2.1 El MVP en tres frases

1. **Un programa que corre solo, de madrugada, una vez al día.** Lee una copia de la lista de pacientes, calcula quién está en riesgo de perderse en la transición, y prepara lo que haga falta. No le pide nada a nadie.
2. **Un aviso que llega solo** cuando hay algo que hacer: un correo al jefe de servicio, un mensaje de WhatsApp a la familia. **Nadie tiene que acordarse de revisar nada.**
3. **Una hoja de papel** — un PDF de una o dos páginas — que se imprime y se le entrega al paciente el día que deja el hospital de niños.

Eso es todo. Si alguien te pregunta qué hace Relevo, eso es la respuesta.

## 2.2 Qué es el "Pasaporte" (la parte que más confunde)

**El Pasaporte es una hoja de papel.** Un PDF de una o dos páginas que se imprime y se le da al paciente. Como una receta o un certificado de alta.

Contiene: sus diagnósticos, sus cirugías, su medicación actual con dosis, sus alergias, sus dispositivos, quiénes lo trataban, qué hay que vigilar y a quién llamar.

No es un programa. No es una aplicación. No es una API. **Es papel.** Que además exista una versión digital de ese mismo contenido, en un formato que una máquina pueda leer, es útil para el futuro — pero el objeto es la hoja.

**De dónde viene la palabra "pasaporte":** no la inventamos nosotros. Es el término establecido en la literatura de transición. El *MyHealth Passport* del programa Good2Go del Hospital for Sick Children de Toronto hace exactamente esto, y tiene literatura publicada sobre su uso. La metáfora es exacta: un pasaporte es un documento que llevas encima, que dice quién eres, y que presentas en un cruce de frontera para que te admitan. Pasar de pediatría a adultos *es* un cruce de frontera.

## 2.3 El principio de diseño más importante

Este proyecto puede fracasar de una forma muy específica y muy común:

> Le agregas una pantalla más a gente que ya tiene cinco abiertas. Nadie la abre. A los tres meses el proyecto está muerto.

Así es como muere el software hospitalario. Entonces nuestra regla es:

> ### **El sistema busca a la persona. La persona no busca al sistema.**

En jerga técnica esto se llama **push** (empujar) en vez de **pull** (jalar). Nadie tiene que acordarse de entrar a ningún lado. La información llega.

Consecuencia práctica: **no hay ninguna pantalla que alguien esté obligado a revisar todos los días.** La pantalla existe, pero solo se abre cuando un aviso te dijo que la abras — igual que el portal de tu banco, que no abres a diario sino cuando te llegó un mensaje.

## 2.4 Un martes cualquiera

Así se ve el sistema funcionando, en concreto:

**2:00 a.m.** — El programa se despierta solo. Lee la copia de datos. Calcula. Detecta que Ana Quispe cumple 18 en siete meses, tiene cuatro diagnósticos crónicos activos y no tiene ningún plan de transición registrado. La marca en rojo. Con la información de su historia arma un borrador de su Pasaporte. Se vuelve a dormir.

**7:00 a.m.** — Al jefe de Neumología le llega un correo de cuatro líneas: *"1 paciente nuevo en prioridad alta esta semana: Ana Quispe M., 17a 5m. [ver detalle]"*. No abrió nada. Llegó solo.

**10:30 a.m.** — En su consulta con Ana, el médico hace clic en el enlace del correo. Ve el borrador del Pasaporte ya armado con lo que el sistema sacó de la historia clínica. Corrige dos cosas, agrega una. Firma. Imprime.

**10:45 a.m.** — Ana sale con una hoja en la mano que dice qué tiene, qué toma, a qué es alérgica y a quién llamar. **Nunca en quince años tuvo eso.**

**Ese mismo día** — A la mamá de Ana le llega un WhatsApp: el recordatorio de que en unos meses viene el cambio de hospital, y un enlace a una explicación en lenguaje sencillo.

**Tres meses después** — Nadie confirmó que Ana llegó a su primera cita en el hospital de adultos. El programa lo nota solo y manda otro correo. Alguien llama a la casa.

**El médico nunca aprendió un sistema nuevo.** Recibió un correo y firmó un papel.

## 2.5 Qué hace y qué no hace

| El sistema **sí** hace | El sistema **no** hace |
|---|---|
| Lee una copia de datos, en formato estándar | No escribe nada en el sistema del hospital |
| Prioriza pacientes y **explica por qué** prioriza | No decide nada solo: el médico revisa y firma |
| Genera el borrador del documento de traspaso | No emite documentos sin revisión humana |
| Avisa por correo y WhatsApp | No obliga a nadie a revisar una pantalla nueva |
| Cuenta los días y alerta si nadie confirmó la llegada | No reemplaza al coordinador humano: lo hace escalable |
| | **No asigna el hospital destino** — ese es un problema abierto, ver §5.4 |

---

# PARTE 3 — Cómo llega la información a las personas

Esta parte es nueva en la versión 3 y es probablemente el aporte de diseño más importante del proyecto.

## 3.1 El descarte del pop-up

Consideramos y descartamos dos variantes de "notificación emergente":

**Pop-up dentro del sistema hospitalario** (que salte cuando el médico abre la historia de ese paciente). Sería lo ideal desde el punto de vista del flujo de trabajo, pero exigiría **modificar SisGalenPlus**, el sistema del hospital. Eso rompe nuestra promesa central de no invadir su software, requiere permisos y desarrollo del proveedor, y no es viable en un hackathon ni probablemente en un piloto.

**Notificación del sistema operativo** (un aviso de Windows en el escritorio). Descartado por una razón práctica: **depende de cómo cada usuario tenga configuradas sus notificaciones**, requiere instalar algo en cada máquina, y en equipos hospitalarios compartidos el aviso le puede llegar a quien no corresponde. Frágil y con riesgo de confidencialidad.

**Lo que queda, y que además funciona mejor:** correo electrónico institucional, papel impreso, y WhatsApp a la familia. Los tres son costo cero, no requieren instalar nada y no tocan el sistema del hospital.

## 3.2 Matriz de avisos

Esta tabla es el diseño completo de la capa de avisos. Cada fila responde: quién recibe, qué, cuándo y por dónde.

| Destinatario | Qué recibe | Cuándo | Canal | Contiene datos clínicos |
|---|---|---|---|---|
| **Jefe de servicio / médico tratante** | Lista de pacientes nuevos en prioridad alta | Lunes 7:00 a.m., semanal | Correo institucional | Sí (canal interno seguro) |
| **Médico tratante** | Aviso de que hay un borrador de Pasaporte listo para revisar y firmar | Al generarse | Correo institucional | Sí |
| **Coordinación / Servicio Social** | Alerta de caso sin confirmación de llegada a los 90 días | Al cumplirse el plazo | Correo institucional | Sí |
| **Jefatura** | Reporte mensual: cuántos transitaron, cuántos llegaron, cuántos se perdieron | Mensual | Correo + PDF | Agregado, sin nombres |
| **Servicio (sin correo)** | La misma lista, impresa | Semanal | Papel, con el reporte del servicio | Sí |
| **Familia / paciente** | Recordatorio del cambio de hospital, fecha de cita, "por favor comuníquese" | Escalonado por edad y por hitos | **WhatsApp** | **No — nunca** |

## 3.3 El canal de WhatsApp, modelado en detalle

WhatsApp es el canal correcto para la familia: es el que efectivamente revisan, no requiere que instalen nada nuevo y funciona en teléfonos modestos y con poca conexión. Pero hay que diseñarlo con cuidado en dos dimensiones.

### Cómo enviarlo sin costo

Existen dos caminos y solo uno es viable para nosotros:

**El camino caro (descartado):** la *WhatsApp Business Platform* de Meta permite envío automático masivo, pero requiere verificación de empresa, aprobación de plantillas de mensaje y **cobra por conversación** en la mayoría de países. Para un hospital público significa proceso de adquisición. Descartado por costo y por fricción administrativa.

**El camino de costo cero (elegido): enlaces `wa.me` con envío por un clic.**

El sistema no envía el WhatsApp: **genera el mensaje ya redactado y un enlace listo para enviar.** La persona a cargo hace clic y el mensaje se abre en su propio WhatsApp, ya escrito, con el destinatario cargado. Ella solo aprieta enviar.

```
https://wa.me/51987654321?text=Hola%2C%20le%20escribimos%20del%20INSN...
```

Tres ventajas, y conviene decirlas todas en el pitch:

1. **Cuesta cero.** No hay API, no hay aprobación de Meta, no hay contrato.
2. **Mantiene un humano en el circuito.** Una persona decide qué se envía y a quién. Nada sale automáticamente hacia un paciente.
3. **No requiere ningún permiso institucional especial**, porque técnicamente el mensaje lo envía una persona desde su propio teléfono o WhatsApp Web, igual que ya lo hace hoy.

A un volumen de aproximadamente un paciente por día hábil, esto es perfectamente manejable: el sistema arma una pequeña cola de mensajes pendientes y alguien los despacha en dos minutos.

Como respaldo para familias sin WhatsApp: **SMS** (que puede enviarse por el mismo mecanismo) o llamada telefónica, que es lo que ya se hace hoy.

### Qué se puede y qué no se puede escribir

Esta es una regla dura del diseño y hay que defenderla:

> **Por WhatsApp nunca viaja información clínica.** Ni diagnósticos, ni medicamentos, ni resultados.

WhatsApp no es un canal apto para información de salud: el teléfono puede ser compartido, el mensaje puede quedar visible en la pantalla de bloqueo, y no hay control institucional sobre el dispositivo. Además, muchos de estos pacientes tienen enfermedades cuyo solo nombre es información sensible.

Lo que sí puede viajar: **avisos de proceso.**

| Permitido | Prohibido |
|---|---|
| *"Le escribimos del INSN San Borja. Su hijo(a) se acerca a la edad de transferencia a un hospital de adultos. Le contamos cómo será el proceso: [enlace]"* | Cualquier mención del diagnóstico |
| *"Recordatorio: cita el 02/04 a las 9:00 en [establecimiento]"* | Nombre de medicamentos o dosis |
| *"No hemos podido confirmar si asistió a su cita. Por favor comuníquese al 2300600 anexo 1118."* | Resultados de exámenes |
| Enlace a material educativo general | Adjuntar el Pasaporte |

**El Pasaporte no se manda por WhatsApp. Se entrega impreso, en mano.**

Que hayamos pensado esto y lo digamos antes de que nos pregunten es, por sí solo, un punto a favor ante un jurado clínico.

## 3.4 El correo, modelado en detalle

**Costo cero:** se envía por el servidor de correo institucional que el hospital ya tiene (SMTP). Para la demo del hackathon basta una cuenta de correo cualquiera o un servidor de prueba local.

**Regla de diseño: el correo debe poder leerse sin abrir nada.** Si el jefe de servicio tiene que hacer clic para enterarse de si hay algo importante, dejará de abrirlo en dos semanas. Entonces el asunto ya trae el número:

> **Asunto:** Relevo · 3 pacientes en prioridad alta esta semana
>
> Buenos días.
>
> Tres pacientes entraron esta semana en ventana de transición prioritaria:
>
> · Ana Q. M. — 17a 5m — cumple 18 en 7 meses — sin plan de transición
> · Juan R. T. — 17a 9m — cumple 18 en 3 meses — Pasaporte pendiente de firma
> · María H. C. — 17a 1m — cumple 18 en 11 meses — sin plan de transición
>
> Ver detalle y firmar Pasaportes: [enlace]
>
> Este correo se genera automáticamente. Si no corresponde recibirlo, responda a este mensaje.

Si esa semana no hay nada, **no se manda correo**. Un aviso que llega siempre deja de leerse.

## 3.5 Dónde queda entonces la pantalla web

Sigue existiendo, pero cambió de rol. **Ya no es donde el equipo vive, es donde entra cuando un aviso lo mandó.** Sirve para tres cosas:

1. Ver el detalle de un paciente y **por qué** el sistema lo priorizó
2. Revisar, corregir y firmar el borrador del Pasaporte
3. Consultar el tablero de indicadores cuando alguien lo quiera ver

Nota importante para el equipo: **esta pantalla no se construye para el jurado.** Se construye para la enfermera o el médico que la va a abrir un martes por la mañana. Si la construimos para impresionar, va a tener animaciones bonitas y ningún flujo de trabajo real, y en la ronda de preguntas alguien va a decir *"¿y esto quién lo usa?"*. Si la construimos para quien la va a usar, el jurado también lo va a notar.

> **No hay pantallas de demo. Hay pantallas de trabajo que además se demuestran.**

---

# PARTE 4 — Cómo funciona por dentro

## 4.1 La arquitectura

```
   [ SisGalenPlus / historia clínica en PDF ]     ← sistema del hospital. NO SE TOCA.
                     │
                     │  (solo lectura, copia de datos)
                     ▼
   ┌──────────────────────────────────────┐
   │  ADAPTADOR                           │   ← única pieza que cambia
   │  hackathon: archivo CSV sintético    │      según de dónde vengan los datos
   │  producción: consulta a SisGalenPlus │      (~5 % del código)
   └──────────────────┬───────────────────┘
                      ▼
   ┌────────────────────────────────────────────────────┐
   │  NÚCLEO — esto es lo que construimos               │
   │  · Modelo de datos en formato estándar (FHIR)      │
   │  · Motor de reglas (archivo YAML)                  │
   │  · Índice de Urgencia de Transición (IUT)          │
   │  · Resumen automático del texto libre (NLP)        │
   │  · Contador de 90 días                             │
   └──────────────────┬─────────────────────────────────┘
                      ▼
   ┌──────────────────────────────────────────────────┐
   │  CAPA DE AVISOS  ← el sistema busca a la persona │
   │  correo · papel impreso · WhatsApp (1 clic)      │
   └──────────────────┬───────────────────────────────┘
                      ▼
   ┌──────────────┬──────────────┬──────────────┬──────────────┐
   │  Pasaporte   │  Pantalla    │  Checklist   │  Indicadores │
   │  PDF + QR    │  de detalle  │  del paciente│  de cierre   │
   └──────────────┴──────────────┴──────────────┴──────────────┘
```

**Lo más importante de este dibujo:** la caja de arriba tiene una flecha que sale, ninguna que entra. **No escribimos nada en el sistema del hospital.** Solo leemos una copia.

Para un área de informática hospitalaria, esa diferencia es la que separa "lo evaluamos" de "ni lo miro".

## 4.2 Los cuatro formatos y para qué sirve cada uno

Esta tabla resuelve una confusión que ya nos costó una observación del mentor. Cada formato hace un trabajo y **ninguno hace el del otro**.

| Capa | Formato | Qué contiene | Quién lo consume |
|---|---|---|---|
| **Configuración** | **YAML** | Las reglas y los pesos clínicos. **Cero datos de paciente.** | El equipo clínico que edita la política |
| **Intercambio** | **JSON (formato FHIR)** | Datos clínicos entre sistemas. Es el estándar que MINSA ya definió. | Máquinas: REFCON, RENHICE, otro hospital |
| **Documento** | **PDF firmado** | El Pasaporte que la familia lleva encima | Paciente, familia, médico receptor |
| **Vista** | **HTML** | La pantalla de trabajo | Personal del INSN |

**Aclaración explícita, porque se prestó a confusión:** nunca se propuso guardar historias clínicas en YAML. YAML es solo el archivo de configuración de reglas. Los datos clínicos van en JSON con formato FHIR — que es, precisamente, el estándar nacional peruano publicado por el MINSA.

## 4.3 El Pasaporte no es un "resumen de historia clínica"

Restricción normativa que hay que respetar y decir en voz alta:

El *resumen de historia clínica* es un **documento regulado** por la Norma Técnica de Salud para la Gestión de la Historia Clínica (RM 214-2018-MINSA, modificada por RM 265-2018-MINSA). Tiene formato definido, lo emite y firma un médico, y hay reglas sobre quién puede solicitarlo.

**El Pasaporte 18+ es un instrumento complementario de traspaso.** No reemplaza ni la historia clínica ni el resumen normado. Eso va impreso **en el propio documento**, al pie:

> *"Documento informativo complementario para la transición asistencial. No reemplaza la historia clínica ni el resumen de historia clínica normado (RM 214-2018-MINSA). Elaborado con apoyo automatizado, revisado y firmado por el médico tratante."*

Poner ese texto no debilita la propuesta: **demuestra que leímos la norma.** Es de las cosas que más credibilidad dan ante un jurado clínico.

## 4.4 El Índice de Urgencia de Transición (IUT)

Nos van a pedir "el algoritmo". Conviene tenerlo escrito de forma cerrada.

### Qué es, en una frase

Un número entre 0 y 1 que dice qué tan urgente es empezar a trabajar la transición de un paciente. Se calcula sumando factores con pesos, y **cada factor se muestra por separado en pantalla**, de modo que el médico pueda ver de dónde salió el número.

### Los factores

Para un paciente $p$ evaluado en el momento $t$, se calcula un conjunto de características, todas normalizadas al rango $[0,1]$.

**Urgencia temporal.** Con $t_r$ = meses que faltan para los 18 años y $W = 48$ meses de ventana de transición (empezando a los 14, como recomienda Got Transition):

$$x_1 = \mathrm{clamp}\!\left(1 - \frac{t_r}{W},\; 0,\; 1\right)$$

Vale 0 a los 14 años y crece linealmente hasta valer 1 a los 18. Si el paciente ya pasó de 18 y sigue en pediatría, $x_1 = 1$ y se marca como caso vencido.

**Complejidad clínica.** Con $K$ = número de diagnósticos crónicos activos y $K_{\max}=5$ (que es el número de casillas de diagnóstico secundario que tiene la historia clínica del INSN):

$$x_2 = \min\!\left(\frac{K}{K_{\max}},\, 1\right)$$

**Severidad ponderada.** Con $w_i$ los pesos definidos en el archivo de reglas y $w_{\max}$ la suma máxima posible:

$$x_3 = \frac{\sum_{i \in \mathcal{D}(p)} w_i}{w_{\max}}$$

**Dependencia tecnológica:** $x_4$ = suma normalizada de dispositivos (gastrostomía, traqueostomía, ventilación mecánica domiciliaria, diálisis).

**Brecha de preparación.** Con el puntaje TRAQ del paciente, que va de 1 a 5:

$$x_5 = \frac{5 - \mathrm{TRAQ}}{4}$$

**Riesgo de pérdida.** Con $\Delta$ = meses desde la última consulta y $\theta$ = intervalo esperado según su patología:

$$x_6 = \mathrm{clamp}\!\left(\frac{\Delta}{2\theta},\, 0,\, 1\right)$$

**Barrera de acceso:** $x_7$ = 1 si la procedencia está fuera de Lima Metropolitana.

**Continuidad de aseguramiento:** $x_8$ = 1 si el régimen de seguro cambia al cumplir 18.

### La fórmula

$$\mathrm{IUT}(p,t) = \sigma\!\left(\beta_0 + \sum_{i=1}^{n} \beta_i\, x_i(p,t)\right), \qquad \sigma(z) = \frac{1}{1+e^{-z}}$$

con el semáforo definido por dos umbrales:

$$\text{estado} = \begin{cases}
\text{ROJO}   & \mathrm{IUT} \ge \tau_2 \\
\text{ÁMBAR}  & \tau_1 \le \mathrm{IUT} < \tau_2 \\
\text{VERDE}  & \mathrm{IUT} < \tau_1
\end{cases}$$

### Qué es β y de dónde sale

$\boldsymbol\beta$ es el **vector de pesos**: cada $\beta_i$ dice cuánto pesa el factor $x_i$.

**Al inicio no se estiman con datos: los pone el médico.** Los β *son* la política clínica escrita como número. Que la fibrosis quística pese más que la artritis idiopática juvenil es una decisión clínica, no estadística.

### Por qué una función logística — la derivación de la elección

Esta es la parte que hay que saber defender si preguntan.

**Paso 1 — hace falta acotar el resultado.** La suma $\sum \beta_i x_i$ no tiene límite superior ni inferior. Queremos una salida entre 0 y 1 para poder fijar umbrales estables.

**Paso 2 — se descarta la normalización min-max.** Normalizar con $(z - z_{\min})/(z_{\max} - z_{\min})$ tiene un defecto grave: depende de la cohorte. Entra un paciente con puntaje extremo y **todos los demás cambian de valor**. Los umbrales se moverían solos. Inaceptable en algo clínico. La función $\sigma$, en cambio, es fija y no depende de los datos.

**Paso 3 — $\sigma$ es monótona creciente**, así que si solo interesa *ordenar* pacientes, no cambia nada: preserva exactamente el orden. Su valor está en otra parte.

**Paso 4 — la razón de fondo.** $\sigma$ es la función inversa del *logit*:

$$z = \ln\frac{p}{1-p} \quad\Longleftrightarrow\quad p = \frac{1}{1+e^{-z}}$$

Es decir, $z$ **es un logaritmo de momios** (*log-odds*). Esto trae dos consecuencias valiosas:

*Interpretabilidad clínica.* Como $\partial z/\partial x_i = \beta_i$, resulta que $e^{\beta_i}$ es el **odds ratio** por unidad de $x_i$: "tener gastrostomía multiplica los momios de sufrir una interrupción de atención por $e^{\beta}$". Los odds ratios son moneda corriente en epidemiología: le estamos hablando al médico en su propio idioma.

*Explicabilidad sin herramientas extra.* El aporte del factor $i$ es exactamente $\beta_i x_i$. Se puede mostrar en pantalla el desglose ordenado de mayor a menor. **No hace falta ninguna técnica añadida de explicabilidad: el modelo es su propia explicación.**

**Paso 5 — el puente hacia el aprendizaje automático.** La forma funcional que hoy usamos con pesos puestos por un médico **es exactamente la de una regresión logística**. El día que existan etiquetas $y_i \in \{0,1\}$ ("¿este paciente tuvo una interrupción mayor a 12 meses?"), la verosimilitud es

$$\mathcal{L}(\boldsymbol\beta) = \prod_i p_i^{\,y_i}(1-p_i)^{1-y_i}$$

su logaritmo

$$\ell(\boldsymbol\beta) = \sum_i \big[\,y_i \ln p_i + (1-y_i)\ln(1-p_i)\,\big]$$

y el gradiente colapsa a una expresión notablemente simple:

$$\nabla\ell = \sum_i (y_i - p_i)\,\mathbf{x}_i = 0$$

que se resuelve numéricamente por Newton-Raphson / IRLS. **No cambia el modelo. No cambia una línea de arquitectura. Solo cambia el valor de β.**

Ese es el argumento entero, y da la frase de cierre del pitch:

> *"Hoy los pesos los define el clínico porque no existe el dato de resultado. Pero el sistema, al registrar quién transitó y quién tuvo una interrupción, **genera la etiqueta que hoy no existe**. En dieciocho meses se pueden ajustar los coeficientes con datos reales del INSN — misma ecuación, mismos coeficientes interpretables, ahora empíricos. El MVP no es un modelo: es el instrumento que crea el conjunto de datos con el que después sí se puede modelar."*

### Cómo se eligen los umbrales

$\tau_1$ y $\tau_2$ no son números mágicos: **se calibran por capacidad operativa real.** Si el equipo puede atender 20 pacientes al mes, se elige $\tau_2$ tal que

$$\big|\{p : \mathrm{IUT}(p) \ge \tau_2\}\big| \approx 20$$

Eso es diseño centrado en el recurso disponible, no en un umbral inventado.

### Nota de honestidad

Un puntaje ponderado de 0 a 100 sin sigmoide ordena exactamente igual. La sigmoide se elige por el puente al aprendizaje automático y por la lectura en odds ratios. **Decirlo así en el pitch — "elegimos σ por esta razón, y sabemos que para solo ordenar no era necesaria" — demuestra criterio.** Elegir con justificación vale más que acertar por accidente.

## 4.5 Dónde va la inteligencia artificial y dónde no

Esta sección es la que nos diferencia. La mayoría de equipos meterá aprendizaje automático porque suena bien. Nosotros explicamos **por qué en cada capa elegimos lo que elegimos**.

> ### **Determinístico donde importa la seguridad y la auditoría. Probabilístico donde ahorra tiempo humano y hay un humano firmando.**

### Detección y priorización → motor de reglas, no aprendizaje automático

Cuatro argumentos, que hay que tener memorizados:

1. **No hay etiquetas.** Un clasificador supervisado necesita saber cuál fue el resultado real: "este paciente sufrió una interrupción de atención". El INSN no tiene ese conjunto de datos. Entrenar sin etiquetas es teatro.
2. **Desbalance de clases.** Un clasificador ingenuo sobre eventos poco frecuentes aprende a decir "no" siempre y obtiene 99 % de exactitud siendo completamente inútil.
3. **Trazabilidad clínica.** Un médico debe poder responder *"¿por qué este paciente está en rojo?"*. Con reglas: "porque tiene 4 diagnósticos crónicos activos, dependencia de gastrostomía y cumple 18 en 7 meses". Con un modelo opaco: "porque sí". Lo segundo no pasa un comité de ética.
4. **Validar un modelo clínico en 48 horas es imposible.** Validar reglas revisadas por un médico, sí.

**Sobre la objeción "las reglas habría que actualizarlas siempre":** es un problema de diseño, no de algoritmo. No se escriben como condicionales dentro del código; se escriben como **archivo de datos versionado** que un médico puede editar sin tocar una línea de programación. Y además, **la lista base ya viene dada por el Estado** (ver §5.1).

```yaml
# reglas_transicion.yaml   v2.0
# fuente base: RM 478-2026-MINSA (558 diagnósticos raros en CIE-10)
# responsable: __________   revisión: 2026-08-14

ventana_inicio_anios: 14
umbral_ambar: 0.45
umbral_rojo:  0.75          # calibrado a la capacidad real del equipo

condiciones_cronicas:
  - { cie10: "E84*", etiqueta: "Fibrosis quistica",         peso: 5, erh: true }
  - { cie10: "N18*", etiqueta: "Enfermedad renal cronica",  peso: 5 }
  - { cie10: "Q21*", etiqueta: "Cardiopatia congenita",     peso: 4 }
  - { cie10: "G80*", etiqueta: "Paralisis cerebral",        peso: 4 }
  - { cie10: "E10*", etiqueta: "Diabetes tipo 1",           peso: 3 }

dependencia_tecnologica:
  - { termino: "ventilacion mecanica domiciliaria", peso: 5 }
  - { termino: "dialisis peritoneal",               peso: 5 }
  - { termino: "traqueostomia",                     peso: 4 }
  - { termino: "gastrostomia",                      peso: 3 }
```

> *"Las reglas no son código: son la política clínica del hospital, escrita en un archivo que el hospital firma y versiona. Cuando cambia la política, cambia el archivo, no el software. Y la lista base no la inventamos nosotros: es la RM 478-2026 del MINSA."*

### Procesamiento de lenguaje → aquí sí, y solo aquí

El texto libre de la historia clínica (*Relato*, *Exámenes Auxiliares Previos*, *Tratamiento Recibido*, *Antecedentes patológicos*, *Plan de Trabajo*) es donde vive la información que **no está codificada** y que es justamente la que se pierde en la transferencia.

Tareas, en orden de valor:

1. **Redactar el borrador del Pasaporte**: de quince años de evoluciones a una página. Es una tarea de resumen, donde los modelos de lenguaje son genuinamente buenos, y donde el error es tolerable **porque un médico firma antes de emitir**.
2. **Extraer entidades**: medicación activa con dosis, dispositivos, cirugías con fecha, alergias.
3. **Sugerir codificación**: proponer el CIE-10 faltante contra la lista oficial.
4. **Detectar banderas** que las reglas no ven: "no acude desde…", "abandonó tratamiento", "familia refiere dificultad económica".

**Sobre correr el modelo dentro de la institución.** Para la demo, un modelo local pequeño es más lento y complica el hardware. Para el despliegue real es la única opción viable, porque **los datos clínicos del MINSA no pueden salir a un servicio externo**. Ese es el argumento serio y conviene decirlo antes de que lo pregunten.

La respuesta que desarma la objeción de "eso necesita mucho hardware":

> *"Esto no es inferencia en tiempo real. Es aproximadamente un paciente por día hábil, y el Pasaporte se genera **una vez** por paciente, en un proceso nocturno. Aunque cada resumen tomara dos minutos en CPU, son unas ocho horas de cómputo **al año**. Un servidor institucional existente lo hace en su tiempo muerto. El costo marginal de infraestructura es cero."*

**Patrón de proveedor intercambiable.** Una interfaz abstracta con tres implementaciones:

```
LLMProvider (interfaz)
 ├── GroqProvider        → demo en vivo, gratis, rápido
 ├── GeminiProvider      → respaldo (Google AI Studio, capa gratuita)
 └── OllamaProvider      → despliegue interno (Qwen/Llama ~7B cuantizado)
```

Se cambia de proveedor con una variable de entorno. En la demo corre con una API gratuita; en la lámina de arquitectura se muestra que el mismo código corre cien por ciento dentro de la institución.

**Y siempre: datos sintéticos en el hackathon. Ningún dato de paciente real, en ningún momento.**

---

# PARTE 5 — Por qué esto es viable en el Perú

## 5.1 La lista de reglas ya existe y es oficial

La **RM 478-2026-MINSA**, del 11 de mayo de 2026, aprueba el listado vigente de enfermedades raras o huérfanas: **558 diagnósticos codificados en CIE-10**. Se actualiza cada tres años por mandato del DS 002-2025-SA, bajo la Ley 29698 modificada por la Ley 31738.

**Por qué importa tanto:** no tenemos que inventar qué códigos cuentan como raros, ni pedirle esa lista al mentor, ni defenderla ante el jurado. El Estado peruano la publicó hace tres meses. Nuestro archivo de reglas deja de ser una lista armada a ojo y pasa a ser **un artefacto normativo vigente y citable**.

**Nota de precisión, importante:** MINSA codifica enfermedades raras **solo en CIE-10**. No usa ORPHAcode. Nosotros podemos anotar ORPHAcode en paralelo como propuesta de mejora — porque CIE-10 colapsa cientos de enfermedades raras distintas en códigos genéricos, lo que limita la investigación y la comparación internacional — pero **nunca presentarlo como si ya fuera lo oficial en el Perú**.

*Pendiente de verificar con el mentor:* el criterio de prevalencia. Una fuente indica 1 por cada 2 500 habitantes; el material del reto menciona 1 de cada 100 000. Son criterios muy distintos. **No poner ninguno de los dos en una lámina hasta confirmarlo.**

## 5.2 Existe un registro nacional que nadie está usando para esto

El **RNPERH** (Registro Nacional de Personas con Enfermedades Raras y Huérfanas) tiene entre sus propósitos declarados "orientar compras, talento humano y **referencia de pacientes**". Ya existe un registro nacional cuya función incluye orientar referencias, y nadie lo está usando para transición. Nuestro sistema es un alimentador natural de ese registro.

## 5.3 El estándar de interoperabilidad ya está definido

MINSA publica una guía de implementación FHIR **nacional** — **HL7.FHIR.PE.COREPE**, versión R4, basada en el *International Patient Summary* — con perfiles ya definidos: `PacientePe`, `ProfesionalPe`, `OrganizacionPe`, `AlergiaPe`, `ConditionPe`, `MedicationStatementPe`, `CompositionPe`, `BundlePe`.

Está en versión 0.1 borrador, pero **existe**. Y esos ocho perfiles son exactamente lo que necesita un resumen de transición.

> *"Nuestro Pasaporte no es un PDF bonito: su versión digital es un paquete FHIR conforme al perfil CorePE del MINSA. El día que RENHICE esté operativo, esto se conecta sin reescribir nada."*

Ningún equipo de hackathon hace eso. Es diferenciación pura y cuesta cero.

## 5.4 El problema abierto: no sabemos a dónde derivar

**Este es el punto más débil de la propuesta y hay que decirlo antes de que lo diga el jurado.**

REFCON, el aplicativo oficial de derivaciones, asigna destino por capacidad resolutiva y geografía, **no por competencia clínica en una patología específica**. Para una enfermedad rara puede sencillamente no existir un servicio adulto equivalente en el país.

Y hay un indicio: la página oficial de Referencia y Contrarreferencia del INSN San Borja **solo describe cómo recibir pacientes**. Sobre cómo derivar hacia afuera, y qué pasa a los 18 años, no dice nada. El instituto está diseñado como receptor, no como emisor. *(Es evidencia indirecta; hay que confirmarla con el mentor.)*

**Nuestro plan mínimo:** construir con el mentor un **directorio de destinos** — una tabla que mapee diagnóstico CIE-10 → servicio adulto candidato. Aunque sean 30 filas, es un artefacto que hoy no existe en ningún lado, y su ausencia es parte del diagnóstico del problema.

Reconocerlo con un plan es infinitamente más fuerte que fingir que está resuelto.

## 5.5 No pedimos una norma nueva

La **NT 018-MINSA** obliga a la contrarreferencia desde 2005. En la práctica casi no se ejecuta.

**No estamos pidiendo que se cree una obligación: estamos dando la herramienta para cumplir una que ya existe.** Eso es muchísimo más fácil de vender a una institución pública que cualquier propuesta que requiera nueva normativa.

## 5.6 El sistema del hospital: SisGalenPlus

El INSN SB usa **SisGalenPlus** (confirmado por el mentor). Es la suite de gestión hospitalaria desplegada en buena parte de los establecimientos MINSA, con componentes GalenHOS (hospitales), GalenCEN (centros de salud) y GalenMART (almacén de datos). Cubre admisión, citas, farmacia, laboratorio, imágenes y archivo de historias clínicas; en otros institutos aparece con módulos de historia clínica electrónica, firma digital y FUA electrónico.

Dos hechos que respaldan la viabilidad técnica:

- MINSA señaló al **INSN SB como el primer establecimiento con "HIS Hospitalario"**.
- En la **I Conectatón 2022 el INSN SB integró su sistema Galenos con REFCON** para gestionar referencias y contrarreferencias.

Es decir: la ruta *sistema hospitalario → módulo externo → REFCON* no es hipotética. El propio instituto ya la recorrió una vez.

*(Aviso de rigor: el portal del INSN dio timeout al intentar leer el detalle técnico de esa nota. El dato proviene del titular de su propia publicación. Confirmar antes de afirmarlo en el pitch.)*

## 5.7 Lo que encontramos leyendo la plantilla de historia clínica

Revisamos la plantilla oficial de historia clínica de hospitalización del INSN San Borja (RD N° 000109-2021-DG-INSN-SB). Estructura: I-Anamnesis, II-Examen Físico, III-Impresión Diagnóstica, IV-Plan de Trabajo.

**Campos que sirven directamente:**

| Campo | Para qué lo usamos |
|---|---|
| Fecha de Nacimiento | Disparador temporal |
| **Diagnóstico(s) Principal(es) + CIE-10** (4 casillas) | Clasificación de cronicidad y rareza — **ya viene codificado** |
| **Diagnósticos Secundarios + CIE-10** (5 casillas) | Complejidad = número de códigos activos |
| Alergias / Reacciones adversas / Transfusiones | Va directo al Pasaporte |
| Antecedentes patológicos, Intervenciones Quirúrgicas | El historial que hoy se pierde |
| Procedencia / Domicilio | Indicador de barrera de acceso |
| Datos socioeconómicos (luz, agua, hacinamiento) | Determinantes sociales, ya recolectados |
| Estadío Tanner, Menarquia | El formato ya contempla adolescentes |
| Tipo y N° de Seguro | Continuidad de aseguramiento después de los 18 |

**Tres hallazgos que valen como aporte propio del equipo:**

1. **La historia clínica ya trae CIE-10 codificado.** Esto elimina la necesidad de un modelo que clasifique diagnósticos. Ahorramos ahí y gastamos el procesamiento de lenguaje donde sí hace falta: el texto libre.
2. **No existe ningún campo de transición.** Ni plan, ni médico de adultos asignado, ni fecha de transferencia. El formato asume que el paciente es niño para siempre. → **Micro-intervención de costo cero: proponer una sección "V — Plan de Transición".** Es un entregable en sí mismo.
3. **Los campos "Informante" y "Parentesco con el Paciente" asumen un tercero.** A los 17 años el informante debería empezar a ser el propio paciente. Detalle pequeño, simbólicamente potente para el trabajo de empatía.

## 5.8 Marcos internacionales que respaldan el diseño

**Got Transition — Six Core Elements**, con las edades que recomiendan:

1. Política de transición escrita y compartida (12–14 años)
2. Registro y seguimiento (14–18) ← **entra nuestro software**
3. Evaluación de preparación del adolescente (14–18) ← **le damos soporte**
4. Plan de transición con resumen médico (14–18) ← **entra el Pasaporte**
5. Transferencia efectiva (18–21)
6. Confirmación de que la transferencia se completó (18–23) ← **entra el cierre de ciclo**

Nota estratégica: los elementos 2, 4 y 6 son los que un software resuelve bien y los que hoy no se hacen. Los elementos 1, 3 y 5 son organizacionales. **Decir explícitamente que cubrimos 2, 4 y 6, y que 1 y 5 no son software, demuestra que sabemos dónde termina nuestra herramienta.** Eso pesa ante un jurado clínico.

**Ready Steady Go** (NHS Southampton): escalonamiento por edad en tres etapas. Formularios PDF públicos y gratuitos, adaptables sin licencia.

**TRAQ** (*Transition Readiness Assessment Questionnaire*): 20 preguntas, escala 1 a 5, mide qué tan preparado está el adolescente para manejar su propia salud. **Existe versión en español validada.** No inventamos la escala.

---

# PARTE 6 — Ejecución

## 6.1 Los cinco entregables

**(A) El proceso nocturno.** Corre solo, calcula el IUT de toda la cohorte, arma borradores de Pasaporte, revisa contadores de 90 días. Es el corazón y nadie lo ve nunca.

**(B) La capa de avisos.** Correo semanal, alertas de plazo vencido, cola de mensajes de WhatsApp listos para enviar con un clic. Es lo que hace que el sistema exista en la vida real.

**(C) El Pasaporte de Salud 18+.** Una o dos páginas: diagnósticos, cirugías, medicación activa, alergias, dispositivos, especialistas, qué vigilar, a quién llamar. Con **QR** que abre la versión digital — útil en Emergencia, que es el escenario de más impacto en el pitch. Exporta también el paquete FHIR. Dos versiones del mismo contenido: lenguaje clínico y lenguaje ciudadano para la familia. Con el aviso normativo del §4.3.

**(D) La pantalla de detalle.** Donde se entra desde el correo: ver por qué un paciente está priorizado, revisar y firmar el Pasaporte, consultar indicadores.

**(E) El cierre de ciclo.** Al emitir la derivación se abre un contador. Si a los 90 días no hay confirmación de primera cita en adultos, se emite alerta y se contacta a la familia.

Métrica primaria del proyecto:

$$\text{Tasa de transferencia efectiva} = \frac{\#\{\text{pacientes con 1.ª cita adulto confirmada} \le 6 \text{ meses}\}}{\#\{\text{pacientes transferidos}\}}$$

Hoy en el INSN ese número probablemente **no existe**. Que nuestro sistema lo produzca por primera vez es, por sí solo, un resultado.

## 6.2 Stack de costo cero

| Capa | Herramienta | Costo | Por qué |
|---|---|---|---|
| Backend | **FastAPI** (Python) | S/ 0 | Rápido, documentación automática |
| Base de datos | **SQLite** | S/ 0 | Un archivo, cero configuración |
| Formato estándar | `fhir.resources` + validador **HAPI FHIR** público | S/ 0 | Validación contra FHIR R4 |
| Reglas | YAML + `pydantic` | S/ 0 | Editable por clínicos |
| Lista de enfermedades | **RM 478-2026-MINSA** | S/ 0 | Fuente normativa oficial |
| Correo | SMTP institucional (demo: cuenta cualquiera) | S/ 0 | El hospital ya tiene servidor |
| WhatsApp | **Enlaces `wa.me`** + envío por un clic | S/ 0 | Sin API, sin contrato, sin aprobación |
| Procesamiento de lenguaje (demo) | **Groq** / **Google AI Studio** capa gratuita | S/ 0 | Rápido para demostrar en vivo |
| Procesamiento (despliegue) | **Ollama** + Qwen2.5-7B o Llama-3.1-8B cuantizado | S/ 0 | Corre dentro de la institución |
| Respaldo sin internet | **spaCy** + diccionarios CIE-10 | S/ 0 | Por si falla el wifi del evento |
| PDF | **WeasyPrint** o ReportLab | S/ 0 | Pasaporte imprimible |
| QR | `qrcode` (pip) | S/ 0 | |
| Frontend | **Streamlit** o HTML + Tailwind | S/ 0 | Streamlit si el tiempo aprieta |
| Datos de prueba | Generador propio con `Faker` | S/ 0 | **Nunca datos reales** |
| Hosting | **Hugging Face Spaces** / **Streamlit Cloud** | S/ 0 | Demo con dirección pública |
| Repositorio | GitHub | S/ 0 | |

**Presupuesto total: S/ 0.** Y eso es parte del argumento: una solución que el INSN puede desplegar sin proceso de adquisición es una solución que puede existir el año que viene.

## 6.3 Plan de trabajo

**Regla: construir lo que sea invariante a lo que responda el mentor.** Si construimos el adaptador antes de saber de dónde salen los datos, tiramos ese trabajo.

### Empezar ya

| # | Tarea | Tiempo estimado |
|---|---|---|
| 1 | Generador de cohorte sintética (~300 pacientes) sobre la lista RM 478-2026 | 2 h |
| 2 | Motor de reglas leyendo el YAML | 2 h |
| 3 | Cálculo del IUT con desglose por factor | 2 h |
| 4 | Generador del Pasaporte: PDF + QR + aviso normativo | 3 h |
| 5 | Exportador del paquete FHIR CorePE | 2 h |
| 6 | Capa de avisos: correo + cola de WhatsApp | 2 h |
| 7 | Contador de 90 días e indicadores | 1 h |
| 8 | Pantalla de detalle | 3 h |

### Dejar parametrizado, no construir

- El adaptador de entrada (depende de si SisGalenPlus tiene historia clínica electrónica o si sigue en PDF)
- El directorio de destinos
- Los pesos $\beta_i$ y los umbrales $\tau_1, \tau_2$

### Trabajo de campo, en paralelo

- Journey map con el vacío visible
- Un caso real anonimizado que cuente el mentor
- Las preguntas de §6.4

### Verificación — no saltarse

- Revisar que el desglose del IUT sea coherente en cinco casos calculados a mano
- Validar el paquete FHIR contra el validador HAPI
- Comprobar que ningún mensaje de WhatsApp de la cola contenga datos clínicos
- Ensayar el pitch completo con **un** paciente ficticio, de principio a fin

## 6.4 Preguntas para el mentor

**Proceso actual — lo más importante. No asumir nada.**

1. Hoy, ¿qué ocurre exactamente cuando un paciente crónico cumple 18 en el INSN SB? ¿Hay procedimiento escrito o depende del médico?
2. ¿Existe un hospital de adultos "contraparte" definido, o depende de cada caso? ¿Cómo se resuelve para enfermedades raras sin especialista adulto en el país?
3. ¿Se emite derivación formal por REFCON, o se da de alta y la familia se las arregla?
4. **¿Alguien sabe hoy cuántos pacientes se transfirieron el año pasado y cuántos llegaron?**
5. ¿Hay flexibilidad en el límite superior de edad? ¿Se quedan pacientes de 19 o 20 en pediatría?

**Sistemas.**

6. ¿Qué módulos de SisGalenPlus están activos? ¿La historia clínica de hospitalización ya está en el sistema, o sigue en PDF con firma digital?
7. ¿Hay vista de reportes, esquema documentado o API sobre SisGalenPlus, o solo acceso por la aplicación?
8. ¿La plantilla RD N° 000109-2021 sigue vigente?
9. ¿Hay algún dato exportable, aunque sea agregado y anonimizado, para calibrar el modelo?

**Sobre la capa de avisos (nuevo).**

10. ¿Los jefes de servicio usan efectivamente el correo institucional? ¿Con qué frecuencia?
11. ¿Existe hoy algún reporte impreso que circule por los servicios al que podríamos sumarnos?
12. ¿El hospital ya se comunica con las familias por WhatsApp? ¿Hay alguna política al respecto?

**Clínico.**

13. ¿Qué diagnósticos concentran el mayor volumen de pacientes que llegan a los 18? (Sospecha: cardiopatías congénitas, neurológicos y parálisis cerebral, enfermedad renal crónica, supervivientes oncológicos, errores innatos del metabolismo.)
14. ¿A qué edad sería razonable iniciar el proceso en el contexto peruano? Got Transition dice 12–14; puede no ser realista aquí.
15. ¿Cuál es el criterio de prevalencia vigente para enfermedad rara en el Perú?
16. ¿Hay algún caso concreto, anonimizado, de un paciente que se perdió? **Un caso real vale más que veinte estadísticas en el pitch.**

**Normativo y de viabilidad.**

17. Si el Pasaporte se posiciona como documento complementario y no como resumen de historia clínica normado, ¿ve algún impedimento?
18. Si esto funcionara, ¿quién lo operaría? ¿Enfermería, Servicio Social, la Oficina de Referencias?

## 6.5 Preparación de objeciones

| Lo que van a decir | Lo que respondemos |
|---|---|
| *"Esto es un cronograma en Excel, no IA"* | "Correcto, y por eso la detección **es** una regla determinística: sería irresponsable usar aprendizaje automático donde una regla auditable basta. La IA está donde hay texto libre: convertir quince años de evoluciones en un resumen de una página. Eso ninguna regla lo hace." |
| *"No tienen acceso al sistema del hospital"* | "Por eso construimos el adaptador y el núcleo estándar, no una integración específica. El núcleo emite FHIR R4 conforme al perfil CorePE del MINSA. Solo el conector de origen cambia: alrededor del 5 % del código. Y el INSN ya integró su sistema con REFCON en 2022, así que la ruta existe." |
| *"Le están agregando una pantalla más al personal"* | "No. El sistema busca a la persona: llega un correo cuando hay algo que hacer, y si no hay nada, no llega nada. La pantalla solo se abre desde ese correo." |
| *"¿Y la privacidad?"* | "Datos cien por ciento sintéticos en la demo. Por WhatsApp nunca viaja información clínica, solo avisos de proceso. El modelo de lenguaje corre dentro de la institución en el despliegue. Y es aproximadamente un paciente por día en proceso nocturno, no inferencia masiva." |
| *"Otro equipo tiene un modelo de machine learning"* | "Nos preguntamos con qué etiquetas lo entrenaron. Nosotros no las tenemos, y el INSN tampoco. Nuestro sistema **produce** esa etiqueta; en dieciocho meses se ajustan los coeficientes con datos reales. Es la misma ecuación, ahora empírica." |
| *"¿Por qué el hospital lo adoptaría?"* | "Porque no le pide una norma nueva: la contrarreferencia ya es obligatoria por la NT 018. Le damos la herramienta para cumplir algo que ya debe hacer, a costo cero, sin tocar su sistema y sin capacitarlo en nada nuevo." |
| *"¿Cómo miden el impacto?"* | "Tasa de transferencia efectiva a seis meses. Referencia internacional: los programas estructurados bajan la interrupción de 36.2 % a 12.7 %. Hoy el INSN no tiene ese indicador; nuestro sistema lo genera." |
| *"¿Su Pasaporte reemplaza la historia clínica?"* | "No, y está impreso en el documento. El resumen de historia clínica es un documento normado por la RM 214-2018-MINSA. El Pasaporte es un instrumento complementario, revisado y firmado por el médico tratante." |
| *"¿Por qué no usan ORPHAcode?"* | "Porque MINSA codifica en CIE-10 y el listado vigente es la RM 478-2026 con 558 diagnósticos. Trabajamos sobre la norma vigente. ORPHAcode lo anotamos en paralelo como propuesta de mejora, no como si ya fuera lo oficial." |
| *"¿Y quién opera esto? No hay personal"* | "No pedimos crear un puesto. Convertimos cuatro horas de reconstruir una historia clínica en diez minutos de revisar y firmar. El mismo personal que hoy alcanza para 30 pacientes alcanza para 250." |

## 6.6 Estructura del pitch (7 minutos)

1. **Un caso.** "Ana, 17 años, fibrosis quística, controlada en el INSN SB desde los 2. Cumple 18 el mes que viene." *(0:45)*
2. **El vacío.** Journey map con la mitad superior en blanco. *(1:00)*
3. **El dato.** 36.2 % de interrupción sin programa contra 12.7 % con programa. 3 727 niños con enfermedades raras en el INSN SB en 2023. Y: *"el problema no se ve porque pasa de a uno"*. *(0:45)*
4. **El reencuadre.** "El sistema ya sabe que Ana cumple 18. El problema no es detectar." *(0:30)*
5. **El martes de Ana**, con las pantallas. *(2:30)*
6. **Por qué es viable.** Costo cero. FHIR CorePE del MINSA. Lista RM 478-2026. Apalanca la NT 018 existente. No toca el sistema del hospital. No agrega una pantalla al día de nadie. *(0:45)*
7. **La métrica y el camino.** Tasa de transferencia efectiva; de reglas a modelo empírico en dieciocho meses. *(0:45)*

## 6.7 Qué nos diferencia, con honestidad

Seamos francos: **es casi seguro que varios equipos presenten un tablero con alertas de pacientes que cumplen 18, y probablemente uno o dos un chatbot para el paciente.** Eso es lo que sale si se le pregunta a una IA sin haber estudiado el dominio.

Lo que es difícil de replicar en 48 horas porque exige haber leído:

1. **FHIR CorePE del MINSA.** Ningún equipo de hackathon va a saber que existe.
2. **La RM 478-2026** como fuente de la lista de reglas.
3. **Apalancarse en la NT 018** en vez de pedir norma nueva.
4. **TRAQ validado en español.** Instrumento existente, no invento.
5. **Proponer la sección "V — Plan de Transición"** en la historia clínica del INSN.
6. **Reconocer el problema del destino** con un plan, en vez de esconderlo.
7. **El encuadre normativo del Pasaporte** como documento complementario.
8. **El diseño de avisos que no agrega pantallas.** Es la razón por la que el software hospitalario muere, y la estamos atacando de frente.

Pero el diferenciador real no es ninguno de esos:

> **Si el pitch se puede escribir sin haber hablado con nadie del INSN, no gana.**

Un caso real anonimizado que cuente el mentor — un paciente concreto que se perdió — vale más que las ocho cosas de arriba juntas.

---

# ANEXO A — Glosario

## Siglas clínicas y administrativas

| Término | Qué es |
|---|---|
| **HC** | Historia Clínica. El documento. En el INSN, actualmente en PDF con firma digital (por confirmar si ya está en formato electrónico estructurado). |
| **HCE** | Historia Clínica **Electrónica**. La misma información pero en base de datos, campo por campo, consultable por software. La diferencia con "HC" es crítica: si es PDF, hay que interpretar texto; si es HCE, es una consulta a la base. |
| **CIE-10** | Clasificación Internacional de Enfermedades, 10.ª revisión (OMS). Asigna un código a cada enfermedad: `E84.0` = fibrosis quística con manifestaciones pulmonares, `Q21.3` = tetralogía de Fallot, `N18.5` = enfermedad renal crónica estadio 5. Funciona como el número de parte de un componente: elimina la ambigüedad del nombre. |
| **ORPHAcode** | Codificación específica de enfermedades raras, de Orphanet. **MINSA no la usa.** La mencionamos como anotación secundaria opcional, nunca como si fuera lo vigente. |
| **Referencia** | El establecimiento A envía un paciente al establecimiento B porque no puede resolverlo. |
| **Contrarreferencia** | B devuelve un informe a A diciendo qué pasó con el paciente. **Es lo que cierra el ciclo**, y es lo que casi nunca se ejecuta. |
| **REFCON** | El aplicativo informático oficial del MINSA para gestionar referencias y contrarreferencias. El INSN SB lo usa. |
| **SisGalenPlus** | La suite de gestión hospitalaria que usa el INSN SB y buena parte de los establecimientos MINSA. Componentes: GalenHOS, GalenCEN, GalenMART. |
| **HIS** | *Hospital Information System*: el sistema de información del hospital, en general. |
| **RENHICE** | Registro Nacional de Historias Clínicas Electrónicas, creado por la Ley 30024. **No es una base central con todas las historias**: es un índice que permite que el establecimiento B pida y reciba la historia guardada en el establecimiento A, con consentimiento del paciente. Es, literalmente, la infraestructura legal del problema que resolvemos. |
| **RNPERH** | Registro Nacional de Personas con Enfermedades Raras y Huérfanas. |
| **SIS** | Seguro Integral de Salud. Relevante porque el régimen puede cambiar al cumplir 18. |
| **ERH** | Enfermedades Raras o Huérfanas. "Huérfana" alude a que la industria farmacéutica no desarrolla medicamentos para ellas por falta de rentabilidad. |
| **OPS / OMS** | Organización Panamericana de la Salud (oficina regional de la OMS para las Américas). |
| **Epicrisis** | Resumen clínico que se emite al alta hospitalaria. |
| **Tanner** | Escala de estadios del desarrollo puberal. |
| **Care gap / brecha asistencial** | Período en que un paciente crónico deja de recibir seguimiento. La métrica central del problema. |
| **Lost to follow-up** | Paciente que desaparece del sistema tras la transferencia. |

## Siglas técnicas

| Término | Qué es |
|---|---|
| **HL7** | *Health Level Seven*: organización que define estándares de interoperabilidad en salud. |
| **FHIR** | *Fast Healthcare Interoperability Resources*: el estándar moderno de HL7 para intercambiar datos clínicos. Se transporta en JSON. Define "recursos" (Patient, Condition, Medication…) con estructura fija. |
| **FHIR R4** | La versión 4 de FHIR, que es la que adopta Perú. |
| **CorePE** | La guía de implementación FHIR **nacional peruana**, publicada por MINSA en `dyaku.minsa.gob.pe/guides/`. |
| **IPS** | *International Patient Summary*: estándar internacional de "resumen mínimo del paciente" que CorePE adopta. |
| **Bundle** | En FHIR, un contenedor que agrupa varios recursos en un paquete. La versión digital del Pasaporte es un Bundle. |
| **JSON** | Formato de texto para representar datos estructurados. Es el formato nativo de FHIR. |
| **YAML** | Formato de texto para archivos de configuración, legible por humanos. **Lo usamos solo para el archivo de reglas. Nunca para datos de paciente.** |
| **ETL** | *Extract, Transform, Load*: sacar datos de un sistema, transformarlos y cargarlos en otro. Es lo que hace nuestro adaptador. |
| **API** | *Application Programming Interface*: la forma en que un programa le pide datos a otro. |
| **NLP** | *Natural Language Processing*: procesamiento de lenguaje natural. |
| **LLM** | *Large Language Model*: modelo de lenguaje grande (GPT, Claude, Llama, Qwen). |
| **Ollama** | Herramienta para correr modelos de lenguaje localmente, sin enviar datos a internet. |
| **SMTP** | El protocolo estándar de envío de correo electrónico. |
| **`wa.me`** | Enlaces oficiales de WhatsApp que abren una conversación con un mensaje ya escrito. Gratuitos, sin API. |
| **PHI** | *Protected Health Information*: información de salud protegida que no puede salir de la institución. |
| **Datos sintéticos** | Datos falsos generados por programa, estadísticamente parecidos a los reales. Sirven para desarrollar y demostrar sin tocar datos de pacientes. |
| **Push / Pull** | *Push*: la información llega sola. *Pull*: hay que ir a buscarla. Nuestro diseño es push. |

## Programas e instrumentos internacionales

| Término | Qué es |
|---|---|
| **Got Transition** | Programa estadounidense, el estándar de facto en transición. Define los Six Core Elements. |
| **Six Core Elements** | Los seis componentes de un programa de transición: política, seguimiento, preparación, planificación, transferencia y confirmación. |
| **Ready Steady Go** | Programa del NHS británico (Southampton). Escalona la preparación del adolescente en tres etapas por edad. Formularios públicos y gratuitos. |
| **TRAQ** | *Transition Readiness Assessment Questionnaire*: 20 preguntas, escala 1–5, mide la preparación del adolescente. Versión en español validada. |
| **MyHealth Passport** | Herramienta del programa Good2Go del Hospital for Sick Children (Toronto) que genera un resumen de salud portátil. **De ahí viene la palabra "pasaporte".** |

## Normativa peruana

| Norma | Qué establece |
|---|---|
| **Ley 30024** | Crea el RENHICE. Reglamento: DS 039-2015-SA, modificado por DS 020-2025-SA. |
| **Ley 29698**, mod. **Ley 31738** | Declara de interés nacional la atención de personas con enfermedades raras o huérfanas. |
| **DS 002-2025-SA** | Obliga a actualizar el listado de enfermedades raras cada tres años. |
| **RM 478-2026-MINSA** (11 may 2026) | Aprueba el listado vigente: **558 diagnósticos de enfermedades raras codificados en CIE-10**. |
| **NT 018-MINSA/DGSP-V.01** | Norma Técnica del Sistema de Referencia y Contrarreferencia. Vigente desde 2005. **La contrarreferencia ya es obligatoria.** |
| **RM 214-2018-MINSA**, mod. **RM 265-2018-MINSA** | Norma Técnica de Salud para la Gestión de la Historia Clínica. Regula qué es y quién emite un resumen de historia clínica. |
| **RD N° 000109-2021-DG-INSN-SB** | Aprueba la plantilla de historia clínica de hospitalización del INSN San Borja. Por confirmar si sigue vigente. |

---

# ANEXO B — Fuentes

**Normativa peruana**
- [Ley N.° 30024 — RENHICE (MINSA)](https://www.gob.pe/institucion/minsa/normas-legales/240527-30024) · [Reglamento DS 039-2015-SA](https://busquedas.elperuano.pe/normaslegales/aprueba-el-reglamento-de-la-ley-n-30024-ley-que-crea-el-re-decreto-supremo-n-039-2015-sa-1324291-4) · [Modificación DS 020-2025-SA](https://lpderecho.pe/modifican-reglamento-ley-crea-registro-nacional-historias-clinicas-electronicas-renhice-decreto-supremo-020-2025-sa/)
- [RM N.° 478-2026-MINSA — listado actualizado de enfermedades raras (558 diagnósticos CIE-10)](https://consultorsalud.com/minsa-actualiza-listado-de-enfermedades-raras/)
- [MINSA — Listado oficial de enfermedades raras o huérfanas (ERH)](https://www.gob.pe/13820-que-son-las-enfermedades-raras-o-huerfanas-erh-listado-de-enfermedades-raras-o-huerfanas-erh)
- [Ley N.° 31738, que modifica la Ley 29698](https://busquedas.elperuano.pe/dispositivo/NL/2176746-1)
- [NT N.° 018-MINSA/DGSP-V.01 — Referencia y Contrarreferencia](https://bvs.minsa.gob.pe/local/dgsp/115_NTREFYCON.pdf)
- [Norma Técnica de Salud para la Gestión de la Historia Clínica — RM 214-2018/MINSA y RM 265-2018/MINSA](https://bibliotecavirtual.insnsb.gob.pe/norma-tecnica-de-salud-para-la-gestion-de-la-historia-clinica-r-m-no-214-2018minsa-y-su-modificatoria-aprobada-con-r-m-no-265-2018minsa/)

**Interoperabilidad**
- [HL7 FHIR Perú — Guía de Implementación CorePE (MINSA)](https://dyaku.minsa.gob.pe/guides/) · [Lineamientos CorePE](https://dyaku.minsa.gob.pe/guides/Lineamientos.html)
- [OPS/OMS — Perú valida interoperabilidad de historias clínicas electrónicas (2025)](https://www.paho.org/es/noticias/20-6-2025-transformacion-digital-peru-valida-interoperabilidad-historias-clinicas)

**INSN San Borja**
- [INSN San Borja — SisGalenPlus](https://portal.insnsb.gob.pe/sisgalenplus/)
- [INSN SB en la I Conectatón 2022: integración Galenos–REFCON](https://portal.insnsb.gob.pe/blog/2022/10/07/insn-sb-destaco-en-i-conectaton-2022-logrando-integrar-el-sistema-galenos-al-refcon-y-facilitar-la-gestion-de-referencias-y-contrareferencias/)
- [MINSA — El INSN San Borja es el primero con "HIS Hospitalario"](https://www.gob.pe/institucion/minsa/noticias/33724-el-insn-san-borja-es-el-primero-con-his-hospitalario)
- [INSN San Borja atendió a 3 727 niños con enfermedades raras en 2023](https://portal.insnsb.gob.pe/blog/2024/03/05/insn-san-borja-atendio-a-3727-ninos-diagnosticados-con-enfermedades-raras-en-el-2023/)
- [INSN San Borja — Referencia y Contra Referencia](https://portal.insnsb.gob.pe/referencia-y-contra-referencia/)
- [SIS-GalenPlus — componentes GalenHOS, GalenCEN, GalenMART](https://gestionensalud.mh.org.pe/tool/sis-galenplus/)

**Transición pediátrico-adulto**
- [Got Transition — Six Core Elements](https://www.gottransition.org/six-core-elements/)
- [Ready Steady Go — plan de transición (NHS Southampton)](https://www.uhs.nhs.uk/Media/UHS-website-2019/Patientinformation/Childhealth/ReadySteadyGo/Ready-Steady-Go-Transition-plan.pdf) · [Implementing transition: Ready Steady Go (PubMed)](https://pubmed.ncbi.nlm.nih.gov/26063244/)
- [The Transition of Children Living With Congenital Heart Disease to Adult Care (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10771806/)
- [Validación español-argentina del TRAQ (Arch Argent Pediatr, 2017)](https://www.sap.org.ar/docs/publicaciones/archivosarg/2017/v115n1a05.pdf)
- [SickKids — Guidelines for Transition from Pediatric to Adult Care](https://www.sickkids.ca/siteassets/care--services/centres/trmc/transition-guidelines_2021.pdf)
- [The use and usefulness of MyHealth Passport](https://www.researchgate.net/publication/330834526_The_use_and_usefulness_of_MyHealth_Passport_An_online_tool_for_the_creation_of_a_portable_health_summary)
- [Design and implementation of a patient passport in a pediatric cardiology clinic](https://www.sciencedirect.com/science/article/abs/pii/S1058981319301791)
