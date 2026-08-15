# Despliegue en Streamlit Community Cloud

Cómo queda la aplicación publicada para que el equipo la vea sin instalar nada,
y cómo hacer que el modelo de lectura funcione **en vivo** desde esa URL.

---

## 1. Lo que ya está configurado en el repositorio

| Archivo | Para qué |
|---|---|
| `requirements.txt` | Lo único que Streamlit Cloud instala. Solo lo que el adaptador web importa de verdad. |
| `.streamlit/config.toml` | Tema claro fijo. Sin esto, quien abra la página con el sistema en modo oscuro ve las tarjetas rotas. |
| `data/corpus_demo/` | 4 documentos sintéticos con su transcripción, versionados a propósito (ver §3). |

**Configuración de la app en share.streamlit.io:**

- **Repository:** `ticket267speedy/Avellana`
- **Branch:** `main` (o `mvp-completo` — a partir del merge de 15-ago-2026 apuntan al mismo commit)
- **Main file path:** `src/relevo/interfaz/web/app.py`
- **Python version:** 3.12 o superior (`pyproject.toml` declara `requires-python = ">=3.12"`)

---

## 2. Por qué el modelo NO puede correr en la nube

Conviene entenderlo antes de intentar arreglarlo por el camino equivocado.

El lector es `qwen3-vl:4b`, un modelo de visión de 4 mil millones de parámetros
servido por Ollama. Streamlit Community Cloud da unos pocos GB de RAM y **cero
GPU**. El modelo no entra, y aunque entrara, `TIMEOUT_SEGUNDOS = 300` en
`lector_ollama.py` ya reconoce que en CPU tarda minutos por documento.

Instalar Ollama dentro del contenedor de Streamlit no es una opción, y no hay
servidor gratuito donde alojarlo. **Esto no es un fallo de configuración: es una
restricción de hardware.**

Sin hacer nada más, la app desplegada:

- ✅ funciona entera: semáforo, priorización, Pasaporte en PDF, destino, avisos;
- ✅ muestra la pestaña de digitalización con las transcripciones ya producidas
  por el modelo y guardadas en disco;
- ❌ no puede transcribir un documento nuevo en el momento.

La sección siguiente resuelve ese último punto.

---

## 3. La muestra versionada del corpus

El corpus completo son 12 documentos (~9 MB) que genera
`python -m relevo.interfaz.cli.generar_corpus --n 12`. No se versiona: son datos
reconstruibles con un comando y el repositorio no es sitio para eso.

Pero en Streamlit Cloud **nadie puede correr ese comando**, y sin documentos la
pestaña de digitalización sale vacía justo en el despliegue que mira el equipo.
Por eso `data/corpus_demo/` sí está versionado: 4 de esos documentos (2.8 MB)
cubriendo las tres variantes de degradación, con las transcripciones **reales**
que produjo el modelo en local.

`.gitignore` tiene una excepción explícita y comentada para ese único
directorio. **No viola la regla 1 de `CLAUDE.md`:** lo que esa regla prohíbe es
dato real de paciente, y estos documentos son sintéticos, generados por el
propio sistema, sin correspondencia con persona alguna.

`CorpusEnArchivos.descubrir()` prefiere el corpus completo cuando existe, así
que en local sigues viendo tus 12 documentos; la muestra solo aparece donde no
hay nada más. Cuando se usa la muestra, la pantalla **lo dice en voz alta**.

---

## 4. Modelo en vivo desde la URL pública (túnel)

Para que el equipo vea el modelo transcribiendo **en directo** desde la app
desplegada, se expone el Ollama que ya corre en tu máquina y se le dice a la app
dónde encontrarlo. Es gratis y no requiere servidor.

```
Streamlit Cloud  ──HTTPS──►  túnel Cloudflare  ──►  tu PC: Ollama + qwen3-vl:4b
```

### Paso 1 — Arrancar Ollama abierto al túnel

Ollama por defecto solo escucha en `127.0.0.1` y **rechaza peticiones cuya
cabecera `Host` no reconoce**. Un túnel las manda con el dominio del túnel, así
que sin estas dos variables devuelve `403` y parecerá que no está corriendo.

En PowerShell, **en la ventana donde vas a arrancar Ollama**:

```powershell
$env:OLLAMA_HOST = "0.0.0.0:11434"
$env:OLLAMA_ORIGINS = "*"
ollama serve
```

Comprueba que el modelo está descargado, en otra ventana:

```powershell
ollama list      # debe aparecer qwen3-vl:4b
```

### Paso 2 — Levantar el túnel

Sin cuenta ni registro:

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:11434
```

Imprime una URL del tipo:

```
https://algo-aleatorio-aqui.trycloudflare.com
```

Cópiala. **Deja esa ventana abierta**: si la cierras, el túnel muere.

### Paso 3 — Declararla en los secretos de la app

En `share.streamlit.io` → tu app → **Settings** → **Secrets**, pega:

```toml
RELEVO_OLLAMA_HOST = "https://algo-aleatorio-aqui.trycloudflare.com"
```

Guarda. La app se reinicia sola en unos segundos.

### Paso 4 — Comprobar

Abre la app, pestaña **Digitalización**. Arriba debe decir:

> **Modelo en vivo:** `ollama/qwen3-vl:4b` — ejecutándose en una máquina del
> equipo, alcanzada en `https://…trycloudflare.com`

Pulsa **"Volver a leer en vivo con el modelo"** en cualquier documento. Tarda un
par de minutos: es el modelo transcribiendo de verdad en tu máquina.

---

## 5. Lo que hay que saber del túnel

**La URL cambia cada vez.** Un túnel rápido de Cloudflare genera un dominio
nuevo en cada arranque. Si reinicias el túnel, hay que actualizar el secreto.

**Depende de tu máquina.** Si la apagas, la suspendes o cierras la ventana del
túnel, la app vuelve sola al modo de transcripciones guardadas y lo dice en
pantalla. No se rompe nada, pero tampoco hay lectura en vivo.

**Mientras el túnel está arriba, tu Ollama es alcanzable desde internet.** La
URL es aleatoria y no está indexada, pero es pública: cualquiera que la tenga
puede mandarle trabajo. Aquí solo pasan documentos sintéticos, así que el riesgo
es de consumo de tu CPU, no de datos. Aun así, **cierra el túnel cuando termines
la demo** (Ctrl+C en esa ventana).

**Esto es solo para la demo.** En un despliegue real dentro del INSN, Ollama
corre en la red de la institución y no hace falta ningún túnel — que es
justamente el argumento del proyecto: los datos clínicos del MINSA no pueden
salir a un servicio externo.

---

## 6. Si algo falla

| Síntoma | Causa probable |
|---|---|
| "Sin modelo alcanzable" con el túnel arriba | Falta `OLLAMA_ORIGINS=*`. Ollama responde 403 al Host del túnel. |
| "Sin modelo alcanzable" y `ollama list` funciona | Falta `OLLAMA_HOST=0.0.0.0:11434`. Solo escucha en localhost. |
| Sigue igual tras cambiar el secreto | Reinicia la app desde el menú de Streamlit Cloud (*Reboot app*). |
| La pestaña de digitalización sale vacía | No se subió `data/corpus_demo/`. Comprueba la excepción del `.gitignore`. |
| El despliegue no toma los cambios | La app apunta a otra rama. `main` y `mvp-completo` están al mismo commit desde el 15-ago-2026. |
| La página se ve rota, tarjetas blancas sobre negro | Falta `.streamlit/config.toml` en la rama desplegada. |
