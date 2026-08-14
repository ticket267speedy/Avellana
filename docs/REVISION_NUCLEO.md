# Revisión del núcleo — bloques 1 a 6

**Fecha:** 14 de agosto de 2026
**Alcance revisado:** `dominio/servicios/calculadora_iut.py`, `dominio/objetos_valor/indice_urgencia.py`
**Veredicto general:** sólido. Cuatro correcciones antes de seguir, dos de ellas bloqueantes.

---

## Las dos decisiones que se consultaron

### ✅ Decisión 1 — imputar x6 y x7 a 0.5 con marca: **correcta**

El razonamiento del comentario es exactamente el correcto:

> *"No saber cuándo vino por última vez no es lo mismo que haber venido ayer."*

Imputar al centro y marcar es la única postura honesta. Imputar a 0 asume lo mejor sin motivo; imputar a 1 castiga al paciente por un fallo de registro del hospital. Se queda como está.

### ✅ Decisión 2 — `PRIVADO` marcado como supuesto: **correcta**

Y el método también: se verificó contra el código en vez de contra la propia afirmación. `verificado: false` en el YAML manda. Se queda.

---

## 🔴 C1 — BLOQUEANTE. `default_factory` contradice el principio del propio archivo

**Archivo:** `dominio/servicios/calculadora_iut.py`, línea 225.

```python
parametros: ParametrosIUT = field(default_factory=ParametrosIUT.provisionales)
```

El archivo declara, en `__post_init__` de `ParametrosIUT`:

> *"Nadie debe inventar un peso: se carga del YAML o se detiene."*

Pero este `default_factory` hace justo lo contrario: `CalculadoraIUT()` sin argumentos **corre en silencio con pesos inventados** y produce números que parecen legítimos. En un hackathon, donde alguien va a instanciar la calculadora a las 3 a.m. sin pensar, esto termina con una demo mostrando prioridades clínicas basadas en valores que nadie validó.

**Cambio:**

```python
# ANTES (línea 225)
parametros: ParametrosIUT = field(default_factory=ParametrosIUT.provisionales)

# DESPUÉS
parametros: ParametrosIUT
```

Sin valor por defecto. Quien construye la calculadora tiene que decir con qué política clínica lo hace. Si nadie la carga, falla ruidosamente — que es lo que el propio archivo pide.

### Y esto resuelve solo el TODO de la duplicación

Con el default eliminado, `ParametrosIUT.provisionales()` y `PoliticaPlazos.provisionales()` **dejan de ser código de producción y pasan a ser lo que en realidad son: fixtures de prueba.**

**Cambio:** moverlos a `tests/dominio/conftest.py`.

```python
# tests/dominio/conftest.py

@pytest.fixture
def parametros_iut() -> ParametrosIUT:
    """Copia de config/reglas_transicion.yaml v0.1.0-provisional.

    Vive en los tests, no en el dominio: la politica clinica de produccion
    se carga del YAML y de ningun otro lado.
    """
    return ParametrosIUT(...)
```

Así ya no hay política clínica duplicada en dos sitios de producción, y el TODO desaparece en vez de quedar esperando al bloque 7. El test de infraestructura que compare fixture contra YAML sigue siendo buena idea, pero ya no es un parche a un riesgo: es una verificación de regresión.

---

## 🔴 C2 — BLOQUEANTE. `x2` y `x3` miden lo mismo dos veces

**Archivo:** `dominio/servicios/calculadora_iut.py`, líneas 239–252.

```python
def _x2_complejidad(...):
    k = len(paciente.diagnosticos)
    x = _acotar(k / self.parametros.diagnosticos_techo)

def _x3_severidad(...):
    suma = sum(severidad_por_categoria.get(dx.categoria.value, 0)
               for dx in paciente.diagnosticos)     # ← suma SOBRE DIAGNOSTICOS
    x = _acotar(suma / self.parametros.peso_maximo_severidad)
```

Los dos crecen con el número de diagnósticos. Un paciente con tres diagnósticos cardiovasculares obtiene `x2 = 0.6` **y** `x3 = 9/9 = 1.0`, y el desglose los presenta como dos razones independientes cuando son la misma señal contada dos veces.

**Por qué esto importa más de lo que parece:** el desglose *es* el producto. Si un médico lee *"complejidad: 0.72 · severidad: 1.50"* concluye que hay dos motivos distintos. Hay uno. Estamos rompiendo la promesa de explicabilidad, que es nuestro principal diferenciador frente a un modelo opaco.

**Cambio propuesto — descorrelacionar preguntando dos cosas genuinamente distintas:**

| Factor | Antes | Después | Pregunta que responde |
|---|---|---|---|
| `x2` complejidad | número de diagnósticos | **número de categorías CCC v2 distintas** / techo | *¿cuántos sistemas están comprometidos?* |
| `x3` severidad | suma de severidad sobre diagnósticos | **severidad máxima** entre los diagnósticos / severidad máxima posible | *¿qué tan grave es lo peor que tiene?* |

```python
def _x2_complejidad(self, paciente: Paciente) -> AporteFactor:
    """Numero de CATEGORIAS CCC v2 distintas / techo.

    Cuenta sistemas comprometidos, no diagnosticos: tres codigos
    cardiovasculares son un sistema, no tres. Asi x2 mide extension y x3
    mide gravedad, que son preguntas distintas.
    """
    categorias = {
        dx.categoria for dx in paciente.diagnosticos
        if dx.activo and dx.es_cronico
    }
    x = _acotar(len(categorias) / self.parametros.categorias_techo)
    return self._aporte(X2_COMPLEJIDAD, x)

def _x3_severidad(self, paciente: Paciente) -> AporteFactor:
    """Severidad MAXIMA entre los diagnosticos activos / severidad maxima posible.

    Un paciente con una condicion severa y dos leves es un paciente severo.
    Sumar convertiria la severidad en un segundo contador de diagnosticos.
    """
    severidades = [
        self.parametros.severidad_por_categoria.get(dx.categoria.value, 0)
        for dx in paciente.diagnosticos if dx.activo and dx.es_cronico
    ]
    maxima = max(severidades, default=0)
    x = _acotar(maxima / self.parametros.severidad_maxima_posible)  # = 3
    return self._aporte(X3_SEVERIDAD, x)
```

**Hacerlo antes de que el mentor ponga los β.** El significado de cada β depende de qué mide su factor; si cambiamos la definición después, los pesos que nos dé quedan sin sentido.

**Y esto también arregla C3 de paso.**

---

## 🟠 C3 — `x2` cuenta todos los diagnósticos, no los crónicos activos

Deriva respecto del `PLAN_TECNICO` §6.2, que dice **`K` = dx crónicos activos**. El código hace `len(paciente.diagnosticos)`, sin filtrar por `activo` ni por cronicidad. Una fractura resuelta hace tres años sube la complejidad de un paciente.

El filtro `if dx.activo and dx.es_cronico` del bloque anterior lo resuelve. Verificar que `Diagnostico` expone ambas propiedades; si `es_cronico` no existe, derivarla del clasificador de cohorte en vez de duplicar la lógica.

---

## 🟠 C4 — Falta el estado "datos insuficientes"

`hay_datos_faltantes` existe pero es booleano, y `IndiceUrgencia` reporta un valor con aspecto de certeza aunque una parte grande del modelo esté imputada.

El caso concreto: un paciente con SIS, sin TRAQ, sin fecha de última consulta y sin procedencia tiene imputados `x5 + x6 + x7 + x8`, cuyos β suman **3.3 de 10 — el 33 % del modelo**. La interfaz muestra `IUT 0.657 [ámbar]` como si fuera un dato.

**Cambio — agregar una medida de confianza a `IndiceUrgencia`:**

```python
@property
def confianza(self) -> float:
    """Fraccion del peso total del modelo que se apoya en datos reales.

    1.0 = ningun factor imputado. 0.67 = un tercio del indice es supuesto.
    El numero se muestra junto al IUT: quien firma tiene derecho a saber
    sobre cuanto dato real esta decidiendo.
    """
    total = sum(abs(a.beta) for a in self.aportes)
    if total == 0.0:
        return 0.0
    imputado = sum(abs(a.beta) for a in self.aportes if a.dato_faltante)
    return 1.0 - imputado / total

@property
def datos_insuficientes(self) -> bool:
    """True si mas del 30% del peso del modelo esta imputado.

    Umbral provisional. TODO: confirmar con mentor — a partir de que punto
    un puntaje deja de ser accionable.
    """
    return self.confianza < 0.70
```

Y en la interfaz: cuando `datos_insuficientes` es verdadero, la insignia dice **"Prioridad alta · datos insuficientes"** en vez de solo "Prioridad alta". No cambia la priorización — cambia lo que el sistema afirma saber.

Es barato y es exactamente el tipo de honestidad que un jurado clínico premia. También responde por adelantado a *"¿y si les faltan datos?"*.

---

## 🟡 Menores

**M1.** `peso_maximo_severidad=9.0` es el único valor del archivo sin fuente en el comentario. Todos los demás la tienen. Marcar `# TODO: confirmar con mentor` o justificarlo. Con el cambio de C2 desaparece, reemplazado por `severidad_maxima_posible=3`.

**M2.** `ambar = min(self.parametros.umbral_ambar, rojo)` — si la calibración devuelve un rojo por debajo del ámbar (cohorte chica, capacidad grande), la banda ámbar desaparece en silencio. Debería avisar, no colapsar callado.

**M3.** `calibrar_umbral_rojo` devuelve `1.0` sin capacidad, pero `sigmoide` puede redondear a `1.0` con z grande, y la comparación es `valor >= rojo`. Borde improbable; devolver `math.nextafter(1.0, 2.0)` o documentarlo.

---

## Siguiente bloque: saltar el 7

**No construir SQLite todavía.** Razones:

1. Para la demo no hace falta persistencia entre corridas: el proceso nocturno regenera todo.
2. Los mapeadores ORM ↔ dominio son el trabajo más tedioso y menos diferenciador del proyecto.
3. **La arquitectura hexagonal existe justamente para poder aplazar esta decisión.**

**En su lugar, treinta líneas:**

```python
# infraestructura/persistencia/repositorio_memoria.py
class RepositorioPacientesMemoria(RepositorioPacientes):
    """Implementa el puerto en memoria. Suficiente para el MVP completo.

    SQLite entra despues, si sobra tiempo, y sera un reemplazo directo:
    el resto del sistema no se entera porque habla con el puerto.
    """
```

Con eso los bloques 8 a 14 quedan desbloqueados hoy mismo, y SQLite pasa a ser opcional. Si el jurado pregunta por persistencia, la respuesta es fuerte: *"el puerto ya está definido; cambiar el adaptador es un archivo"* — y es verdad, demostrable.

**Orden recomendado:** `RepositorioMemoria` → 8 (cohorte sintética) → 9 (casos de uso) → 10 (`SinLLM`) → 11 (PDF + QR) → 12 (FHIR) → 14 (interfaz) → 15 → 16 → 7 solo si sobra tiempo.

---

## Orden de trabajo de esta revisión

1. **C1** — quitar el `default_factory`, mover `provisionales()` a `conftest.py`
2. **C2 + C3** — redefinir `x2` y `x3`, recalcular los cinco casos a mano
3. **C4** — `confianza` y `datos_insuficientes`
4. **M1, M2, M3**
5. `RepositorioMemoria`, y seguir por el bloque 8

⚠️ **C2 cambia la aritmética de los cinco casos de aceptación.** Hay que recalcularlos en papel, no ajustar los tests al resultado del código. El criterio del bloque 3 es que el papel mande.
