# Guía de puesta en marcha — lectura de documentos con Ollama

**Todo gratis. Todo local. Ningún dato sale de la máquina.**

---

## Por qué local y no una API

No es solo el costo. Un escaneo de Hoja de Referencia trae DNI, partida de nacimiento, afiliación al SIS y el DNI del tutor. Mandar eso a un servicio externo deja de ser una decisión de arquitectura y pasa a ser un problema legal.

Y el volumen lo hace trivial: del orden de **un paciente por día hábil**, en proceso por lotes. Aunque cada documento tardara dos minutos, son unas **ocho horas de cómputo al año**.

---

## Paso 1 · Saber con qué hardware cuentas

```powershell
nvidia-smi
```

Mira la columna **Memory-Usage**: el número de la derecha es tu VRAM total. Si el comando no existe, no tienes GPU NVIDIA y vas por CPU (funciona, pero lento).

| VRAM | Principal | Contraste |
|---|---|---|
| Sin GPU | `minicpm-v4.6:1b` | `deepseek-ocr:3b` |
| 4 GB | `deepseek-ocr:3b` | `qwen3-vl:2b` |
| **8 GB** | **`glm-ocr`** | **`qwen3-vl:4b`** |
| 12 GB | `glm-ocr` | `qwen3-vl:8b` |
| 16 GB+ | `qwen3-vl:8b` | `minicpm-v4.5:8b` |

---

## Paso 2 · Descargar los modelos

Ya tienes Ollama instalado. Verifica y descarga:

```powershell
ollama --version
ollama serve          # si no está corriendo ya

# el par recomendado para 8 GB
ollama pull glm-ocr
ollama pull qwen3-vl:4b

# opcional pero interesante: modelo especializado en contenido médico
ollama pull medgemma:4b

ollama list           # confirma qué quedó descargado
```

**Si un tag no existe**, búscalo en `ollama.com/search?c=vision` — el catálogo cambia. El código elige automáticamente entre lo que encuentre instalado, así que no importa si te falta alguno.

### Qué es cada uno

| Modelo | Para qué |
|---|---|
| **`glm-ocr`** | OCR multimodal para documentos complejos. Es el especialista en transcripción literal. |
| **`deepseek-ocr:3b`** | OCR eficiente en tokens. Rápido y liviano. |
| **`qwen3-vl`** | Visión-lenguaje general. Fuerte siguiendo un esquema JSON. |
| **`minicpm-v4.5:8b`** | Sólido en documentos densos. |
| **`minicpm-v4.6:1b`** | El último recurso. Corre en casi cualquier máquina. |
| **`medgemma:4b`** | **Especializado en texto e imágenes médicas.** Para los campos clínicos de texto libre, donde el vocabulario importa. |

---

## Paso 3 · Probar que responde

```powershell
ollama run glm-ocr "describe esta imagen" --image ruta\a\una\hoja.jpg
```

Si contesta algo coherente, ya está listo.

---

## Paso 4 · Usarlo desde el proyecto

Si Ollama corre en otra máquina o detrás de un túnel, no hace falta tocar el código. Basta con exportar la variable de entorno que usa la app:

```powershell
$env:RELEVO_OLLAMA_HOST = "http://host-del-tunel:11434"
# por defecto, si no se setea, la app usa:
# http://localhost:11434
```

Y luego:

```python
from relevo.infraestructura.llm.extractor import CampoPedido, ExtractorDocumento
from relevo.infraestructura.llm.lector_ollama import elegir_lectores

principal, contraste = elegir_lectores()   # detecta solo lo que tengas instalado

extractor = ExtractorDocumento(
    campos=CAMPOS,
    lector_principal=principal,
    lector_contraste=contraste,
)
lectura, segunda = extractor.leer_imagen(Path("data/corpus/imagenes/hr_0001.jpg"))
```

Y de ahí al verificador, que es donde se impide el error silencioso:

```python
reporte = verificador.verificar(
    lecturas=lectura.valores,
    segunda_lectura=segunda.valores if segunda else None,
)
for campo in reporte.requieren_revision:
    print(campo.nombre, campo.explicacion())
```

**Si Ollama no está corriendo, `elegir_lectores()` devuelve `LectorNulo`** y todos los campos salen `null` → todos a revisión humana. El sistema no miente ni se rompe: entra en modo captura manual, y el resto del flujo (validación, catálogo, coherencia, priorización, Pasaporte, FHIR) sigue funcionando igual.

---

## La estrategia de los dos lectores

No es una pasada del mismo modelo dos veces: son **dos modelos distintos leyendo la misma imagen.**

```
glm-ocr      →  fuerte en transcripción literal
qwen3-vl:4b  →  fuerte siguiendo el esquema
```

Donde los dos coinciden hay **acuerdo independiente**. Donde discrepan, el campo va a ámbar.

Es exactamente la **doble digitación** que usan los servicios de transcripción profesionales para garantizar calidad — pero gratis, porque los dos modelos son locales. Y resuelve el problema de que los modelos locales no exponen probabilidades: la señal de confianza sale del desacuerdo.

---

## Cómo está escrito el prompt, y por qué

Cinco reglas absolutas, y todas apuntan al mismo sitio:

> **Si dudas entre dos lecturas posibles, devuelve `null`. Un `null` se revisa; un valor equivocado con aspecto correcto no se detecta.**

También:

- **Transcribe literalmente.** No corrijas ortografía, no completes abreviaturas. Corregir es trabajo del catálogo, que no alucina.
- **No calcules nada.** Si la edad no está escrita, es `null` aunque esté la fecha de nacimiento. Un valor calculado por el modelo rompería la validación cruzada, que es justamente la que detecta errores.
- **Las dosis se copian carácter por carácter.** Si un dígito no es legible, el campo entero es `null`.
- Y va incluido el **glosario de abreviaturas del INSN**, con `PC` marcado como ambiguo: *perímetro cefálico* o *parálisis cerebral* según el contexto, y si no se puede decidir, no se expande.

El parseo es defensivo: los modelos pequeños envuelven el JSON en explicaciones o bloques de código por mucho que se les prohíba. Se busca el primer objeto balanceado, y `"N/A"`, `"no legible"`, `"-"` y demás se tratan como `null`.

---

## Sobre que los documentos varían

Esto tumbó el enfoque de plantilla con coordenadas, y en el fondo lo simplificó.

En vez de preguntar *"¿qué dice el rectángulo (1300, 470, 340, 55)?"* — que depende del maquetado — se pregunta **"¿cuál es el DNI del paciente en este documento?"**, que no depende de nada. El modelo localiza el campo; nosotros solo exigimos el esquema de salida y el formato de cada campo.

**Y lo importante: `VerificadorExtraccion` no se entera.** Valida valores, no posiciones. Un DNI de siete dígitos es inválido venga de donde venga, y un CIE-10 fuera del catálogo no existe aunque el documento sea otro.

> La capa que impide el error silencioso es independiente del maquetado. Por eso sobrevivió intacta al cambio de enfoque.

Eso también es lo que hay que decir en el pitch: el sistema **no depende de que el hospital estandarice sus formularios.**

---

## Si todo falla el día de la demo

En orden de degradación, cada escalón sigue siendo un sistema útil:

1. **Dos modelos locales** → doble lectura con señal de confianza por desacuerdo
2. **Un modelo local** → lectura simple, sin esa señal, todo lo demás igual
3. **Sin modelo (`LectorNulo`)** → captura manual asistida: la pantalla de verificación se convierte en un formulario con validación de formato, ajuste a catálogo y coherencia cruzada en vivo

**Incluso el escalón 3 aporta valor real:** hoy en el INSN alguien tipea esos campos en REFCON sin ninguna validación. Con el escalón 3 los tipea con el catálogo CIE-10 corrigiéndole y la coherencia avisándole. Eso ya es mejor que el estado actual, y funciona sin GPU, sin internet y sin modelo.
