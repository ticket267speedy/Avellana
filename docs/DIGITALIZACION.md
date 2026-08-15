# Módulo de digitalización

**Cómo leer una Hoja de Referencia sin que ningún error pase inadvertido.**

---

## El encuadre, y hay que decirlo así en el pitch

El mentor dijo: *"si consiguen digitalizar las historias clínicas sin error, ganan"*.

**"Sin error" no existe.** Ningún sistema —ni Claude, ni Ollama, ni nadie— transcribe escritura médica manuscrita sin equivocarse. Prometerlo es regalarle al jurado la pregunta que te desarma: te traen una letra fea y se acabó.

Lo que sí es alcanzable, y es mejor objetivo de ingeniería:

> ## Ningún error pasa sin ser detectado.

Un campo mal leído que el sistema marca en amarillo **no es un fallo del sistema: es el sistema funcionando.** El fallo es un campo mal leído que pasa en verde.

De ahí sale la métrica que se puede prometer y demostrar:

$$\text{tasa de error no detectado} = \frac{\text{campos mal leídos que quedaron en VERDE}}{\text{campos totales}}$$

**El objetivo de ese número es cero.** La exactitud bruta puede ser 88% y el sistema seguir siendo utilizable en un hospital, siempre que el 12% restante esté en amarillo. Un sistema con 97% de exactitud y 3% de error no detectado, no.

Es un reencuadre honesto y es más fuerte que la promesa original.

---

## Por qué funciona: el formulario tiene estructura

Casi ningún campo de la Hoja de Referencia es texto libre. Eso es lo que hace posible detectar los errores sin leer mejor.

| Capa | Qué detecta | Ejemplo |
|---|---|---|
| **Formato** | Valores imposibles | Un DNI de 7 dígitos. Un celular que no empieza en 9. Una fecha que no es DD/MM/AAAA. |
| **Catálogo** | Valores inexistentes | Un CIE-10 que no está en la RM 478-2026. Una especialidad que no es una de las siete. |
| **Coherencia** | Contradicciones internas | La edad escrita no cuadra con la fecha de nacimiento. Dos casillas excluyentes marcadas. |

Cada capa convierte un error de lectura en un **error detectado**.

### El truco del catálogo cerrado

Para los campos con vocabulario finito no hace falta leer mejor: hace falta **ajustar a lo válido**.

El modelo lee `E84.O` con una letra O. Se busca el vecino más cercano en el catálogo CIE-10 y solo existe `E84.0`. Corregido, sin haber leído mejor, y con constancia de la corrección.

**Y la distancia está ponderada por confusiones típicas de lectura óptica.** Con Levenshtein plano, `E84.O` está a distancia 1 tanto de `E84.0` como de `E84.1` — ambiguo sin necesidad. Pero un lector que ve una O casi nunca quiso decir un 1: quiso decir un 0. Cobrando `0↔O` a 0.3 y una sustitución cualquiera a 1.0, el catálogo desempata solo:

```
"E84.O" → "E84.0"   cuesta 0.30   ✅ verde, corregido
"E84.O" → "E84.1"   cuesta 1.00
"E84.5" → E84.0 / E84.1  ambos a 1.00   ⚠️ ámbar, decide una persona
"XYZ99" → nada dentro del umbral        🔴 rojo, no se inventa
```

Ese comportamiento está en `tests/dominio/test_verificador_extraccion.py`.

### La constancia de la corrección

Toda corrección automática guarda `valor_leido`, `valor_catalogo` y la distancia. **Sin ese rastro, una corrección es indistinguible de una alucinación.** El valor crudo nunca se pierde.

---

## El corpus: por qué lo generamos nosotros

El INSN no va a entregar Hojas de Referencia llenas. Son datos personales y la negativa es correcta y definitiva.

**La salida es generarlas.** Y sale mejor que pedirlas prestadas:

- **No hay dato de nadie.** Se puede versionar, publicar y mostrar en el pitch.
- **La verdad viene gratis.** Nosotros escribimos cada campo, así que sabemos exactamente qué dice sin que nadie transcriba nada. **Eso convierte la evaluación en una función y no en una tarde de trabajo.**
- **Se generan mil, no cinco.**
- Se puede regenerar entero cambiando una semilla.

### Cómo se genera

1. **Plantilla** — se dibuja la Hoja de Referencia en blanco a 2480×3508 (A4 a 300 ppp) con las secciones, etiquetas y cajas del formulario oficial.
2. **Mapa de campos** — el rectángulo de cada uno de los 41 campos. Es la pieza central: convierte *"lee esta página"* en *"lee esta cajita de 340×52 px que contiene un DNI"*.
3. **Escritura** — se rellenan los campos con **15 fuentes manuscritas** de Google Fonts (todas con tildes y ñ verificadas), una por formulario, con tinta, escala, inclinación y presión sorteadas. Cada línea se rota por separado, que es lo que produce renglón torcido en vez de página torcida.
4. **Degradación** — perspectiva, sombra en diagonal, desenfoque, ruido y compresión JPEG. Simula lo que de verdad llega: **una foto de celular enviada por correo**, que es el flujo que el propio INSN describe.

### Reparto por defecto

| Variante | Peso | Por qué |
|---|---|---|
| Foto de celular manuscrita | 60 % | El caso real y el difícil |
| Escaneo limpio manuscrito | 20 % | |
| Tipeado | 15 % | La dirección a la que va el hospital |
| Fotocopia degradada | 5 % | El peor caso |

*TODO: confirmar el reparto con el mentor.*

### La limitación, y hay que declararla

**La letra renderizada con fuente es más regular que la humana.** No varía dentro de una misma palabra, no arrastra el trazo, no se sale del renglón igual. **La exactitud medida sobre este corpus es optimista** respecto de manuscrito real.

Lo que el corpus sí valida honestamente es el pipeline completo, la detección de errores y la calibración de umbrales — que es donde está el aporte. Decirlo antes de que lo pregunten suma.

---

## Uso

```bash
# una sola vez: 18 fuentes de Google Fonts, ~2 MB
python -m relevo.interfaz.cli.descargar_fuentes

# el corpus
python -m relevo.interfaz.cli.generar_corpus --n 200 --salida data/corpus
```

Produce:

```
data/corpus/
├── imagenes/hr_0001.jpg      la foto
├── verdad/hr_0001.json       lo que dice cada campo, exacto
└── manifiesto.json           índice + parámetros
```

---

## Arquitectura

Respeta la regla de dependencia. El motor de verificación es **dominio puro**: aritmética y reglas, sin imágenes, sin red y sin modelo.

| Pieza | Capa |
|---|---|
| `CampoExtraido`, `EstadoCampo`, `Motivo`, `AjusteCatalogo` | `dominio/objetos_valor/` |
| `VerificadorExtraccion`, `EspecificacionCampo`, `ReglaCruzada`, `medir` | `dominio/servicios/` |
| Plantilla, renderizador, degradación | `infraestructura/corpus/` |
| Descarga de fuentes, generación del corpus | `interfaz/cli/` |

El verificador **no lee nada**: recibe lo que el modelo ya leyó. Por eso se prueba sin GPU y en 30 milisegundos.

---

## Lo que falta

| # | Qué | Nota |
|---|---|---|
| 1 | **Rectificación con RANSAC** | Homografía contra la plantilla. 8 grados de libertad, 4 correspondencias por muestra; con 50% de inliers bastan ~71 iteraciones para 99% de éxito. Es lo que permite recortar los campos de una foto torcida. |
| 2 | **Adaptador de lectura** | Implementación de `GeneradorResumen` que recibe recortes y devuelve texto. Primero `SinLLM`, después Ollama con modelo de visión. |
| 3 | **Especificaciones desde YAML** | Hoy las `EspecificacionCampo` se construyen en código. Deben cargarse de `config/`, como el resto de la política. |
| 4 | **Calibrar umbrales** | Con el corpus y la verdad, ajustar `umbral_confianza` **por campo**. Hoy es 0.75 para todos, que casi seguro está mal. |
| 5 | **Pantalla de verificación** | Solo los campos ámbar y rojo, con su motivo. Un minuto de revisar tres campos en vez de quince de tipear cuarenta. |
| 6 | **Conectar con `cohorte_sintetica`** | Que el corpus de documentos y la cohorte del Radar sean la misma población: un formulario escaneado se convierte en un paciente priorizado sin costuras. |
| 7 | **Plantilla real** | Reemplazar el dibujo aproximado por el formulario oficial escaneado y recalibrar coordenadas. |

---

## Hallazgo para el pitch

Mirando la página 2 de la Hoja de Referencia:

> **Condiciones del Paciente a la llegada al Establecimiento Destino** · **Persona que recibe** — nombre, colegiatura, fecha, hora, firma y sello · **N° Hoja de Monitoreo** · Copias: Original SIS · EE.SS. Destino (1ª) · EE.SS. Destino (2ª) · **SRCR (3ª copia)**

**El cierre del ciclo no falta. Está impreso en el formulario oficial, con su propia copia asignada, y simplemente nunca vuelve.**

Eso le da explicación física al 0.55 % de contrarreferencias del estudio de Lima Norte: el mecanismo existe, pero depende de que una tercera copia en papel viaje de regreso.

> *"El cierre del ciclo no hay que inventarlo. Ya está impreso. Solo que es papel, y el papel no vuelve."*
