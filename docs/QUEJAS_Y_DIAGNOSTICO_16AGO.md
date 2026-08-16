# Quejas del usuario (16 ago 2026) y diagnóstico

**Contexto:** el usuario pasó el proyecto a Antigravity para continuar C6 (autenticación, FHIR). Antigravity añadió login con argon2id, sesión de servidor y un exportador FHIR CorePE. Al probar `localhost:8000` después de esos cambios, encontró varios problemas. Este documento tiene dos partes: **1)** la queja copiada tal cual la escribió, **2)** mi diagnóstico de causa raíz para cada punto, investigado sobre el código actual en la rama `fusion/entrenate-receptor`, para que Sonnet 5 no tenga que redescubrirlo.

---

## 1 · La queja, copiada literal

> ok usé mis créditos para antigravity, sé que añadió seguridad supuestamente y algunos detalles más, pero sigue el mismo error desde que tú me entregaste el proyecto para pasarselo a antigravity y acá lo describo. que sigue incompleto el localhost:8000 cuando estoy en paciente me manda a "elige un rol primero", no me muestra nada. Cuando esto en "apoderado" tampoco me muestra algo concreto, me dice que elija un rol primero. Cuando estoy como Profesional INSN me sale el corte etario..., qué es etario? había quedado contigo en sesiones pasadas que el software era amigable ante el público porque era usado por médicas/enfermeras jóvenes, adultos y muy adultos que no tienen mucho roce con tecnologías y tampoco necesariamente tiene un conocimiento léxico amplio, por lo que debe ser entendible, la diferencia de columnas en una tabla debe estar marcada por líneas, no tan fuerte, pero al menos que se note visiblemente y con facilidad la división de celdas. Ahora, cuando paso entre secciones, SIMPLEMENTE los botones no se activan (me refiero a cuando tengo rol de INSN y creo que también del receptor no funciona sus botones) No puedo cambiar entre secciones, simplemente los botones no se activan para "Requiere acción del INSN", "Esperando al receptor", "Sin destino asegurado". También en donde está la parte de digitalización de historias clínicas? Yo usaba un modelo de Ollama para hacer OCR de archivos a archivos que generé artificialmente. El código seguro sigue por ahí en el proyecto, pero no lo has terminado de integrar. Otro gran error es que no estás poniendo ninguna tilde, estas evitando usar la 'ñ', mejora tu escritura y rectifica que todos los botones funcionen.

**Nota importante del usuario:** dice que este mismo error "viene desde que [Claude Code] le entregó el proyecto", es decir, los botones muertos y las tildes faltantes **ya estaban rotos en la entrega original de Claude Code (commits C0–C6 antes de Antigravity)**, no son algo que Antigravity introdujo. Antigravity los heredó y no los arregló al añadir autenticación/FHIR.

---

## 2 · Diagnóstico, punto por punto

### 2.1 · "Los botones no se activan" — radar, receptor, y selección de rol

**Causa raíz encontrada: una condición de carrera de microtareas en `app.js`.**

En `src/relevo/interfaz/web/estatico/js/app.js`:

```js
VISTAS.forEach(([patron, modulo]) => {
  registrar(patron, async (parametros) => {
    const html = await modulo.render(parametros);
    if (modulo.enganchar) {
      queueMicrotask(() => modulo.enganchar(app, repintar));
    }
    return html;
  });
});
```

Y en `enrutador.js`:

```js
const html = await encontrada.render(encontrada.parametros);
contenedor.innerHTML = html;               // el HTML se pinta AQUI
contenedor.querySelectorAll("[data-ir]")…  // solo engancha los data-ir genericos
```

El orden real de ejecución de microtareas es:

1. Dentro del wrapper de `app.js`, se llama `queueMicrotask(() => modulo.enganchar(...))` — esto encola el trabajo de enganchar **antes** de que la función `return html;` dispare la resolución de la promesa que `enrutador.js` está esperando.
2. Esa resolución (el `return html`) encola la continuación de `pintar()` en `enrutador.js` **después** del trabajo que se acaba de encolar en el paso 1.
3. Como las microtareas se procesan en orden FIFO, **`enganchar()` se ejecuta antes de que `contenedor.innerHTML = html` se haya asignado.**

Consecuencia: `modulo.enganchar(app, repintar)` hace `contenedor.querySelectorAll(...)` sobre el HTML **viejo** (o el `"Cargando…"` de transición), no encuentra los botones nuevos, y no les engancha ningún `addEventListener`. Los botones existen visualmente (porque el HTML sí se pinta un instante después) pero **nunca tienen manejador de clic.**

Esto explica de una sola vez:

- Los filtros del radar (`Requiere acción del INSN`, `Esperando al receptor`, `Sin destino asegurado`, `Completadas`) no responden — es `radar.js::enganchar()`.
- Los botones de acción del receptor no responden — es `bandeja.js::enganchar()`.
- Muy probablemente también: las tarjetas de selección de rol en `entrar.js::enganchar()` no disparan `fijarRol()` / `fijarPaciente()` / `ir()` al hacer clic, así que el usuario nunca navega ni fija un paciente en memoria — lo que a su vez explica el punto 2.2 de abajo.

**Dónde arreglarlo:** en `app.js` o en `enrutador.js`. La forma más simple y robusta: que el router (`enrutador.js`) sea quien llame a `enganchar()`, **después** de asignar `innerHTML`, en vez de que cada vista se auto-enganche con `queueMicrotask` desde dentro de su wrapper. Por ejemplo, que `render()` devuelva `{ html, enganchar }` en vez de solo `html`, y que `pintar()` en `enrutador.js` haga:

```js
const { html, enganchar } = await encontrada.render(encontrada.parametros);
contenedor.innerHTML = html;
contenedor.querySelectorAll("[data-ir]").forEach(...);
if (enganchar) enganchar(contenedor, repintar);   // AHORA sí, después de innerHTML
```

Esto elimina la carrera por completo: ya no depende del orden de microtareas, es secuencial y explícito.

**Verificación sugerida:** un test de humo en Playwright/Selenium (si se añade), o al menos una prueba manual explícita: cargar `#/insn/radar`, hacer clic en un filtro, comprobar que `tr[hidden]` cambia. Hoy no hay ningún test de frontend que ejercite clics reales — los tests de `tests/interfaz/` prueban la API, no el DOM — así que este bug pasó desapercibido en la suite.

---

### 2.2 · "En paciente/apoderado me manda a 'elige un rol primero'"

Consecuencia directa de 2.1: si el clic en la tarjeta de rol de `entrar.js` nunca se enganchó, entonces `fijarPaciente("DEMO-0001")` nunca se llamó, `pacienteActual()` sigue siendo `null`, y las vistas `paciente.js`, `ruta.js`, `entrenate.js`, `leccion.js` — que todas empiezan con:

```js
const id = pacienteActual();
if (!id) return '<section class="tarjeta"><p>Elige un rol primero.</p></section>';
```

— devuelven ese mensaje aunque el usuario ya haya "seleccionado" un rol visualmente (el clic no hizo nada). **Arreglar 2.1 arregla esto automáticamente.** No hace falta tocar `estado.js` ni las vistas.

Verificar después del fix: entrar por `#/entrar`, clic en "Paciente", confirmar que `estado.pacienteId === "DEMO-0001"` (se puede loguear temporalmente) y que la URL cambia a `#/paciente`.

---

### 2.3 · "¿Qué es 'corte etario'? Necesito lenguaje llano"

Esto es una queja de **legibilidad para un público no técnico**: médicas/enfermeras jóvenes, adultas y muy adultas, sin roce con tecnología ni vocabulario administrativo. El proyecto ya tiene un principio equivalente para el paciente (`etiqueta_llana` en el dominio, "Tu nuevo hospital está revisando tu información" en vez de `EN_EVALUACION`), pero **no se aplicó ese mismo cuidado a la vista del profesional del INSN**.

"Corte etario" es jerga interna del equipo (viene de `dominio/servicios/corte_etario.py`) y llegó tal cual a la interfaz en `radar.js`:

```js
function cabeceraCorteEtario(corte) {
  return `
    <div class="corte-etario">
      <h1>Corte etario</h1>
      ...
```

**Sugerencia de redacción** (a decidir con el usuario, no soy quien firma el texto final):
- Título: algo como **"Pacientes en riesgo de quedarse sin hospital"** o **"Alerta: cumplen 18 sin destino"**, en vez de "Corte etario".
- Mantener "corte etario" como subtítulo técnico entre paréntesis si se quiere preservar precisión clínica, pero el titular grande tiene que decir la consecuencia humana, no el nombre del mecanismo.
- Lo mismo aplica a otros tecnicismos que aparecen sin traducir: "IUT", "responsable" (¿de qué?), "situación_plazo: vencido/por_vencer/en_plazo" (esto en particular sale literal del backend en algunas etiquetas — revisar que **todas** las etiquetas que llegan a pantalla pasen por el campo `_etiqueta` del dominio y no el `.value` crudo del enum).

**Dónde tocar:** `src/relevo/interfaz/web/estatico/js/vistas/radar.js` (función `cabeceraCorteEtario`) y `src/relevo/interfaz/web/estatico/js/vistas/bandeja.js`. Posiblemente también revisar `src/relevo/dominio/servicios/corte_etario.py::MetricaCorteEtario.titular()`, que es la fuente del texto que la API expone en `titular` — si se traduce ahí, se traduce en todos los consumidores a la vez (API, radar, futura barra de resumen).

---

### 2.4 · "Las columnas de la tabla necesitan líneas visibles, no tan fuertes"

Confirmado mirando `src/relevo/interfaz/web/estatico/css/vistas.css`, la tabla del radar (`.tabla-radar`):

```css
.tabla-radar th,
.tabla-radar td {
  text-align: left;
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--borde);   /* solo linea HORIZONTAL */
  vertical-align: top;
}
```

Solo hay `border-bottom`. **No hay separación vertical entre columnas**, así que en una tabla ancha (6 columnas: Paciente, Edad, Prioridad, Etapa, Turno, Corte) las celdas se leen corridas, sobre todo para alguien sin costumbre de leer tablas densas.

**Fix concreto:** añadir un borde vertical suave entre celdas, por ejemplo:

```css
.tabla-radar th,
.tabla-radar td {
  border-right: 1px solid var(--borde);
}
.tabla-radar th:last-child,
.tabla-radar td:last-child {
  border-right: none;
}
```

Usar el mismo tono `var(--borde)` que ya se usa para el borde horizontal (`#d8e0e8` en `base.css`), para que sea "notorio pero no fuerte", tal como lo pidió el usuario — no un color contrastante nuevo.

---

### 2.5 · "¿Dónde está la digitalización de historias clínicas / OCR con Ollama?"

**No está perdido — nunca se integró al frontend nuevo, por una decisión de diseño explícita del documento de fusión (§7.5) que quizás no se le comunicó bien al usuario.**

Verificado: el flujo de digitalización (`DigitalizarDocumento`, `ConfirmarDigitalizacion`, el lector Ollama, `acta_digitalizacion.py`) sigue existiendo intacto en `src/relevo/aplicacion/digitalizar_documento.py` y está expuesto **solo en Streamlit** (`src/relevo/interfaz/web/app.py`), no hay ningún endpoint FastAPI ni vista `.js` que lo llame. `contenedor.digitalizar` y `contenedor.confirmar` existen en `arranque.py` pero ningún router de `interfaz/api/` los usa.

La instrucción original (`FUSION_RELEVO_INSTRUCCIONES.md §7.5`) decía explícitamente:

> Streamlit se queda como consola técnica — no es el producto. Reenfócalo a lo que ya hace bien: digitalización con verificador, generación y evaluación de corpus, métricas del extractor, inspección de la cadena de auditoría.

Es decir: el plan original era que el OCR se siguiera usando desde `streamlit run src/relevo/interfaz/web/app.py` (otro puerto, típicamente 8501), **no** desde `localhost:8000`. Pero el usuario claramente espera verlo en el mismo lugar donde ve todo lo demás, y es una queja legítima de experiencia de usuario: tener que saltar a otro proceso/puerto para digitalizar un documento es fricción real para el personal del hospital.

**Dos caminos, a decidir con el usuario (no es una decisión técnica pura):**
1. **Mantener la separación** (como dice el documento original) pero dejarlo muy claro en la interfaz: un enlace/botón visible en `localhost:8000` que diga "Digitalizar un documento nuevo → abre la consola técnica (Streamlit)" con la URL, para que no parezca "perdido".
2. **Traer el flujo de digitalización al producto nuevo**: un router `rutas_digitalizacion.py` en `interfaz/api/` que use los casos de uso ya existentes (`contenedor.digitalizar`, `contenedor.confirmar`), y una vista `.js` nueva (`#/insn/digitalizar`) para el profesional del INSN. Esto es más trabajo pero resuelve la queja de raíz.

Dado que el usuario ya expresó insatisfacción con la separación, **probablemente prefiere la opción 2**, pero hay que confirmarlo — es un cambio de alcance, no un bug.

---

### 2.6 · "No estás poniendo tildes, evitas la 'ñ' — mejora tu escritura"

Confirmado y es un fallo real, no una regla del proyecto mal aplicada. `CLAUDE.md` dice:

> Identificadores y comentarios en español, **sin tildes ni ñ en identificadores**.

Esa regla es explícitamente para **identificadores de código** (nombres de variables, funciones, archivos) — así el proyecto es compatible con sistemas de archivos y linters que no manejan bien Unicode en nombres. **Nunca fue la intención que se extendiera al texto que lee una persona en pantalla.** De hecho `docs/CIERRE_MVP.md` (T2, el acta del PDF) lo dice explícitamente: *"la regla de CLAUDE.md de no usar tildes es para identificadores, no para lo que lee un médico."* Ese mismo criterio no se aplicó de forma consistente al frontend nuevo.

Evidencia en el código actual (`grep` sobre `src/relevo/interfaz/web/estatico/js/vistas/`):

```
"anios" en vez de "años"          (entrar.js, paciente.js, pasaporte.js, ruta.js, bandeja.js)
"Que tengo" en vez de "Qué tengo" (pasaporte.js)
"Que tomo" en vez de "Qué tomo"   (pasaporte.js)
"Elige un rol primero"            (correcto, sin problema aqui)
```

Y es sistemático: casi todos los literales de texto en `estatico/js/vistas/*.js` y en las etiquetas que arma el dominio (`etiqueta`, `etiqueta_llana` en varios `objetos_valor/*.py`) están escritos sin tildes ni eñes.

**Alcance del arreglo — es grande, no es un `find & replace` trivial:**
- Todo el texto de usuario en `src/relevo/interfaz/web/estatico/js/vistas/*.js` y `src/relevo/interfaz/web/estatico/js/componentes/*.js` (literales de plantilla).
- Todas las propiedades `etiqueta` / `etiqueta_llana` / `.etiqueta` de los enums de dominio que llegan a pantalla: `EstadoCiclo`, `Responsable`, `EstadoHabilidad`, `EstadoConciliacion`, `MotivoReingreso`, `BaseLegalAcceso`, `TipoDiscrepancia`, etc. — repartidos por `dominio/objetos_valor/` y `dominio/entidades/`.
- El contenido de `config/lecciones_entrenate.yaml` (la lección 6 completa) — revisar si ya lleva tildes correctas (sí las lleva, fue escrita con cuidado) o si se degradó en algún punto.
- Los mensajes de error de la API (`HTTPException(...)` en `interfaz/api/rutas_*.py`).

**Importante para quien lo arregle:** el archivo debe guardarse en **UTF-8** en todos los casos (Python ya lo hace por defecto; verificar que el editor/herramienta que use Sonnet 5 no reintroduzca ASCII al escribir). No cambiar ningún **identificador** (nombre de variable, función, clase, endpoint, clave de enum) — solo el texto que un humano lee: strings literales, docstrings orientados a persona, y los diccionarios `_ETIQUETAS` de cada enum.

---

## 3 · Prioridad sugerida

| # | Punto | Por qué primero |
|---|---|---|
| 1 | **2.1 — condición de carrera en `app.js`/`enrutador.js`** | Es la causa raíz de 2.1 y 2.2 a la vez. Arreglar esto solo ya destraba "no puedo hacer nada en la interfaz", que es el bloqueo más grave. |
| 2 | **2.6 — tildes y eñes** | Barrido mecánico pero extenso; conviene hacerlo antes de que se agreguen más vistas nuevas (digitalización, si se decide la opción 2 de 2.5) para no tener que repetirlo. |
| 3 | **2.4 — bordes de columna** | Cambio de CSS, bajo riesgo, dos minutos. |
| 4 | **2.3 — lenguaje llano en el radar del profesional** | Requiere criterio de redacción, no solo código — conviene decidir el texto final con el usuario antes de tocar el código. |
| 5 | **2.5 — digitalización/OCR** | Es una decisión de alcance (opción 1 vs 2), no un bug puntual — preguntarle al usuario cuál prefiere antes de construir. |

---

## 4 · Lo que Antigravity sí añadió y funciona (para no perder ese trabajo)

Verificado en el código actual, para que quede claro que no todo retrocedió:

- **Autenticación real**: `src/relevo/interfaz/api/autenticacion.py` — argon2id, `GestorAutenticacion`, usuarios de demo precargados (`paciente_mateo`, `apoderado_rosa`, `dra_valdez`, `dr_mendoza`, `admin`), cookie de sesión de servidor.
- **Endpoints de auth**: `src/relevo/interfaz/api/rutas_auth.py` (`/api/auth/login`, `/api/auth/logout`, `/api/auth/sesion`).
- **Exportador FHIR CorePE**: `src/relevo/infraestructura/interoperabilidad/fhir_corepe.py` (306 líneas) y el endpoint `GET /api/pacientes/{id}/fhir` en `rutas_insn.py`, con botón "Exportar HL7 FHIR CorePE (MINSA)" ya en `pasaporte.js`.

Esto es avance real hacia C6/C7. **No conviene revertirlo** al arreglar los puntos de arriba.

**Confirmado, y es importante:** `entrar.js` engancha el login de la misma forma que las demás vistas —

```js
export function enganchar(contenedor) {
  ... boton.addEventListener("click", async () => { await login(...); ...
```

— así que **el login también sufre la condición de carrera del punto 2.1.** Es casi seguro que los botones de usuario de demo en la pantalla de entrada tampoco responden a clics hoy, por la misma causa raíz. Arreglar 2.1 debería destrabar el login a la vez que el resto.

---

## 5 · Comando para cambiar de modelo

El usuario preguntó por el comando para cambiar de modelo: es **`/model`**. Se escribe solo, sin argumentos, y abre un selector.
