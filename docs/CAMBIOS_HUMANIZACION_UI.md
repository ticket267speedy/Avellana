# Informe de Cambios: Humanización Clínica, Ortografía y Rediseño de UI
**Proyecto:** Relevo (Puente 18+) · INSN San Borja  
**Fecha:** 14 de agosto de 2026  
**Documento para:** Equipo Avellana y Sesiones con Agentes de Código (Claude Code / Antigravity)

---

## 1. Resumen Ejecutivo de la Intervención

Se realizó una revisión profunda del código generado por Claude Code para alinear el sistema con las necesidades reales del personal asistencial (**médicos, enfermeras, asistentas sociales y coordinadores de referencia** del INSN San Borja).

La intervención corrigió los siguientes aspectos clave:
1. **Destrucción de caracteres en español (`á, é, í, ó, ú, ñ`):** Se restituyó la ortografía correcta en todo el catálogo de diagnósticos CIE-10, nombres de pacientes, regiones del Perú, medicamentos y textos de usuario.
2. **Exceso de jerga estadística y matemática:** Se eliminaron términos académicos o crípticos (*"cohorte"*, *"imputado"*, *"log-odds"*, *"intercepto $\beta_0$"*, *"sigmoide(z)"*, *"IUT"*) y se reemplazaron por lenguaje asistencial directo y empático.
3. **Eliminación total de bloques de código (JSON/YAML) en la interfaz médica:** Se eliminaron los recuadros de código para desarrolladores y se sustituyeron por tarjetas explicativas en lenguaje clínico formal, con botón de descarga digital opcional para el área de TI.
4. **Tabla Clínica Nativa de Alta Legibilidad:** Se sustituyó la tabla HTML por el componente nativo interactivo `st.dataframe` con `column_config` y selección de fila (`selection_mode="single-row"`), eliminando cualquier riesgo de fuga de código HTML y garantizando bordes nítidos, columnas ajustables y alta legibilidad para profesionales de todas las edades.
5. **Generación real de PDF oficial (ReportLab):** Se implementó la generación y descarga directa del Pasaporte de Salud 18+ en formato PDF (tamaño A4) con código QR de alta resolución y casilla formal para firma y sello médico (CMP / RNE).
6. **Diseño sobrio y sin emojis:** Apariencia hospitalaria seria y formal, con número de WhatsApp preconfigurado en `975 864 664`.

---

## 2. Detalle de Correcciones por Área

### A. Ortografía y Caracteres en Español
* **Catálogo CIE-10 ([`cohorte_sintetica.py`](file:///c:/Users/siule/Luis%20Felipe/DeepLearningUTEC/avellanaMVP/src/relevo/infraestructura/fuentes/cohorte_sintetica.py)):**
  - `Paralisis cerebral infantil` $\rightarrow$ `Parálisis cerebral infantil`
  - `Hipertension pulmonar primaria` $\rightarrow$ `Hipertensión pulmonar primaria`
  - `Tetralogia de Fallot` $\rightarrow$ `Tetralogía de Fallot`
  - `Fibrosis quistica` $\rightarrow$ `Fibrosis quística`
  - `Enfermedad renal cronica estadio 5` $\rightarrow$ `Enfermedad renal crónica estadio 5`
  - `Sindrome nefrotico corticorresistente` $\rightarrow$ `Síndrome nefrótico corticorresistente`
  - `Rinon poliquistico` $\rightarrow$ `Riñón poliquístico`
  - `Enfermedad celiaca` $\rightarrow$ `Enfermedad celíaca`
  - `Cirrosis hepatica` $\rightarrow$ `Cirrosis hepática`
  - `Inmunodeficiencia comun variable` $\rightarrow$ `Inmunodeficiencia común variable`
  - `Anemia aplasica constitucional` $\rightarrow$ `Anemia aplásica constitucional`
  - `Fenilcetonuria clasica` $\rightarrow$ `Fenilcetonuria clásica`
  - `Sindrome de Down / Marfan / Ehlers-Danlos` $\rightarrow$ `Síndrome de Down / Marfan / Ehlers-Danlos`
  - `Espina bifida` $\rightarrow$ `Espina bífida`
  - `Leucemia linfoblastica aguda` $\rightarrow$ `Leucemia linfoblástica aguda`
  - `Trasplante hepatico` $\rightarrow$ `Trasplante hepático`
  - `Traqueostomia / Gastrostomia permanente` $\rightarrow$ `Traqueostomía / Gastrostomía permanente`
  - `Dependencia de dialisis` $\rightarrow$ `Dependencia de diálisis`
  - `Neumonia adquirida en la comunidad` $\rightarrow$ `Neumonía adquirida en la comunidad`
* **Nombres y Geografía:**
  - Nombres: `María`, `José`, `Lucía`, `Sofía`, `Andrés`, `Huamán`, `Chávez`, `Sánchez`.
  - Departamentos: `Junín`, `Áncash`, `Apurímac`.
  - Medicamentos: `Ácido fólico`.

### B. Humanización del Vocabulario Clínico
Se aplicó la siguiente tabla de equivalencias en todo el sistema:

| Término anterior (Jerga Matemática) | Término asistencial (Lenguaje Clínico) | Ubicación / Justificación |
| :--- | :--- | :--- |
| *Tamaño de la cohorte* | **Total de pacientes en padrón** | Permite entender el volumen de adolescentes evaluados. |
| *Cohorte activa* | **Pacientes en preparación (14 a 17 años)** | Delimita la población que requiere atención activa antes del corte. |
| *Cohorte de seguimiento* | **Pacientes transferidos (≥ 18 años)** | Pacientes que ya cumplieron 18 y cuyo ciclo sigue en curso. |
| *IUT: 0.842* | **Prioridad Alta (Urgencia de Transferencia)** | Los médicos toman decisiones con semáforos y motivos, no con floats. |
| *Dato imputado* | **Dato no registrado en historia clínica** | Describe con precisión la ausencia de información en la ficha. |
| *$\sigma(z)$, log-odds, intercepto* | **Factores determinantes de urgencia** | Oculta la fórmula logística y destaca los riesgos asistenciales. |
| *x1 urgencia temporal* | **Tiempo restante para cumplir 18 años** | Muestra los meses exactos antes del alta obligatoria. |
| *x5 brecha de preparación* | **Autonomía y preparación para autocuidado (TRAQ)** | Evalúa la capacidad del paciente para gestionar su enfermedad. |
| *x6 riesgo de pérdida* | **Tiempo transcurrido sin consulta de control** | Identifica deserción o citas perdidas. |
| *x7 barrera de acceso* | **Residencia fuera de Lima Metropolitana** | Contempla la dificultad de traslado desde provincias. |
| *x8 continuidad de seguro* | **Riesgo de pérdida de cobertura (EsSalud/SIS)** | Alerta sobre la mayoría de edad y el régimen de aseguramiento. |

---

## 3. Arquitectura de la Interfaz Web y Pasaporte PDF

### A. Pasaporte de Salud 18+ en PDF Oficial ([`src/relevo/infraestructura/documentos/pdf_reportlab.py`](file:///c:/Users/siule/Luis%20Felipe/DeepLearningUTEC/avellanaMVP/src/relevo/infraestructura/documentos/pdf_reportlab.py))
- Generado con **ReportLab 5.0** en tamaño A4 con formato institucional para impresión láser.
- Código QR embebido localmente con resumen digital del paciente.
- Sección de Diagnósticos CIE-10 y esquema farmacológico con casillas delimitadas para dosis pendientes de firma.
- Casilla formal para firma y sello médico con número de colegiatura (CMP / RNE).

### B. Módulos de la Interfaz Web ([`src/relevo/interfaz/web/app.py`](file:///c:/Users/siule/Luis%20Felipe/DeepLearningUTEC/avellanaMVP/src/relevo/interfaz/web/app.py))
1. **Radar de Pacientes:** Tabla clínica nativa interactiva (`st.dataframe`) con columnas claramente definidas, buscador rápido por código o diagnóstico, selección de fila sincronizada con la ficha del paciente, y tarjetas de resumen KPI.
2. **Ficha y Pasaporte 18+:** Ficha descriptiva, factores de urgencia explicados con barras de progreso clínicas limpias y botón de descarga directa del PDF oficial.
3. **Avisos y Contacto Familiar:** Asistente de mensajería configurado con el número de prueba `975 864 664`, garantizando la privacidad de datos (Ley 29733).
4. **Seguimiento y Cierre de Ciclo:** Línea de tiempo formal de la derivación y registro de la primera cita cumplida en hospital de adultos.
5. **Criterios Clínicos e Interoperabilidad:** Explicación humana de los 7 criterios institucionales de priorización y botón de descarga FHIR R4 para el equipo de sistemas, sin mostrar bloques de código en pantalla.

---

## 4. Estado de Validación y Calidad

- **Pruebas Unitarias:** `pytest` ejecutado con éxito: **55 tests aprobados al 100%**.
- **Regla de Dependencia Hexagonal:** `tests/test_arquitectura.py` pasa limpiamente (el dominio no importa paquetes externos).
- **Ejecución Offline:** Todo el sistema funciona sin conexión a internet ni llamadas a APIs de pago.
