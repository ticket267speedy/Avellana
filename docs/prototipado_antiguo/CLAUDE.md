# Contexto operativo del proyecto Relevo

Este documento forma parte del prototipado antiguo y del historial de contexto del equipo. No es la fuente principal del producto actual, pero sigue siendo útil como referencia operativa para continuidad del trabajo.

## 1. Qué es Relevo

Relevo es un sistema de acompañamiento de la transición pediátrico-adulto del INSN San Borja.

Su propósito es:

- detectar casos en riesgo de pérdida de continuidad
- priorizar según urgencia clínica y administrativa
- preparar documentación de traspaso
- avisar por correo o WhatsApp
- confirmar que el paciente llegó al servicio de adultos

La regla más importante del proyecto es que el INSN no atiende mayores de 18 años bajo ninguna circunstancia. El corte es absoluto.

## 2. Reglas no negociables

1. No usar ni versionar datos reales de pacientes.
2. No depender de internet para la operación principal.
3. No usar APIs pagadas, licencias comerciales ni servicios de pago.
4. Mantener la lógica clínica fuera de infraestructura y de la interfaz.
5. El médico siempre debe revisar y firmar cualquier salida clínica.
6. La validación no debe inventar datos ni completar campos sin sustento.
7. Los mensajes de WhatsApp no pueden llevar diagnósticos, dosis, medicamentos ni resultados.
8. El dominio se prueba sin mocks ni base de datos ni red.

## 3. Arquitectura actual

El proyecto usa arquitectura hexagonal:

- dominio: reglas y entidades de negocio
- aplicacion: casos de uso
- infraestructura: OCR, persistencia, FHIR, avisos, archivos
- interfaz: API y frontend web

La regla de dependencia es estricta: el dominio no importa frameworks ni servicios externos.

## 4. Documentos de referencia principal

Leer en este orden:

1. README.md
2. docs/PLAN_TECNICO.md
3. docs/ARQUITECTURA_SOFTWARE.md
4. docs/ESTRUCTURA_TECNICA.md
5. docs/CONTEXTO_IA.md

Los demás documentos sirven como material de fondo, pero no reemplazan la lectura principal del sistema.

## 5. Qué no se construye

- adaptador real a SisGalenPlus sin contrato claro
- chatbot de WhatsApp con recepción activa
- OCR de historias manuscritas como alcance principal
- asignación automática del destino final
- aprendizaje automático como núcleo del producto
- escritura en sistemas del hospital

## 6. Qué debe mantenerse cada vez que se edite el proyecto

- no introducir dependencias del dominio hacia la infraestructura
- no inventar dosis ni resultados clínicos
- no dejar textos de usuario con ortografía o acentos rotos
- preservar la lógica explicable y auditable
- mantener el flujo local y sin internet

## 7. Contexto del producto actual

La base técnica del proyecto es un MVP local con:

- FastAPI como API principal
- frontend estático y navegación por roles
- OCR local usando Ollama
- configuración por YAML y corpus sintético
- pruebas de arquitectura, interfaz, integración y privacidad

El objetivo no es “hacerlo bonito” por encima de la realidad clínica; es mantener un sistema verificable, local y útil para acompañar la transición sin romper la regla institucional del corte a los 18 años.

