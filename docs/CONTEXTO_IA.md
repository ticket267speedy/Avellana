# Contexto para IA asistente

## Proyecto

Relevo es un sistema de acompañamiento para la transición pediátrico-adulto del INSN San Borja. Su objetivo es detectar pacientes en riesgo de pérdida de continuidad, preparar la salida de la institución y cerrar el ciclo de derivación con trazabilidad y revisión humana.

## Restricciones no negociables

- el INSN no atiende mayores de 18 años bajo ninguna circunstancia
- no se usan datos reales ni personales
- todo debe funcionar sin internet para la operación principal
- no se usan API de pago ni licencias comerciales
- el médico siempre firma cualquier salida clínica
- la lógica de negocio debe mantenerse separada de la infraestructura
- los documentos y mensajes deben ser sintéticos y no pueden contener diagnósticos, dosis o resultados clínicos en notificaciones de WhatsApp

## Arquitectura

El proyecto usa una arquitectura hexagonal con cuatro capas principales:

- dominio: reglas, entidades, validaciones y puertos
- aplicacion: casos de uso
- infraestructura: adaptadores, OCR, FHIR, persistencia, notificaciones
- interfaz: API y vista web

La capa de dominio es la que define la lógica del negocio y debe ser independiente de frameworks y servicios externos.

## Casos de uso centrales

- detectar pacientes en riesgo de pérdida de continuidad
- priorizar cohortes según urgencia de transición
- preparar documentación de traspaso
- avisar por correo o WhatsApp
- confirmar que el paciente llegó al servicio de adultos
- digitalizar documentos con OCR local y validación cruzada

## Reglas clave para cualquier cambio

- no inventar datos clínicos ni dosis
- no introducir dependencias del dominio hacia infraestructura
- preservar la trazabilidad y la explicación de la prioridad
- no generar salidas clínicas sin revisión humana
- mantener el sistema ejecutable localmente sin internet
- respetar la política de privacidad y de datos sintéticos

## Estructura del repositorio

- src/relevo/dominio/: reglas y modelo del negocio
- src/relevo/aplicacion/: casos de uso y coordinación
- src/relevo/infraestructura/: adaptadores, OCR, autenticación, FHIR, persistencia, avisos
- src/relevo/interfaz/: API y capa de entrada web
- tests/: verificaciones funcionales y de arquitectura
- config/: reglas clínicas y configuración local
- data/: corpus sintético, imágenes y artefactos de demo

## Qué no es este proyecto

- no es un sistema de diagnóstico médico autónomo
- no escribe en sistemas del hospital
- no depende de que el usuario final tenga internet
- no se basa en un modelo con decisiones opacas en la parte crítica
- no es una automatización de prescripción ni de tratamiento

## Qué sí importa para la IA

La IA debe apoyar las siguientes prioridades:

- mantener la arquitectura limpia y la regla de dependencias
- evitar introducir lógica de negocio dentro de infraestructura o interfaz
- preservar la explicabilidad clínica de las decisiones
- mantener el flujo OCR con validación y revisión humana
- seguir la convención de producto: local, seguro, sin datos reales, con firma humana

## Modo de trabajo recomendado

- priorizar cambios pequeños y verificables
- mantener pruebas de arquitectura y validación relevantes en verde
- documentar decisiones clínicas y de negocio cuando se introducen supuestos
- si hay información faltante o no confirmada, anotarla y no inventarla
- mantener el repo orientado a la entrega del MVP y no a artefactos históricos
