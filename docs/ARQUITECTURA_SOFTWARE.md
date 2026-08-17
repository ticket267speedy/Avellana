# Arquitectura de software

## 1. Propósito

Relevo acompaña la transición asistencial pediátrico-adulto del INSN San Borja. El producto no intenta reemplazar la decisión clínica: busca detectar casos en riesgo, organizar la derivación, preparar la documentación y dejar trazabilidad para que un profesional revise y firme cualquier salida.

## 2. Principios que definen el diseño

- Arquitectura hexagonal
- Dependencias apuntando hacia el dominio
- Reglas clínicas audibles y verificables
- Operación local y sin internet para la parte principal
- Datos sintéticos y sin identidad real
- No se escriben sistemas del hospital ni se usa información real

## 3. Capas del sistema

### 3.1 Dominio

La capa de dominio contiene la lógica de negocio y las reglas que no cambian aunque cambie la infraestructura. Aquí viven entidades, objetos de valor, validaciones y puertos abstractos.

Incluye conceptos como:

- pacientes y cohortes
- diagnósticos y categorías de complejidad
- cálculo de urgencia
- reglas de corte etario
- ciclo de transición y confirmación
- pasaporte y documentación de traspaso

El dominio debe poder ejecutarse y probarse sin base de datos, sin red y sin mocks. Si una regla depende de un framework o de una API, no pertenece al dominio.

### 3.2 Aplicación

La capa de aplicación orquesta casos de uso. Sirve de frontera entre el dominio y la infraestructura, y decide qué flujo se ejecuta para cada acción del sistema.

Ejemplos:

- priorizar cohortes
- evaluar urgencia y riesgo de pérdida
- generar documentos de traspaso
- despachar avisos
- registrar confirmación de llegada o cierre del ciclo

### 3.3 Infraestructura

La infraestructura implementa los puertos definidos por el dominio. Aquí va todo lo que depende del entorno exterior:

- OCR local con Ollama
- lectura de documentos e imágenes
- carga de config YAML
- FHIR y exportación interoperable
- correo y WhatsApp
- persistencia y almacenamiento
- generación de PDFs y artefactos de salida

La regla es simple: si algo depende del mundo real, vive aquí.

### 3.4 Interfaz

La interfaz expone la solución a usuarios o sistemas externos. En el repositorio se usa una API FastAPI con frontend estático y un conjunto de rutas organizadas por rol y flujo. El objetivo es mantener el comportamiento operativo desacoplado de la presentación.

## 4. Validación y seguridad

El proyecto aplica validaciones en varias capas:

1. formato
2. catálogo
3. coherencia clínica
4. negocio
5. privacidad

Ejemplos:

- DNI con 8 dígitos
- teléfono celular peruano con 9 dígitos
- fecha con formato válido
- códigos CIE-10 restringidos al catálogo vigente
- mensajes de WhatsApp sin diagnósticos, dosis ni resultados

La regla no es inventar datos. Si algo no es legible o no está confirmada la información, debe quedar como no válido o pendiente de revisión, no como inferencia sin sustento.

## 5. Lógica de priorización

La priorización se hace con un índice de urgencia basado en reglas explicables. El sistema combina factores como:

- tiempo antes de cumplir 18 años
- complejidad clínica
- severidad del caso
- dependencia tecnológica
- riesgo de pérdida de continuidad
- barreras de acceso
- disponibilidad y calidad de datos

La clave es que el número no viaja solo: el sistema debe poder explicar por qué ese paciente tiene prioridad.

## 6. Ciclo de transición

El flujo de transición se modela como una secuencia con estados. Lo importante es que el sistema no solo crea un documento: también registra si la derivación fue aceptada, si hubo cita, si se confirmó la llegada y si el ciclo se cerró de manera auditable.

## 7. OCR y digitalización local

La digitalización usa un flujo local con validación cruzada. El objetivo no es confiar en una sola lectura del documento; se busca detectar errores tempranamente y forzar revisión humana cuando haya dudas. Así, el OCR no reemplaza el criterio clínico, sino que reduce la fricción del ingreso documental.

## 8. Restricciones del producto

El proyecto tiene límites explícitos:

- no usa datos reales
- no escribe en sistemas del hospital
- no depende de internet para la operación principal
- los avisos clínicos requieren revisión humana
- WhatsApp y correo no llevan diagnósticos, dosis ni resultados
- la salida final debe ser firmada por el profesional

### 8.1 Simulación de separación por red y rol

En este MVP la diferencia entre el entorno del INSN y los accesos del paciente, apoderado y médico receptor se implementa como una simulación visual y funcional de segmentación. El objetivo es mostrar, en la demo, que el admin y el médico del INSN comparten un contexto interno y que los demás actores operan en accesos distintos, con experiencias de interfaz separadas.

Esto no es una LAN real, ni una VLAN, ni una separación de red de producción. Es una representación deliberada para la navegación y la lógica de acceso por rol. La comprobación de seguridad, el aislamiento real y la política de red se resolverían fuera del MVP con infraestructura de red, autenticación, proxy inverso y control de acceso.

## 9. Cómo se mantiene la claridad técnica

- la lógica clínica vive en el dominio
- la infraestructura implementa adaptadores y servicios externos
- la interfaz solo consume la capa funcional
- las pruebas verifican la regla de dependencias y el comportamiento crítico

Esto permite que el proyecto conserve su promesa: el núcleo de negocio permanece estable aunque cambie la forma de entrar datos o la tecnología de ejecución.

## 10. Resumen ejecutivo

Relevo es un sistema de acompañamiento clínico y administrativo para una transición de alto riesgo. La arquitectura está pensada para ser auditable, local, segura y explicable, con la lógica de negocio separada de la infraestructura y la validación humana siempre presente.
