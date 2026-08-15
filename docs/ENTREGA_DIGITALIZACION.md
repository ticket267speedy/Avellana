# Entrega — módulo de digitalización

**Para el agente de código.** Terminar la integración y dejarlo corriendo en `localhost`.

Contexto completo en `docs/DIGITALIZACION.md` y `docs/GUIA_OLLAMA.md`. Las reglas del proyecto siguen siendo las de `CLAUDE.md`, sin excepciones.

---

## 0. Qué acaba de entrar al repo

Nueve archivos nuevos. **Ninguno se ha ejecutado en esta máquina todavía** — se escribieron y probaron en otro entorno, así que lo primero es verificar que importan y corren aquí.

```
src/relevo/dominio/objetos_valor/campo_extraido.py       CampoExtraido, EstadoCampo, Motivo, AjusteCatalogo
src/relevo/dominio/servicios/verificador_extraccion.py   el motor anti-error-silencioso
src/relevo/infraestructura/corpus/plantilla.py           plantilla + mapa de 41 campos
src/relevo/infraestructura/corpus/renderizador.py        escribe con fuentes manuscritas
src/relevo/infraestructura/corpus/degradacion.py         simula foto de celular
src/relevo/infraestructura/corpus/datos_ejemplo.py       pacientes sintéticos de relleno
src/relevo/infraestructura/llm/extractor.py              extracción SIN plantilla, prompt + parseo
src/relevo/infraestructura/llm/lector_ollama.py          LectorOllama, LectorNulo, autodetección
src/relevo/infraestructura/llm/lector_simulado.py        inyecta errores de OCR realistas
src/relevo/infraestructura/llm/catalogo_campos.py        campos + catálogos + validaciones
src/relevo/interfaz/cli/descargar_fuentes.py             18 fuentes de Google Fonts
src/relevo/interfaz/cli/generar_corpus.py                genera el corpus con su verdad
src/relevo/interfaz/cli/evaluar_corpus.py                corre el pipeline y reporta la métrica
tests/dominio/test_verificador_extraccion.py             18 tests, pasaban en el otro entorno
```

### La idea, en una línea

**No hay que leer mejor. Hay que hacer imposible estar mal en silencio.**

El verificador valida **valores, no posiciones**: por eso funciona con cualquier maquetado de documento, que es lo que hay en el INSN. La métrica del proyecto no es la exactitud: es la **tasa de error no detectado** — campos mal leídos que quedaron en verde. Objetivo: cero.

---

## 1. Verificación previa · bloqueante

```powershell
python -m pytest tests/ -q
python -m mypy --strict src/relevo/dominio/
```

**Esperado:** los 18 tests nuevos pasan y `test_arquitectura.py` sigue pasando. Si `mypy` se queja de los archivos nuevos, arreglar los tipos — no relajar la configuración.

**Punto de riesgo conocido:** `descargar_fuentes.carpeta_fuentes()` resuelve la raíz del proyecto con `Path(__file__).resolve().parents[4]`. Ese `4` asume el layout `src/relevo/interfaz/cli/`. **Verificar que apunta a la raíz del repo y corregir el índice si no.** Debe dar `<raíz>/assets/fuentes`.

---

## 2. Corpus

```powershell
python -m relevo.interfaz.cli.descargar_fuentes
python -m relevo.interfaz.cli.generar_corpus --n 120 --salida data/corpus
```

**Criterio de aceptación:** al menos 12 fuentes descargadas, y `data/corpus/` con 120 imágenes, 120 JSON de verdad y el manifiesto. Abrir dos o tres imágenes y confirmar que se lee la escritura.

**Añadir `assets/fuentes/` y `data/` a `.gitignore`** si no están ya. Las fuentes se descargan, no se versionan.

---

## 3. Medir el pipeline sin modelo · esto produce el número del pitch

```powershell
python -m relevo.interfaz.cli.evaluar_corpus --corpus data/corpus --json data/metricas.json
```

Usa `LectorSimulado`, que inyecta errores de OCR realistas sobre la verdad. **No necesita Ollama ni GPU.**

**Criterio de aceptación, y es el importante:**

> **`tasa de error no detectado` debe ser 0.00 % en los campos con catálogo o patrón** (dni, celular, fecha_nacimiento, cie10_*, especialidad, departamento, tipo_seguro, condición, establecimientos).

Si sale mayor que cero en alguno de esos campos, **hay un hueco en la validación y hay que encontrarlo antes de seguir.** Ese es el único número que el sistema promete.

En los campos de texto libre (`diagnostico_1`, `tratamiento`, nombres) va a haber error no detectado y **es esperado**: no tienen estructura contra la que validarse. Por eso `catalogo_campos.py` les pone `umbral_confianza=1.01`, que los fuerza a ámbar siempre. Confirmar que ese mecanismo funciona.

Guardar el resultado: es la lámina de la demo.

---

## 4. Pantalla de verificación · el entregable visual

Crear `src/relevo/interfaz/web/paginas/digitalizacion.py` e integrarla como pestaña en la app existente.

### Qué muestra

**Columna izquierda — el documento.** La imagen del corpus (o la que suba el usuario), con zoom.

**Columna derecha — los campos, en tres bloques y en este orden:**

1. **🔴 No legibles** — con el motivo. Campo de texto vacío para escribir a mano.
2. **🟠 Requieren revisión** — el valor propuesto, editable, y **el motivo en texto claro**. Si `fue_corregido`, mostrar *"se leyó 'E84.O'"* al lado. Botón de aceptar por campo.
3. **🟢 Validados** — plegados por defecto, en una sola línea. No se revisan; se muestran para que se pueda auditar si alguien quiere.

**Arriba, la barra de estado:**

```
18 campos · 12 validados · 4 a revisar · 2 no legibles · 3 corregidos por catálogo
```

**Abajo:** botón *"Confirmar y crear paciente"*, habilitado solo cuando no quedan rojos obligatorios (`reporte.utilizable`).

### Reglas de la pantalla

- **Solo se muestra lo que hay que tocar.** Los verdes plegados. Ese es el punto entero: un minuto revisando tres campos en vez de quince tipeando cuarenta.
- **Todo ámbar y todo rojo lleva su motivo escrito.** Decirle a alguien "revisa esto" sin decirle por qué lo obliga a revisar todo de nuevo. Usar `campo.explicacion()`.
- **Nunca ocultar que un valor fue corregido.** Si el catálogo cambió `E84.O` por `E84.0`, se ve.
- Selector de lector arriba: usar `elegir_lectores()` y mostrar cuál quedó activo. Si es `LectorNulo`, avisar en la interfaz: *"sin modelo — modo captura manual asistida"*, y que se note que **sigue siendo útil** porque la validación, el catálogo y la coherencia funcionan igual.

### Sobre el estilo

Que quede en la misma línea visual que el Radar. **No es una pantalla de demo: es la pantalla que alguien va a abrir un martes por la mañana.** Fea y funcional gana a bonita y vacía.

---

## 5. Conectar con el resto

Al confirmar la verificación, el documento tiene que convertirse en un paciente del sistema:

1. Mapear los campos verificados a la entidad `Paciente`
2. Guardarlo en `RepositorioPacientesMemoria`
3. Recalcular el IUT y que aparezca en el Radar

**Ese es el recorrido que se demuestra:** una foto de un formulario entra por un lado y sale un paciente priorizado con su desglose. Si eso funciona de punta a punta, la demo está.

Si el mapeo pide más campos de los que hoy extrae `catalogo_campos.py`, agregarlos ahí — con su `CampoPedido` **y** su `EspecificacionCampo`. **Nunca uno sin el otro:** pedir un campo y no validarlo es exactamente el agujero que este módulo existe para tapar.

---

## 6. Con Ollama · opcional, después de que 1–5 funcionen

```powershell
ollama serve
ollama pull glm-ocr
ollama pull qwen3-vl:4b
python -m relevo.interfaz.cli.evaluar_corpus --corpus data/corpus --ollama --limite 10
```

Empezar con `--limite 10`: un modelo de visión en CPU puede tardar minutos por documento.

**Comparar contra la corrida simulada.** Lo interesante no es cuál acierta más: es si la `tasa de error no detectado` sigue en cero. Si con modelo real sube, hay validaciones que faltan.

`elegir_lectores()` detecta solo lo que haya instalado y cae a `LectorNulo` si no hay nada. Modelos y VRAM recomendada en `docs/GUIA_OLLAMA.md`.

---

## 7. Lanzar

```powershell
streamlit run src/relevo/interfaz/web/app.py
```

Debe abrir en `localhost:8501` con la pestaña nueva funcionando **sin Ollama corriendo** — modo captura manual asistida. Que dependa del modelo para arrancar sería un fallo de diseño.

---

## 8. Verificación final

- [ ] `pytest` y `mypy --strict` limpios
- [ ] `test_arquitectura.py` pasa — el dominio sigue sin importar nada externo
- [ ] Corpus de 120 generado, imágenes legibles
- [ ] **`tasa de error no detectado` = 0.00 % en campos con catálogo o patrón**
- [ ] Los campos de texto libre siempre salen en ámbar
- [ ] La pantalla corre **con Ollama apagado**
- [ ] Un documento del corpus se recorre entero: imagen → verificación → paciente en el Radar con su IUT
- [ ] Las correcciones por catálogo se ven en pantalla, no se ocultan
- [ ] `assets/fuentes/` y `data/` fuera de git

---

## Lo que NO hay que hacer

| No | Por qué |
|---|---|
| Volver a la extracción por coordenadas | En el INSN no llega un solo formulario. El mapa de plantilla sirve para generar corpus, no para leer documentos reales. |
| Rellenar un campo que el modelo devolvió `null` | Un `null` es un campo a revisar. Un valor inventado es el error silencioso que este módulo existe para impedir. |
| Dejar que un campo de texto libre salga en verde | No tiene estructura contra la que validarse. Sin validación posible, no hay verde posible. |
| Bajar `umbral_confianza` para que salgan menos ámbares | La carga de revisión es el precio de no equivocarse en silencio. Se baja calibrando con el corpus, no a ojo. |
| Prometer "sin error" en la interfaz o en el pitch | No existe. La promesa es "ningún error pasa sin ser detectado", y esa sí se puede demostrar con un número. |
| Entrenar o afinar un modelo | No hay dato etiquetado en dominio y no hay tiempo. El catálogo cerrado da más precisión por infinitamente menos esfuerzo. |
| Mandar documentos a una API externa | Traen DNI, partida de nacimiento y afiliación al SIS. Es un problema legal, no de arquitectura. |

---

## Nota sobre la plantilla

`plantilla.py` dibuja una Hoja de Referencia **aproximada** — reproduce secciones, etiquetas y los 41 campos, no el diseño exacto. Sirve para generar corpus y calibrar.

**No se usa para leer.** La lectura es sin plantilla, por eso funciona con documentos de cualquier establecimiento. Si algún día se consigue el formulario oficial escaneado, se reemplaza la función de dibujo y el corpus mejora; nada más cambia.

Y hay que declararlo en el pitch: **la letra renderizada con fuente es más regular que la humana, así que la exactitud medida sobre este corpus es optimista.** Lo que el corpus valida honestamente es el pipeline, la detección de errores y la calibración de umbrales.
