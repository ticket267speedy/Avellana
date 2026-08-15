# Cierre del MVP — instrucciones para el agente de código

**Estado:** cuatro archivos nuevos ya están en el repo, escritos y **probados en un entorno externo**. Falta el cableado, que no se pudo verificar contra este proyecto.

**Lo que NO está verificado aquí:** que importen bien, que `mypy --strict` pase, y que encajen con las firmas reales de `Paciente`, `CicloTransicion` y los puertos. Eso es lo primero que hay que comprobar.

---

## Lo que entró, y qué se probó de cada cosa

| Archivo | Probado | Sin probar |
|---|---|---|
| `infraestructura/persistencia/repositorio_sqlite.py` | Esquema, guardar/leer, persistencia al reabrir, consultas indexadas, `vaciar()` | Los mapeadores contra las entidades reales |
| `infraestructura/persistencia/auditoria.py` | Cadena de hash, **detección de manipulación**, sello de contenido | Integración con la pantalla |
| `interfaz/cli/sembrar.py` | Exportar/importar SQL, guardas de seguridad | La llamada a `contenedor.sembrar_demo()`, que **aún no existe** |
| `dominio/entidades/destino.py` | Búsqueda, motivos, `medir_cobertura` | Nada — es dominio puro, no depende de nada |

---

## T1 · 🔴 Verificación previa, antes de tocar nada

```powershell
python -c "from relevo.infraestructura.persistencia.repositorio_sqlite import BaseDatos; print('ok')"
python -c "from relevo.dominio.entidades.destino import DirectorioDestinos; print('ok')"
python -m mypy --strict src/relevo/dominio/entidades/destino.py
python -m pytest tests/ -q
```

`repositorio_sqlite.py` importa `Sequence` de `collections.abc` y puede que no lo use — quitar el import muerto si `ruff` se queja.

---

## T2 · 🔴 El PDF que sigue desbordando

**Ya se intentó una vez y no se aplicó donde importaba.** El diagnóstico exacto:

`acta_digitalizacion.py` línea 110 declara `filas: list[list[str]]` y las líneas 114-119 meten cadenas planas. `Paragraph` está importado y se usa para el título y la nota, **pero no para las celdas de la tabla**. ReportLab no ajusta líneas en un `str`: lo dibuja de corrido y lo deja salir de la celda.

Además `colWidths=[42, 52, 52, 28]` suma **174 mm** y el ancho útil de un A4 con márgenes de 20 mm es **170**.

```python
# acta_digitalizacion.py — reemplazar las lineas 110-123

from html import escape

_CELDA = ParagraphStyle(
    "celda", fontName="Helvetica", fontSize=7.5,
    leading=9.5,        # sin interlineado explicito las lineas se pisan al ajustar
    wordWrap="CJK",     # parte tambien dentro de nombres largos sin espacios
)

def _celda(texto: str | None) -> Paragraph:
    """Toda celda va en Paragraph: un str no ajusta y se sale de la columna.

    `escape` es obligatorio — ReportLab interpreta el contenido de Paragraph
    como marcado, y un valor leido por OCR puede traer '&' o '<'.
    """
    return Paragraph(escape(str(texto or "—")), _CELDA)

filas: list[list[Paragraph]] = [
    [_celda(t) for t in ("Campo", "Valor validado", "Lectura automática", "Origen")]
]
for c in campos:
    estado = c.get("estado", "")
    leido = c.get("valor_leido")
    filas.append([
        _celda(c.get("nombre", "")),
        _celda(c.get("valor_final")),
        # "no legible" y "no aplica" son cosas distintas: el guion se lee como
        # lo segundo y aqui casi siempre es lo primero.
        _celda(leido if estado == "CORREGIDO" else ("=" if leido else "no legible")),
        _celda(estado),
    ])

tabla = Table(
    filas,
    colWidths=[38 * mm, 54 * mm, 50 * mm, 28 * mm],   # 170 mm = ancho util real
    repeatRows=1,
)
```

Y **quitar** `("FONTSIZE", (0,0), (-1,-1), 7.5)` del estilo de tabla: con `Paragraph` el tamaño lo manda el `ParagraphStyle`, y tener los dos confunde.

**Prueba de aceptación, concreta:** generar un acta con
`establecimiento_destino = "INSTITUTO NACIONAL DE SALUD DEL NIÑO SAN BORJA"`
y verificar que se parte en tres líneas dentro de su celda, que la fila crece de alto, y que **nada invade la columna vecina**. Abrir el PDF y mirarlo, no solo comprobar que no lanza excepción.

Aprovechar y corregir los acentos del texto visible: *"Acta de Digitalización Asistida"*, *"Instituto Nacional de Salud del Niño San Borja"*, *"Lectura automática"*. La regla de `CLAUDE.md` de no usar tildes es **para identificadores**, no para lo que lee un médico.

---

## T3 · 🔴 Cablear SQLite

### Los mapeadores

`RepositorioPacientesSQLite` recibe `a_documento` y `desde_documento` por inyección: **no conoce la forma del agregado**. Hay que escribir ese par en `infraestructura/persistencia/mapeadores.py`.

```python
def paciente_a_documento(p: Paciente) -> dict[str, Any]:
    """Serializa el agregado completo. Sin perder nada.

    El repositorio guarda esto como JSON. Si un campo no entra aqui, se pierde
    al reiniciar — y se pierde en silencio, que es lo peor.
    """

def paciente_desde_documento(d: dict[str, Any]) -> Paciente:
    """Reconstruye. Debe ser inverso exacto del anterior."""
```

**Test obligatorio de ida y vuelta**, porque una serialización que pierde datos falla en silencio:

```python
def test_ida_y_vuelta_no_pierde_nada() -> None:
    for semilla in range(50):
        original = generar_paciente_sintetico(random.Random(semilla))
        reconstruido = paciente_desde_documento(paciente_a_documento(original))
        assert reconstruido == original, f"semilla {semilla}: la serializacion pierde datos"
```

Si `Paciente` no es comparable con `==`, comparar campo por campo. **Este test no es opcional**: es lo único que garantiza que reiniciar la app no borre información.

### Los índices

`guardar()` recibe `indices` aparte del documento. Son las columnas por las que se consulta:

```python
repo.guardar(paciente, indices={
    "fecha_nacimiento": paciente.fecha_nacimiento,
    "cohorte":          paciente.cohorte(hoy).value,
    "iut":              indice.valor,
    "estado_semaforo":  indice.estado.value,
    "confianza":        indice.confianza,
    "tiene_contacto":   paciente.tiene_contacto_vigente(hoy),
})
```

Si `indices` va vacío, el Radar no puede ordenar por IUT.

### En `arranque.py`

```python
# Un flag decide memoria o SQLite. Por defecto SQLite: si la demo no persiste,
# no es una demo de un sistema, es una demo de una pantalla.
def construir(config: Path = Path("config"), persistente: bool = True) -> Contenedor:
    if persistente:
        bd = BaseDatos(Path("data/relevo.db"))
        repo = RepositorioPacientesSQLite(bd, paciente_a_documento, paciente_desde_documento)
        auditoria = RegistroAuditoria(bd)
    else:
        repo = RepositorioPacientesMemoria()
        auditoria = RegistroAuditoriaNulo()
```

**Añadir `data/` a `.gitignore` si no está.** La base nunca se versiona.

---

## T4 · 🟠 `sembrar_demo` en el contenedor

`sembrar.py` llama a `contenedor.sembrar_demo(...)` y **ese método todavía no existe**. Hay que escribirlo en `arranque.py` con esta firma:

```python
def sembrar_demo(
    self, n_pacientes: int, semilla_aleatoria: int, hoy: date,
    ciclos_abiertos: int, reparto_estados: dict[str, int],
    vencidos_forzados: int,
) -> dict[str, int]:
    """Genera y persiste la cohorte de demo. Determinista.

    Misma `semilla_aleatoria` = misma cohorte, hasta el ultimo digito del IUT.
    Eso es lo que hace que el ensayo del pitch sea reproducible: si cada
    reinicio genera pacientes distintos, no se puede ensayar.

    `vencidos_forzados` crea ciclos con la fecha atrasada a proposito, para que
    `correr_noche` tenga siempre algo que avisar en la demo.
    """
```

Devuelve `{"pacientes": n, "ciclos": m, "vencidos": k}`.

**Verificación:**

```powershell
python -m relevo.interfaz.cli.sembrar --reiniciar
python -m relevo.interfaz.cli.sembrar --estado
python -m relevo.interfaz.cli.sembrar --reiniciar   # otra vez
```

Las dos siembras deben producir **exactamente los mismos IUT**. Si no, hay una fuente de aleatoriedad sin semilla.

---

## T5 · 🟠 Auditoría en la pantalla

Tres puntos de enganche:

**1. Cada corrección humana se registra:**

```python
if valor_nuevo != campo.valor:
    auditoria.registrar_correccion_humana(
        actor=revisor, documento_id=doc_id, campo=campo.nombre,
        valor_leido=campo.valor_crudo, valor_corregido=valor_nuevo,
    )
```

Es la contraparte de `AjusteCatalogo`: ese guarda qué corrigió el sistema, este qué corrigió la persona. Sin los dos, un acta firmada no se puede auditar.

**2. El sello va impreso en el acta:**

```python
sello = sello_de_contenido(campos_validados)
# al pie: "Sello de contenido: 587cb48868701013"
```

Sin él, el acta se puede editar después de firmada y nadie se entera.

**3. Y una advertencia honesta en la pantalla**, porque hoy es verdad:

> *"Sesión sin autenticar. El nombre del revisor es declarativo. En despliegue se firma con certificado digital, como ya hace el INSN en su historia clínica."*

**No inventar autenticación.** Declararla pendiente es correcto; fingirla no.

---

## T6 · 🟠 WhatsApp: una sola ruta

`app.py:890` construye `https://wa.me/51{telefono_limpio}?text={quote(...)}` a mano. **Ese enlace no pasa por `CanalWhatsAppEnlace`, así que no pasa por la guarda de privacidad.**

Hoy no hay fuga porque las tres plantillas están limpias. Pero el `test_privacidad_whatsapp` que falta va a probar el adaptador, **va a pasar en verde**, y el canal que la gente usa seguirá sin protección. Un test que certifica el canal equivocado es peor que no tener test.

- Mover las tres plantillas a `infraestructura/notificacion/plantillas_mensaje.py`, cada una con su bandera `contiene_datos_clinicos`
- Añadir `DespacharAvisos.preparar_para_familia(...)` que devuelve `ResultadoDespacho` con el enlace
- `app.py` usa `resultado.enlace`; si `not resultado.aceptado`, muestra el error y no ofrece el botón
- Usar `Telefono.formato_internacional` en vez de recomponer el prefijo `51` a mano

**Y un test de arquitectura nuevo**, porque el de imports no ve una f-string:

```python
def test_la_interfaz_no_construye_urls_de_canal() -> None:
    """Un enlace wa.me armado en la pantalla se salta la guarda de privacidad."""
    for archivo in Path("src/relevo/interfaz").rglob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        for patron in ("wa.me", "mailto:", "smtp"):
            assert patron not in texto, (
                f"{archivo} construye un enlace de canal ('{patron}'). "
                "Los canales se piden a la capa de aplicacion, que aplica las "
                "reglas de privacidad."
            )
```

**Solo después de esto, escribir `test_privacidad_whatsapp.py`.**

---

## T7 · 🟡 Enchufar `Destino` al Radar

`destino.py` es dominio puro y ya funciona. Falta usarlo:

1. `config/destinos.csv` con las columnas de `Destino`. **Puede ir vacío** — cuanto más vacío, más grande el hallazgo.
2. Cargarlo en `arranque.py` como `DirectorioDestinos`.
3. En el Radar, una tarjeta más:

```
Sin destino identificado
        87
de 120 evaluados · 0 son brecha de oferta
```

`medir_cobertura(directorio, diagnosticos)` lo devuelve hecho.

**Ese número es entregable de pitch aunque el directorio esté vacío**, porque hoy nadie en el INSN lo tiene. No mide qué tan bueno es el software: mide un hueco del sistema de salud que nadie había cuantificado.

---

## T8 · 🟡 FHIR — lo último y el diferenciador

`infraestructura/interoperabilidad/` existe y está vacía. Es la promesa número uno del dossier y sigue en cero.

Bundle tipo `document` con perfiles CorePE del MINSA: `Composition`, `Patient`, `Condition`, `MedicationStatement`, `AllergyIntolerance`, `Organization`, `Practitioner`. Validar contra el validador público de HAPI FHIR. **Si no valida, no es entregable.**

---

## Orden y verificación final

| # | Qué | Bloqueante |
|---|---|---|
| T1 | Que todo importe y los tests pasen | Sí |
| T2 | El PDF | Sí — es lo que se ve |
| T3 | Mapeadores + SQLite en `arranque` | Sí |
| T4 | `sembrar_demo` | Sí — sin esto no hay reinicio |
| T6 | WhatsApp ruta única | Sí — antes del test de privacidad |
| T5 | Auditoría en pantalla | Casi |
| T7 | `Destino` en el Radar | Barato y vale mucho |
| T8 | FHIR | Sí, si queda tiempo |

```powershell
python -m pytest tests/ -q
python -m mypy --strict src/relevo/
python -m relevo.interfaz.cli.sembrar --reiniciar
python -m relevo.interfaz.cli.correr_noche --hoy 2026-08-15
streamlit run src/relevo/interfaz/web/app.py
```

- [ ] Toda la suite en verde, `mypy --strict` limpio
- [ ] Test de ida y vuelta de serialización pasa con 50 semillas
- [ ] Dos siembras seguidas producen los mismos IUT
- [ ] **Cerrar la app, reabrirla, y que los pacientes sigan ahí**
- [ ] El acta con el nombre largo del INSN no desborda — mirando el PDF
- [ ] Las correcciones humanas aparecen en `auditoria`, y la cadena verifica
- [ ] El sello sale impreso en el acta
- [ ] `test_la_interfaz_no_construye_urls_de_canal` pasa
- [ ] El Radar muestra el conteo de pacientes sin destino

---

## Sobre la IP y la MAC

`auditoria.py` **sí las registra**, en `contexto_de_maquina()`, como metadato forense. Nunca como identidad, y con la advertencia escrita en el propio registro.

Detecta además el caso en que `uuid.getnode()` devolvió un número aleatorio — el bit 41 a 1 — y en vez de guardar ruido con aspecto de dato, guarda `"aleatoria-no-fiable"`.

**No usarlas para firmar.** La MAC es capa 2 y no atraviesa el router: servido desde un servidor, este código vería la MAC del propio servidor, idéntica para todos los usuarios. Hoy parece funcionar solo porque Streamlit corre en la misma máquina que el navegador.

Lo que el INSN usa de verdad está impreso en su propia historia clínica: **firma digital con certificado**. Ese es el camino de despliegue, y el equivalente honesto para el MVP es lo que quedó implementado — usuario declarado + marca de tiempo + hash del contenido + cadena de auditoría.
