# Estructura técnica del proyecto

## 1. Objetivo de esta guía

Este documento complementa al README y describe cómo está organizado el software para que otra IA o desarrollador nuevo entienda la base del producto sin tener que revisar el código completo.

## 2. Vista general

El proyecto está organizado por capas funcionales siguiendo arquitectura hexagonal:

- dominio
- aplicacion
- infraestructura
- interfaz

La regla general es que las dependencias apuntan hacia adentro. La lógica crítica del negocio no depende de frameworks ni de servicios externos.

## 3. Capa de dominio

Ruta principal:

- src/relevo/dominio/

Aquí viven los conceptos del problema y las reglas del negocio. Esta capa incluye:

- entidades del paciente y del ciclo de transición
- objetos de valor para fechas, códigos, teléfonos y otros datos críticos
- validaciones y reglas de negocio
- puertos abstractos que definen interfaces para infraestructura

Importante:

- no importa FastAPI
- no importa SQLAlchemy
- no importa requests
- no importa modelos externos ni LLMs

Si una operación es propia del negocio, va aquí.

## 4. Capa de aplicación

Ruta principal:

- src/relevo/aplicacion/

Esta capa coordina casos de uso. Su función es poner en movimiento la lógica del dominio, invocando puertos y decisiones de negocio necesarias para cada flujo.

Ejemplos de responsabilidad:

- priorizar una cohorte de transición
- evaluar un paciente ante la ventana de edad
- generar un documento de traspaso
- preparar avisos para equipo o familia
- registrar confirmación de cita o llegada

La aplicación no debería estar llena de detalles de infraestructura. Su trabajo es orquestar, no implementar la lógica técnica.

## 5. Capa de infraestructura

Ruta principal:

- src/relevo/infraestructura/

Aquí se implementan los adaptadores que conectan el sistema con el mundo exterior. Esto incluye:

- OCR local con Ollama
- lectura de imágenes y documentos
- persistencia y almacenamiento
- carga de YAML de configuración
- exportación FHIR
- notificaciones por correo y WhatsApp
- generación de PDF y artefactos

Todo lo que depende de un entorno externo vive aquí. Esta capa implementa los puertos declarados por el dominio.

## 6. Capa de interfaz

Ruta principal:

- src/relevo/interfaz/

La interfaz es la entrada del sistema al usuario o a otros sistemas. Aquí se exponen rutas, páginas y adaptadores para la operación real.

En el repo se usa una mezcla de:

- API FastAPI
- frontend estático en JavaScript/CSS
- rutas y dependencias de autenticación/roles
- flujo web para navegación y visualización del MVP

La interfaz no define la lógica de negocio; solo la consume y la presenta.

## 7. Configuración y datos

### config/

Aquí se guardan entradas de negocio y políticas configurables, como:

- reglas de transición
- plazos del ciclo
- catálogo de diagnósticos raros
- destinos y mappings
- abreviaturas clínicas y semilla de demo

La idea es que la política clínica no esté harcodeada en el código. El dominio sigue siendo el mismo aunque cambien los valores de configuración.

### data/

Aquí se mantienen los artefactos sintéticos del proyecto:

- corpus de prueba
- imágenes y transcripciones
- documentos de demo
- contenidos no reales

No debe haber datos reales ni identificadores de pacientes reales.

## 8. Pruebas

Ruta principal:

- tests/

El repositorio separa pruebas por tipo:

- dominio: lógica sin infraestructura ni red
- infraestructura: adaptadores, OCR, FHIR, privacidad, persistencia
- interfaz: rutas, autenticación, contrato API y flujo de usuario
- arquitectura: validación de dependencias y capa de diseño

Las pruebas no son solo de calidad: también protegen la arquitectura. En particular, el test de arquitectura se encarga de garantizar que el dominio no dependa de capas externas.

## 9. Qué busca preservar el proyecto

- la lógica clínica separada de la presentación
- operación local y sin internet
- no depender de APIs pagadas ni externas para la operación principal
- trazabilidad y firma humana en cualquier salida clínica
- validación y descarga de datos con criterio, no con inferencia sin respaldo

## 10. Resumen corto para otra IA

Si otra IA va a continuar el proyecto, la recomendación es partir por:

1. dominio
2. casos de uso
3. puertos e infraestructura
4. rutas e interfaz
5. pruebas de arquitectura y validación

Y mantener siempre presente esta regla: el negocio debe seguir funcionando aunque cambien la interfaz, la base de datos o el proveedor de OCR.
