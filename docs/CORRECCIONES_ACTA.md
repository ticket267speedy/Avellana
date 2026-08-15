# Correcciones — acta de digitalización y catálogo de establecimientos

Cuatro cosas. La segunda es la importante y no se ve a simple vista.

---

## 🔴 C1 — El texto se desborda de la celda en el PDF

**Síntoma:** en `establecimiento_destino`, el valor `"INSTITUTO NACIONAL DE SALUD NIÑO SAN BORJA"` se sale de su columna y se pinta encima de `"INSN San Borja"` de la columna siguiente. Ilegible, y en un documento firmable es inaceptable.

**Causa:** las celdas de la tabla reciben **cadenas planas**. ReportLab no ajusta líneas en un `str`: lo dibuja en una sola línea y lo deja salir de la celda.

**Cambio — en el generador del acta (`infraestructura/documentos/`):**

```python
# ANTES — cadenas planas, no ajustan
filas.append([campo.nombre, campo.valor, campo.valor_crudo or "—", origen])

# DESPUES — Paragraph, que sí ajusta dentro del ancho de columna
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT

_CELDA = ParagraphStyle(
    "celda",
    fontName="Helvetica",
    fontSize=8.5,
    leading=10.5,          # interlineado: sin esto las lineas se pisan
    alignment=TA_LEFT,
    wordWrap="CJK",        # parte tambien dentro de palabras muy largas
)

def _celda(texto: str | None) -> Paragraph:
    return Paragraph(escape(str(texto or "—")), _CELDA)

filas.append([
    _celda(campo.nombre),
    _celda(campo.valor),
    _celda(campo.valor_crudo),
    _celda(origen),
])
```

**Y fijar los anchos de columna explícitamente.** Sin `colWidths`, ReportLab reparte a ojo:

```python
from reportlab.lib.units import mm

ANCHO_UTIL = 170 * mm          # A4 (210 mm) menos 20 mm de margen por lado
tabla = Table(
    filas,
    colWidths=[38*mm, 55*mm, 50*mm, 27*mm],   # suma 170 mm
    repeatRows=1,                              # la cabecera se repite al pasar de pagina
)
```

**Importante:** `escape()` de `html` es obligatorio. Un valor leído por OCR puede traer `&` o `<`, y ReportLab interpreta el contenido de `Paragraph` como marcado — reventaría el PDF con datos reales.

**Criterio de aceptación:** un establecimiento con nombre de 60 caracteres se parte en dos o tres líneas dentro de su celda y la fila crece de alto. Nada invade la columna vecina.

---

## 🔴 C2 — El corpus y el catálogo están desincronizados

Esto es lo grave, y explica por qué `"Hospital Regional de Ucayali"` "no existía".

**Lo que pasó:** el catálogo de establecimientos ahora viene de una fuente real (la API que se conectó). Pero el corpus sintético se sigue generando con la lista **inventada** que puse en `infraestructura/corpus/datos_ejemplo.py`:

```python
ESTABLECIMIENTOS = (
    "Hospital Regional de Ucayali",     # ← no existe en el registro oficial
    "Hospital Regional de Loreto",      # ← probablemente tampoco
    ...
)
```

Yo inventé esos nombres antes de que hubiera catálogo real. No son nombres oficiales.

**La consecuencia es peor que un campo raro:** si el corpus escribe nombres que no están en el catálogo, **todos los documentos fallan la validación de establecimiento**, y la métrica de error no detectado queda contaminada. Los números que midas no valen.

**Cambio — una sola fuente de verdad:**

```python
# infraestructura/corpus/datos_ejemplo.py
# BORRAR la constante ESTABLECIMIENTOS de este archivo.

from relevo.infraestructura.llm.catalogo_campos import establecimientos

def valores_de_ejemplo(rnd):
    catalogo = establecimientos()      # el MISMO que usa el validador
    ...
    "establecimiento_origen": rnd.choice(catalogo),
    "establecimiento_destino": "INSN San Borja",   # ← con su nombre OFICIAL exacto
```

Y lo mismo con `DEPARTAMENTOS`, `ESPECIALIDADES` y los códigos CIE-10: **si el validador lo valida contra un catálogo, el generador tiene que sortear de ese mismo catálogo.** Cualquier otra cosa mide el desajuste entre dos listas, no la calidad de la lectura.

**Añadir un test que lo impida:**

```python
# tests/infraestructura/test_coherencia_corpus_catalogo.py
def test_todo_valor_generado_existe_en_su_catalogo():
    """Si el corpus escribe valores fuera de catalogo, la metrica no vale nada."""
    specs = especificaciones()
    for semilla in range(200):
        valores = valores_de_ejemplo(random.Random(semilla))
        for nombre, valor in valores.items():
            spec = specs.get(nombre)
            if spec and spec.catalogo:
                assert valor in spec.catalogo, (
                    f"El generador produjo '{valor}' para '{nombre}', "
                    f"que no esta en su catalogo. La medicion quedaria falseada."
                )
```

**Bonus:** verificar cómo se llama de verdad el hospital de Ucayali en el registro oficial. Si el nombre real es `"HOSPITAL REGIONAL DE PUCALLPA"` o similar, ese es el que va — y de paso confirma que la conexión a la fuente real fue una buena decisión.

---

## 🟠 C3 — Los campos con catálogo no deben corregirse escribiendo

**Síntoma real detrás de "no me lo ofreció":** el campo se corrigió con una **caja de texto libre**. Si el usuario tiene que teclear el nombre del establecimiento, puede escribir uno que no existe — y acabamos de meter a mano el error que el sistema existe para impedir.

**Regla:** un campo que tiene catálogo cerrado **no se corrige escribiendo. Se corrige eligiendo.**

```python
# En la pantalla de verificacion, para cada campo:
spec = especificaciones()[campo.nombre]

if spec.catalogo:
    # Desplegable con busqueda. No se puede elegir algo inexistente.
    opciones = list(spec.catalogo)
    indice = opciones.index(campo.valor) if campo.valor in opciones else None
    valor = st.selectbox(
        spec.etiqueta,
        opciones,
        index=indice,
        placeholder="Buscar…",
        help=campo.explicacion(),
    )
else:
    # Solo los campos sin catalogo admiten texto libre
    valor = st.text_input(spec.etiqueta, value=campo.valor or "", help=campo.explicacion())
```

Con eso el catálogo protege igual al humano que al modelo, y la queja *"no me lo ofreció"* se convierte en información útil: si un establecimiento real no aparece en el desplegable, **falta en el catálogo** y hay que agregarlo a la fuente — no escribirlo a mano en un caso suelto.

Añadir debajo del desplegable: *"¿No aparece? Reportar establecimiento faltante"*, que lo registre en un log. Ese log es exactamente lo que hay que llevarle al mentor.

---

## 🟡 C4 — Acentos en el texto que ve el usuario

En el acta se lee *"Acta de Digitalizacion Asistida"*, *"Instituto Nacional de Salud del Nino San Borja"*, *"LECTURA AUTOMATICA"*.

La regla de `CLAUDE.md` es **sin tildes ni ñ en identificadores** — nombres de variables, funciones, claves. **No aplica al texto que se muestra.** Un documento que un médico va a firmar y que dice "Nino" en vez de "Niño" se ve descuidado, y en el nombre de la institución es directamente un error.

**Cambio:** todas las cadenas visibles al usuario con su ortografía correcta.

```python
# ANTES
TITULO = "Acta de Digitalizacion Asistida"
INSTITUCION = "Instituto Nacional de Salud del Nino San Borja"
COLUMNAS = ["CAMPO", "VALOR VALIDADO", "LECTURA AUTOMATICA", "ORIGEN"]

# DESPUES
TITULO = "Acta de Digitalización Asistida"
INSTITUCION = "Instituto Nacional de Salud del Niño San Borja"
COLUMNAS = ["Campo", "Valor validado", "Lectura automática", "Origen"]
```

Y verificar que la fuente del PDF tiene el glifo `ñ`. Las Type-1 base de ReportLab (`Helvetica`) sí lo tienen con `encoding='WinAnsiEncoding'`, pero si se registró una TTF hay que asegurarse de que trae el latino completo. **Prueba concreta:** generar un acta con `establecimiento = "INSN San Borja"` y `apellido = "Muñoz"` y confirmar que la ñ sale bien en las dos.

*(Los identificadores en código se quedan como están: `establecimiento_destino`, `apellido_paterno`. Esa parte de la regla sigue en pie.)*

---

## 🟢 Lo que quedó bien y conviene reforzar

**El Acta de Digitalización Asistida es un acierto.** No estaba en el plan y es exactamente lo que faltaba: convierte una corrección automática en un acto documentado y firmado. Dos refuerzos:

1. **La columna "Lectura automática" es el corazón del acta** — nunca omitirla ni resumirla. Es lo único que permite auditar después si una corrección fue razonable. Cuando el OCR devolvió `null`, que diga *"no legible"* en vez de `—`: son cosas distintas y el guion se lee como "no aplica".

2. **Registrar también qué modelo leyó.** Una línea en el pie: *"Lectura automática: ollama/glm-ocr · 15/08/2026 01:20"*. Sin eso, dentro de seis meses nadie sabrá con qué se leyó ese documento.

El pie de página ya dice lo correcto — que no reemplaza a la Hoja de Referencia original. Mantenerlo.

---

## Sobre la base de datos

**Para el MVP: SQLite, y no hace falta más.**

- Cero costo, cero servidor, cero configuración. Es un archivo.
- El puerto `RepositorioPacientes` ya está definido, y hoy corre `RepositorioPacientesMemoria`. Pasar a SQLite es **escribir un adaptador nuevo**; nada más del sistema se entera. Es exactamente para esto que se eligió la arquitectura hexagonal.
- Un hospital puede desplegarlo sin pedirle nada a nadie, que es parte del argumento de adopción.

**Cuándo dejaría de alcanzar:** varios usuarios escribiendo a la vez desde máquinas distintas. Ahí SQLite empieza a bloquear. Pero para un piloto de un equipo de transición con un paciente por día hábil, queda lejísimos de ese límite.

**Si más adelante hace falta servidor**, hay capas gratuitas reales: Supabase, Neon y Turso ofrecen Postgres o SQLite gestionado sin tarjeta. Pero **no lo metería ahora**: agrega una dependencia de red a un sistema cuya promesa es funcionar sin internet, y en la demo del hackathon eso es un riesgo sin ninguna contrapartida.

**Y una advertencia que sí importa:** el día que haya datos reales, la base **no puede estar en la máquina de nadie del equipo ni en un servicio en la nube fuera del hospital.** Va en infraestructura del INSN. Vale la pena decirlo en el pitch antes de que lo pregunten.

---

## Orden

1. **C2** primero — sin catálogo coherente, cualquier número que midas está mal
2. **C1** — el desbordamiento, que es lo que se ve
3. **C3** — desplegables en campos con catálogo
4. **C4** — acentos
5. Los dos refuerzos del acta

Y volver a correr `evaluar_corpus` después de C2: los números de antes no valen.
