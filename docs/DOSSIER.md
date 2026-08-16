# RELEVO
## Dossier del proyecto · versión 4 — para el pitch

**Reto 1 · Hackathon INSN San Borja — "Puente 18+"**
**Equipo Avellana** · 15 de agosto de 2026

---

## Cómo usar este documento

Escrito para que **cualquiera del equipo pueda presentar sin haber programado nada.**

- Vas a presentar y tienes 10 minutos → **Partes 1, 2 y 3**
- Te van a preguntar de arquitectura → **Parte 4**
- Te van a preguntar de despliegue o seguridad → **Parte 5**
- Te van a apretar → **Parte 6: debilidades, ya respondidas**
- Sigla que no reconoces → **Anexo**

**Regla de oro del equipo:** no afirmar nada que no esté en este documento. Si alguien pregunta algo que no sabemos, la respuesta es *"no lo sabemos todavía, es una de nuestras preguntas abiertas"*. Un jurado clínico perdona no saber; no perdona inventar.

---

# PARTE 1 — Qué ataca

## 1.1 La restricción que define todo

> **El INSN no atiende a mayores de 18 años bajo ninguna circunstancia.**

No es una demora de atención. Es una **interrupción total en una fecha exacta**. El día del cumpleaños 18 el paciente deja de existir para el instituto donde se atendió quince años.

Eso convierte el proyecto en uno de **prevención de daño**, no de mejora de calidad.

## 1.2 Los cuatro cuellos de botella

| | Cuello | Qué falta hoy |
|---|---|---|
| **B1** | **No hay destino** | Nadie sabe a qué servicio de adultos mandarlo. Para enfermedades raras puede sencillamente no existir en el país. |
| **B2** | **La información no viaja** | La historia clínica del INSN son doce páginas. Lo que cruza es una hoja de referencia de una carilla. Quince años en un párrafo. |
| **B3** | **El paciente no está preparado** | A los 17 la madre sabe todo y el paciente nada: no conoce su diagnóstico, no sabe sus dosis, nunca pidió una cita solo. |
| **B4** | **Nadie cierra el ciclo** | La norma obliga a contrarreferencia desde 2005. Se emite la derivación y nadie confirma que el paciente llegó. |

## 1.3 El reencuadre que hay que decir en voz alta

La idea que a todos se les ocurre primero es *"una IA que detecte a los que van a cumplir 18"*. Hay que descartarla en el pitch, antes de que la descarte el jurado:

> **Detectar quién cumple 18 años no es un problema de inteligencia artificial. Es una resta de fechas.** La fecha de nacimiento ya está en la historia clínica. El hospital ya lo sabe. Y el paciente igual se pierde.

La pregunta correcta es la otra: **¿por qué, sabiéndolo, el sistema igual lo suelta?**

## 1.4 Por qué el problema es invisible

El INSN San Borja atendió **3 727 niños con enfermedades raras en 2023**. En estado estacionario, con edades de 0 a 17:

$$\frac{3\,727}{18} \approx 207 \text{ pacientes/año} \quad\Rightarrow\quad \frac{207}{250 \text{ días hábiles}} \approx 0.8 \text{ por día}$$

*(Supuestos: "atendidos" incluye repetidos; la distribución por edad no es uniforme y sesga a la baja; solo cuenta raras y no crónicas ni complejas, que sesga al alza. Conclusión defendible: **orden de 10² al año**, no más precisión que esa.)*

**Menos de un paciente por día hábil.** Y de ahí sale la mejor frase del pitch:

> *"El problema no se ve porque pasa de a uno. Se pierde un paciente por día. Nadie lo nota. A fin de año son doscientas personas sin continuidad de atención."*

## 1.5 La evidencia

| Dato | Fuente |
|---|---|
| Los programas estructurados bajan la interrupción de **36.2 % a 12.7 %** | Revisión en cardiopatías congénitas |
| Solo el **41 %** de 96 centros europeos tiene programa de transición | Mismo estudio — **no es un problema resuelto en el primer mundo** |
| **110 contrarreferencias sobre 19 951 referencias = 0.55 %** | Estudio DIRIS Lima Norte, Revista Médica Herediana |
| Mediana de espera aceptación → cita: **80–85 días** | Mismo estudio |
| **3 727** niños con enfermedades raras atendidos en 2023 | INSN San Borja |

**El 0.55 % es nuestro dato estrella.** Es peruano, publicado y revisado por pares, y demuestra B4 sin discusión posible.

Y tiene una explicación física que encontramos leyendo el formulario oficial: la página 2 de la Hoja de Referencia **ya trae impreso** el bloque de *"Condiciones del paciente a la llegada"*, con firma de quien recibe y una tercera copia asignada al sistema de referencia.

> **"El cierre del ciclo no hay que inventarlo. Ya está impreso en el formulario oficial. Solo que es papel, y el papel no vuelve."**

---

# PARTE 2 — Qué ofrece

## 2.1 El sistema en tres frases

1. **Un proceso nocturno** que corre solo, prioriza la cohorte de 14 a 18 años con un índice explicable, y prepara lo que haga falta.
2. **Avisos que llegan solos** — correo al equipo, mensajes de WhatsApp listos para despachar. Nadie revisa ninguna pantalla.
3. **Documentos que el paciente se lleva** — el Pasaporte de Salud 18+, en papel, escalonado a los 14, 16 y 17 años.

Más un cuarto: **el ciclo se sigue hasta confirmar que el paciente llegó** al servicio de adultos.

## 2.2 El principio rector

> ### El sistema busca a la persona. La persona no busca al sistema.

Así muere el software hospitalario: le agregas una pantalla más a gente que ya tiene cinco abiertas, nadie la abre, y a los tres meses el proyecto está muerto.

**Ninguna pantalla de Relevo es de revisión obligatoria diaria.** Llega un correo cuando hay algo que hacer, y si no hay nada, no llega nada.

## 2.3 Los cinco entregables

**A · Radar de Transición.** La cohorte ordenada por urgencia, con semáforo. Al abrir un paciente aparece **de dónde sale el número**, factor por factor.

**B · El Índice de Urgencia de Transición (IUT).** Ocho factores, pesos definidos por criterio clínico, y el desglose siempre visible.

**C · Pasaporte de Salud 18+.** Papel que el paciente se lleva. Tres versiones por edad: media página a los 14, una a los 16, dos a los 17. Con QR y aviso normativo al pie.

**D · Digitalización asistida.** Una foto de un documento entra, salen campos validados, y **ningún error pasa sin ser detectado**. Con acta firmada y sellada.

**E · Cierre de ciclo.** Máquina de estados con plazos, proceso nocturno y avisos. Métrica: **tasa de transferencia efectiva a 6 meses** — un número que hoy en el INSN no existe.

## 2.4 El escalonamiento del Pasaporte, y por qué no es cosmético

| Edad | Versión | Contenido |
|---|---|---|
| 14 | media página | Qué tengo, qué tomo, a qué soy alérgico |
| 16 | 1 página | + cómo pedir una cita, qué hacer si me siento mal |
| 17–18 | 2 páginas, doble versión | Completo: clínica para el médico receptor, ciudadana para el paciente |

> *"A los 14 el paciente no necesita saber todo. Darle las dos páginas de la v3 a los 14 garantiza que no lea ninguna."*

Y en cada hito se **captura y verifica el teléfono** — a los 16 y 17, el del propio paciente. Porque a los 18 la madre deja de ser la interlocutora legal y el sistema tiene que tener al paciente. Hoy no lo tiene nadie.

---

# PARTE 3 — El punto de innovación

## 3.1 Lo que NO es original, y hay que citarlo en vez de esconderlo

| Elemento | Ya existe |
|---|---|
| Pasaporte de salud portátil | MyHealth Passport, SickKids Toronto |
| Escalonamiento por edad | Got Transition, Ready Steady Go (NHS) |
| Tablero con semáforo | Cualquier sistema de gestión |
| Resumen con modelo de lenguaje | Lo va a proponer medio hackathon |
| Cuestionario de preparación | TRAQ, validado desde 2014 |

**Presentar alguno de estos como invención propia sería un error grave.** Un jurado con un clínico que haya leído sobre transición lo detecta, y a partir de ahí desconfía de todo lo demás. Citarlos demuestra que estudiamos el campo.

## 3.2 Lo que sí es nuestro

### ① El reencuadre de "sin error" a "sin error no detectado"

El mentor dijo: *"si digitalizan las historias sin error, ganan"*.

**"Sin error" no existe.** Ningún sistema transcribe escritura médica manuscrita sin equivocarse. Prometerlo es regalarle al jurado la pregunta que te desarma.

Lo que sí es alcanzable, y es mejor objetivo de ingeniería:

$$\text{tasa de error no detectado} = \frac{\text{campos mal leídos que quedaron en VERDE}}{\text{campos totales}}$$

**Un campo mal leído que el sistema marca en amarillo no es un fallo: es el sistema funcionando.** El fallo es uno que pasa en verde.

> **88 % de exactitud con 0 % de error no detectado es utilizable en un hospital. 97 % de exactitud con 3 % de error no detectado, no.**

### ② No hay que leer mejor: hay que hacer imposible estar mal en silencio

Casi ningún campo de una Hoja de Referencia es texto libre. Tres capas convierten un error de lectura en un error **detectado**:

- **Formato** — un DNI tiene 8 dígitos, un celular peruano 9 empezando en 9
- **Catálogo** — un CIE-10 tiene que existir en el listado oficial vigente
- **Coherencia** — la edad tiene que cuadrar con la fecha de nacimiento

### ③ Distancia de edición ponderada por confusiones ópticas

Un lector que ve `E84.O` casi nunca quiso decir `E84.1`: quiso decir `E84.0` y confundió el cero con la O. Cobrando esa sustitución a 0.3 en vez de 1.0, el catálogo desempata solo:

```
E84.O  →  E84.0    coste 0.30    ✅ se corrige, con constancia
E84.5  →  ambiguo  1.00 / 1.00   ⚠️ decide una persona
XYZ99  →  nada dentro del umbral 🔴 no se inventa
```

Con Levenshtein plano las dos primeras cuestan igual y el campo va a revisión sin necesidad. **Ese detalle es nuestro.**

### ④ Plazos calibrados con el dato peruano

La mediana de espera aceptación → cita es de **80–85 días**. Un umbral de alerta a los 90 días dispararía en la mitad de los casos que van perfectamente bien — fatiga de alertas, y a la tercera semana nadie las lee.

Por eso la máquina de estados usa **120 días** para esa transición: percentil alto de la distribución observada, no un número redondo. **Diseño derivado de evidencia local.**

### ⑤ Contar lo que nadie cuenta

Dos números que hoy no existen en el INSN y que el sistema produce:

- **Tasa de transferencia efectiva** a 6 meses
- **Pacientes que salen sin destino identificado**

El segundo es especialmente honesto: **no resuelve B1 — nadie puede, si en el Perú no hay servicio adulto para una enfermedad rara.** Lo que hace es volver el vacío contable. *"De 120 evaluados, 87 salieron sin destino identificado."* Ese número convierte una queja en un dato que se le lleva a quien decide.

### ⑥ Habla el idioma que MINSA ya está estandarizando

- **RM 478-2026-MINSA** (11 may 2026) — 558 diagnósticos raros en CIE-10. **Nuestro archivo de reglas no lo inventamos: es normativa vigente de hace tres meses.**
- **HL7 FHIR CorePE** — la guía de implementación nacional del MINSA, R4, basada en el International Patient Summary.
- **NT 018-MINSA** — la contrarreferencia ya es obligatoria. **No pedimos una norma nueva: damos la herramienta para cumplir una que existe.**
- **RM 214-2018-MINSA** — por eso el Pasaporte se declara documento complementario y **no** resumen de historia clínica normado.

## 3.3 La conclusión honesta sobre la innovación

> **Ninguna pieza es original por separado. Lo original es que cada decisión tiene una fuente peruana verificable detrás.**

Eso se llama rigor. Es menos vistoso que una idea brillante y mucho más difícil de improvisar en 48 horas.

## 3.4 Y dónde va la IA — la pregunta que van a hacer

> **Determinístico donde importa la seguridad y la auditoría. Probabilístico donde ahorra tiempo humano y hay un humano firmando.**

**La priorización es un motor de reglas, no aprendizaje automático.** Cuatro razones:

1. **No hay etiquetas.** Un clasificador necesita saber quién sufrió una interrupción. El INSN no tiene ese dato. Entrenar sin etiquetas es teatro.
2. **Desbalance de clases.** Sobre eventos poco frecuentes, un clasificador ingenuo dice "no" siempre y saca 99 % de exactitud siendo inútil.
3. **Trazabilidad clínica.** Un médico debe poder responder *"¿por qué este paciente está en rojo?"*. Con reglas: "tres diagnósticos crónicos, gastrostomía, cumple 18 en siete meses". Con un modelo opaco: "porque sí". Eso no pasa un comité de ética.
4. **Validar un modelo clínico en 48 horas es imposible.** Validar reglas revisadas por un médico, sí.

**Y el remate, que es la mejor frase técnica del pitch:**

> *"Hoy los pesos los define el clínico porque no existe el dato de resultado. Pero el sistema, al registrar quién transitó y quién tuvo una interrupción, **genera la etiqueta que hoy no existe**. En dieciocho meses se ajustan los coeficientes por regresión logística con datos reales del INSN — misma ecuación, ahora empírica.*
>
> ***El MVP no es un modelo: es el instrumento que crea el conjunto de datos con el que después sí se puede modelar."***

---

# PARTE 4 — Arquitectura y aislamiento

## 4.1 La promesa, y por qué es verificable

> **"El núcleo no cambia. Solo se cambia el adaptador."**

Eso lo dice cualquiera. Nosotros lo podemos **demostrar abriendo un archivo**, porque la arquitectura es hexagonal (puertos y adaptadores) con la regla de dependencia verificada por un test que bloquea el commit.

```
   interfaz ────────┐
                    ├──►  aplicación  ──►  dominio
   infraestructura ─┘                        ▲
                                             │
                    (define los puertos que ambos implementan)
```

**Las dependencias apuntan hacia adentro. Siempre.**

- `dominio/` — **no importa nada externo.** Ni base de datos, ni web, ni red. Solo librería estándar.
- `aplicación/` — importa `dominio`. Nada más.
- `infraestructura/` e `interfaz/` — importan hacia adentro e implementan los puertos que el dominio declaró.

`tests/test_arquitectura.py` recorre los imports y **falla** si alguien rompe la regla.

## 4.2 Por dónde entra y sale — el aislamiento

```
   [ SisGalenPlus / documentos en papel ]     ← sistema del hospital
                    │                            NO SE TOCA
                    │  solo lectura, copia
                    ▼
   ┌────────────────────────────┐
   │  ADAPTADOR DE ENTRADA      │  ← única pieza que cambia según la fuente
   └──────────────┬─────────────┘
                  ▼
   ┌──────────────────────────────────────────┐
   │  NÚCLEO — dominio + casos de uso         │
   │  IUT · reglas · máquina de estados       │
   │  verificador anti-error-silencioso       │
   └──────────────┬───────────────────────────┘
                  ▼
   ┌──────────────────────────────────────────┐
   │  CAPA DE AVISOS · correo · papel · WhatsApp │
   └──────────────┬───────────────────────────┘
                  ▼
   ┌───────────┬────────────┬────────────┬──────────┐
   │  Radar    │ Pasaporte  │ Acta       │ REFCON   │
   └───────────┴────────────┴────────────┴──────────┘
```

**Lo más importante del dibujo:** la caja de arriba tiene una flecha que **sale**, ninguna que entra.

> **No escribimos nada en el sistema del hospital. Solo leemos una copia.**

Para un área de informática hospitalaria, esa diferencia separa *"lo evaluamos"* de *"ni lo miro"*.

## 4.3 Los cuatro formatos, y ninguno hace el trabajo del otro

| Capa | Formato | Contiene | Lo consume |
|---|---|---|---|
| Configuración | **YAML** | Reglas y pesos clínicos. **Cero datos de paciente.** | El equipo clínico que edita la política |
| Intercambio | **JSON (FHIR)** | Datos clínicos entre sistemas. Estándar MINSA. | Máquinas: REFCON, RENHICE |
| Documento | **PDF firmado** | El Pasaporte que la familia se lleva | Paciente, familia, médico receptor |
| Vista | **HTML** | La pantalla de trabajo | Personal del INSN |

## 4.4 La política clínica no vive en el código

Los pesos del IUT, los umbrales y los plazos están en `config/*.yaml`, cada valor con su fuente comentada. **Sin ese archivo cargado el sistema no arranca** — es imposible que calcule con pesos que ningún médico aprobó.

> *"Las reglas no son código: son la política clínica del hospital, escrita en un archivo que el hospital firma y versiona. Cuando cambia la política, cambia el archivo, no el software."*

## 4.5 Persistencia

SQLite. Un archivo, cero servidor, cero costo. Guarda cada agregado como documento JSON con las columnas consultables indexadas.

Y un **registro de auditoría encadenado por hash**: cada entrada incluye el hash de la anterior, así que editar o borrar una fila intermedia rompe la cadena y el sistema dice en cuál. Está probado: se editó una fila por SQL y la verificación la detectó.

Migrar a PostgreSQL es escribir otro adaptador del mismo puerto y cambiar **una línea**.

---

# PARTE 5 — Cómo corre hoy y cómo debería correr

## 5.1 Hoy: una laptop haciendo de servidor

| | |
|---|---|
| Aplicación | Streamlit en `localhost:8501` |
| Base de datos | SQLite, un archivo en disco |
| Modelo de lenguaje | Ollama en `localhost:11434` |
| Datos | **100 % sintéticos** |
| Internet | **No hace falta para nada** |

## 5.2 La comunicación con el modelo — NO es un túnel

**Punto importante para no equivocarse ante un mentor técnico.**

El sistema habla con el modelo por un **HTTP POST corriente a `localhost:11434/api/generate`**, con la imagen en base64 y el prompt en el cuerpo. Ollama es un servidor local que escucha en ese puerto. **No hay túnel, no hay VPN, no hay API externa, no sale un solo byte de la máquina.**

*(Lo del túnel fue otra cosa: `cloudflared` para que el equipo pudiera ver la demo desde otra ciudad. Es una herramienta de desarrollo, no forma parte del sistema.)*

Y esto no es solo una decisión de arquitectura: **es un requisito legal.** Un escaneo de Hoja de Referencia trae DNI, partida de nacimiento, afiliación al SIS y el DNI del tutor. Mandarlo a un servicio externo no es una opción.

**El volumen lo hace trivial:** ~1 paciente por día hábil, en proceso nocturno por lotes. Aunque cada documento tardara dos minutos, son **unas ocho horas de cómputo al año**.

## 5.3 Los tres escalones de degradación

Cada uno sigue siendo un sistema útil:

| Escalón | Qué hay | Qué se pierde |
|---|---|---|
| **1** | Dos modelos locales distintos | Nada — hay doble lectura y señal de confianza por desacuerdo |
| **2** | Un solo modelo | Se pierde el contraste; todo lo demás igual |
| **3** | **Sin modelo** | Captura manual asistida |

**El escalón 3 merece explicación, porque suena a fracaso y no lo es.** Sin modelo, la pantalla se convierte en un formulario con validación de formato, ajuste a catálogo CIE-10 y coherencia cruzada en vivo.

> **Hoy en el INSN alguien tipea esos campos en REFCON sin ninguna validación. El escalón 3 los tipea con el catálogo corrigiéndole y la coherencia avisándole. Eso ya es mejor que el estado actual — y funciona sin GPU, sin internet y sin modelo.**

## 5.4 Cómo debería correr

| | Hoy (demo) | Piloto en el INSN |
|---|---|---|
| Dónde | Laptop | Servidor institucional del INSN |
| Base | SQLite local | SQLite o PostgreSQL, **en infraestructura del hospital** |
| Modelo | Ollama local | Ollama en el mismo servidor |
| Proceso nocturno | Manual | Tarea programada, 2:00 a.m. |
| Correo | Cuenta de prueba | SMTP institucional |
| Usuarios | Uno | El equipo de transición |
| Datos | Sintéticos | Reales, y con lo que eso implica |
| Autenticación | **Ninguna** | Directorio del hospital + firma digital |

**Lo que hay que decir sí o sí:**

> *"El día que haya datos reales, esto no puede vivir en la laptop de nadie del equipo ni en un servicio en la nube fuera del hospital. Va en infraestructura del INSN."*

Decirlo antes de que lo pregunten vale mucho.

## 5.5 Sobre la firma y por qué no usamos IP ni MAC

Nos lo planteamos y lo descartamos, y conviene tener la razón lista:

**La MAC es capa 2 y no atraviesa el router.** Servido desde un servidor, el sistema vería la MAC del propio servidor, idéntica para los cuarenta usuarios. Hoy parece funcionar solo porque todo corre en la misma máquina. Además los sistemas operativos aleatorizan la MAC en WiFi por defecto, y se falsifica en un comando.

Y lo de fondo: **identifica la máquina, no a la persona.** En una estación compartida del servicio eso no sirve para una auditoría clínica.

**Lo que el INSN usa de verdad está impreso en su propia historia clínica:** firma digital con certificado. Ese es el camino de despliegue. Para el MVP implementamos el equivalente honesto: usuario declarado + marca de tiempo + **hash del contenido** + cadena de auditoría. La IP y el hostname se registran, pero como **metadato forense, nunca como identidad**.

## 5.6 Presupuesto

| Componente | Costo |
|---|---|
| Todo | **S/ 0** |

Sin APIs de pago, sin licencias, sin servidores contratados. **Una solución que el INSN puede desplegar sin proceso de adquisición es una solución que puede existir el año que viene.**

---

# PARTE 6 — Debilidades

Esta parte existe para que **nosotros digamos las debilidades antes que el jurado**. Un equipo que conoce sus límites se lee como serio; uno que dice que todo funciona, como que no lo probó.

## 6.1 Las que reconocemos de frente

### No hemos hablado con pacientes ni familias

Nuestro diagnóstico viene de literatura internacional, normativa peruana y conversación con el mentor. **No hemos escuchado a una madre decir qué siente cuando le avisan que su hijo ya no se atiende aquí.** Es el vacío más grande del proyecto.

### B1 no lo resolvemos, y no puede resolverlo un software

Si en el Perú no existe un servicio de adultos que atienda una enfermedad rara concreta, ningún sistema lo va a inventar. **Lo que hacemos es volver el vacío contable.**

> *"No resolvemos el problema del destino. Lo contamos, que es lo primero que hay que hacer con un problema que nadie ha medido."*

### La letra sintética es más regular que la humana

El corpus se genera renderizando con fuentes manuscritas sobre un formulario. **La exactitud medida ahí es optimista** respecto de manuscrito real. Lo que el corpus sí valida honestamente es el pipeline, la detección de errores y la calibración de umbrales.

*(Y el corpus lo generamos nosotros porque el hospital no puede entregar formularios llenos — son datos personales y la negativa es correcta.)*

### Los pesos del índice son provisionales

Están puestos por criterio razonado, no por un especialista. **Quince minutos de un médico del INSN los convierten de inventados en validados**, y es la mejor relación esfuerzo/credibilidad que le queda al proyecto.

### No hay autenticación

Hoy quien abre la aplicación escribe su nombre en una caja de texto. **Está declarado como pendiente en la propia pantalla**, no disimulado.

### El umbral rojo no está calibrado

La función existe y funciona — con capacidad de 45 pacientes/mes calcula el umbral 0.930 — pero **por defecto está apagada porque nadie nos ha dado la capacidad real del equipo**. Es un solo número que falta.

## 6.2 Lo que un jurado puede señalar y por qué funcionaría igual

| Objeción | Respuesta |
|---|---|
| *"Depende de que el hospital estandarice sus formularios"* | No. La lectura es **sin plantilla**: se pregunta "¿cuál es el DNI en este documento?", no "¿qué dice el rectángulo (x,y)?". Y el verificador valida **valores, no posiciones**. |
| *"Si el modelo falla, no sirve"* | Funciona en tres escalones. Sin modelo entra en captura manual asistida, que **ya es mejor que tipear en REFCON sin validación**. |
| *"Nadie va a usar otra pantalla"* | Correcto, y por eso el sistema busca a la persona. Llega un correo cuando hay algo que hacer; si no hay nada, no llega nada. |
| *"¿Y si no hay presupuesto?"* | Costo cero. Sin adquisición. |
| *"Se necesita personal que no existe"* | No pedimos crear un puesto. Convertimos cuatro horas de reconstruir una historia en diez minutos de revisar y firmar. **El mismo personal que hoy alcanza para 30 alcanza para 250.** |
| *"Otro equipo tiene machine learning"* | ¿Con qué etiquetas lo entrenaron? Nosotros no las tenemos y el INSN tampoco. Nuestro sistema **produce** esa etiqueta. |
| *"¿Su Pasaporte reemplaza la historia clínica?"* | No, y está impreso en el documento. El resumen de HC es un documento normado por la RM 214-2018. |
| *"¿Por qué no ORPHAcode para las raras?"* | Porque MINSA codifica en CIE-10 y el listado vigente es la RM 478-2026. Trabajamos sobre la norma vigente. |

## 6.3 Estado honesto de los cuatro dolores

| | Modelado | Funcionando | Estado |
|---|---|---|---|
| **B1** No hay destino | ✅ | 🟠 | Se cuenta el vacío. No se resuelve — nadie puede. |
| **B2** La info no viaja | ✅ | ✅ | Pasaporte y Acta funcionando. FHIR pendiente. |
| **B3** Paciente no preparado | ✅ | 🟠 | Pasaporte escalonado y captura de contacto modelados. |
| **B4** Nadie cierra el ciclo | ✅ | ✅ | Proceso nocturno corriendo y avisando. |

**Aclaración que conviene tener clara:** FHIR **no es lo que resuelve B2** — el Pasaporte en papel ya hace que la información viaje. FHIR es el **diferenciador** y lo que conecta con RENHICE. Son cosas distintas y mezclarlas confunde.

---

# PARTE 7 — El pitch, en 7 minutos

| # | Bloque | Tiempo |
|---|---|---|
| 1 | **Un caso.** "Ana, 17 años, fibrosis quística, en el INSN desde los 2. Cumple 18 el mes que viene." | 0:45 |
| 2 | **El vacío.** Journey map con la mitad superior en blanco. | 1:00 |
| 3 | **El dato.** 36.2 % → 12.7 %. Y *"el problema no se ve porque pasa de a uno"*. | 0:45 |
| 4 | **El reencuadre.** "El sistema ya sabe que Ana cumple 18. El problema no es detectar." | 0:30 |
| 5 | **El martes de Ana**, con las pantallas. | 2:30 |
| 6 | **Por qué es viable.** Costo cero · FHIR CorePE del MINSA · RM 478-2026 · apalanca la NT 018 · no toca el sistema del hospital · **no agrega una pantalla al día de nadie**. | 0:45 |
| 7 | **La métrica y el camino.** Tasa de transferencia efectiva; de reglas a modelo empírico en 18 meses. | 0:45 |

## Las frases que hay que memorizar

> *"El problema no se ve porque pasa de a uno."*

> *"No estamos construyendo un detector de cumpleaños. Estamos construyendo el puente que hoy no existe."*

> *"El cierre del ciclo no hay que inventarlo. Ya está impreso en el formulario oficial. Solo que es papel, y el papel no vuelve."*

> *"No prometemos leer sin error, porque eso no existe. Prometemos que ningún error pasa sin ser detectado."*

> *"El MVP no es un modelo: es el instrumento que crea el dataset con el que después sí se puede modelar."*

> *"El software no reemplaza al coordinador de transición; hace que un coordinador pueda con 250 pacientes en vez de 30."*

## El cierre, sin números

Al final, después de la métrica, una frase sin cifras:

> *"El adolescente que a los 18 sabe el nombre de su enfermedad, sabe qué toma y por qué, y puede pedir una cita solo. Eso no aparece en ningún indicador y es probablemente lo más importante que hace el proyecto."*

---

# ANEXO — Glosario

| Sigla | Qué es |
|---|---|
| **HC / HCE** | Historia Clínica / Historia Clínica **Electrónica** (en base de datos, consultable por software) |
| **CIE-10** | Clasificación Internacional de Enfermedades. Código por enfermedad: `E84.0` = fibrosis quística pulmonar |
| **Referencia** | Enviar un paciente a otro establecimiento |
| **Contrarreferencia** | El informe que el receptor devuelve. **Es lo que cierra el ciclo** |
| **REFCON** | Aplicativo oficial del MINSA para registrar referencias y contrarreferencias |
| **SisGalenPlus** | La suite de gestión hospitalaria que usa el INSN |
| **RENHICE** | Registro Nacional de Historias Clínicas Electrónicas. No es una base central: es un índice que permite que un establecimiento pida la historia guardada en otro |
| **FHIR** | Estándar moderno de HL7 para intercambiar datos clínicos. Se transporta en JSON |
| **CorePE** | La guía de implementación FHIR **nacional peruana**, publicada por MINSA |
| **Ollama** | Herramienta para correr modelos de lenguaje **localmente**, sin enviar datos a internet |
| **TRAQ** | Cuestionario validado que mide qué tan preparado está un adolescente para manejar su salud. Existe en español |
| **Got Transition** | Programa estadounidense, estándar de facto en transición. Define los Six Core Elements |
| **IUT** | Índice de Urgencia de Transición. Nuestro |
| **SIS / EsSalud** | Seguro público / seguro de trabajadores formales |
| **Derechohabiente** | Familiar cubierto por el seguro del titular. En EsSalud, los hijos **hasta los 18** |

## Normativa

| Norma | Qué establece |
|---|---|
| **RM 478-2026-MINSA** (11 may 2026) | Listado vigente de enfermedades raras: **558 diagnósticos en CIE-10** |
| **NT 018-MINSA/DGSP-V.01** | Sistema de Referencia y Contrarreferencia. **La contrarreferencia ya es obligatoria** |
| **RM 214-2018-MINSA** | Gestión de la Historia Clínica. Define qué es un resumen de HC y quién lo emite |
| **Ley 30024** | Crea el RENHICE |
| **Ley 29698**, mod. **Ley 31738** | Enfermedades raras o huérfanas de interés nacional |

---

## Fuentes

- [RM N.° 478-2026-MINSA — listado de enfermedades raras](https://consultorsalud.com/minsa-actualiza-listado-de-enfermedades-raras/) · [Listado oficial ERH](https://www.gob.pe/13820-que-son-las-enfermedades-raras-o-huerfanas-erh-listado-de-enfermedades-raras-o-huerfanas-erh)
- [NT N.° 018-MINSA/DGSP-V.01](https://bvs.minsa.gob.pe/local/dgsp/115_NTREFYCON.pdf)
- [Norma Técnica de Gestión de la Historia Clínica — RM 214-2018](https://bibliotecavirtual.insnsb.gob.pe/norma-tecnica-de-salud-para-la-gestion-de-la-historia-clinica-r-m-no-214-2018minsa-y-su-modificatoria-aprobada-con-r-m-no-265-2018minsa/)
- [HL7 FHIR Perú — Guía CorePE (MINSA)](https://dyaku.minsa.gob.pe/guides/)
- [Evaluación del Sistema de Referencia y Contrarreferencia, DIRIS Lima Norte](https://www.redalyc.org/journal/3380/338068009007/html/) — el 0.55 %
- [The Transition of Children Living With Congenital Heart Disease to Adult Care](https://pmc.ncbi.nlm.nih.gov/articles/PMC10771806/) — el 36.2 % → 12.7 %
- [INSN San Borja — 3 727 niños con enfermedades raras en 2023](https://portal.insnsb.gob.pe/blog/2024/03/05/insn-san-borja-atendio-a-3727-ninos-diagnosticados-con-enfermedades-raras-en-el-2023/)
- [Got Transition — Six Core Elements](https://www.gottransition.org/six-core-elements/) · [Ready Steady Go (NHS)](https://www.uhs.nhs.uk/Media/UHS-website-2019/Patientinformation/Childhealth/ReadySteadyGo/Ready-Steady-Go-Transition-plan.pdf)
- [MyHealth Passport — SickKids](https://www.sickkids.ca/siteassets/care--services/centres/trmc/transition-guidelines_2021.pdf)
- [Complex Chronic Conditions v2 (Feudtner, BMC Pediatrics)](https://link.springer.com/article/10.1186/1471-2431-14-199)
- [TRAQ, validación en español (Arch Argent Pediatr)](https://www.sap.org.ar/docs/publicaciones/archivosarg/2017/v115n1a05.pdf)
