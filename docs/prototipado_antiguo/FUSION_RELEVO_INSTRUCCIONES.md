# Instrucciones de continuidad para Relevo

Este documento forma parte del prototipado antiguo y del historial operativo del equipo. No es el documento principal del producto, pero conserva contexto útil para continuidad del trabajo y para revisar decisiones tomadas antes de cerrar la versión MVP.

## 1. Estado actual del proyecto

El repositorio está centrado en un MVP local de acompañamiento de la transición pediátrico-adulto, con foco en:

- prioridad clínica y administrativa
- flujo de traspaso y cierre del ciclo
- OCR local con validación
- roles y permisos ligeros para demo
- documentación y trazabilidad del proceso

El producto no es una implementación de aprendizaje automático como núcleo; la lógica crítica sigue siendo explicable y guiada por reglas y validación humana.

## 2. Contexto principal del repositorio

Los documentos principales para continuar el trabajo son:

- README.md
- docs/PLAN_TECNICO.md
- docs/ARQUITECTURA_SOFTWARE.md
- docs/ESTRUCTURA_TECNICA.md
- docs/CONTEXTO_IA.md
- docs/ARQUITECTURA.md
- docs/DOSSIER.md
- docs/GUIA_OLLAMA.md

Estos son los documentos activos para trabajo principal. El material restante debe quedar acotado como documentación auxiliar, histórica o de prototipado.

## 3. Qué debe evitarse en el repositorio principal

- documentación histórica de trabajo en ramas o fusiones
- listas largas de checkpoints de desarrollo
- texto informal de sesión o decisiones no consolidadas
- notas más orientadas al proceso interno que al producto real
- material antiguo que ya fue reemplazado por documentación actual

La regla general es simple: si no ayuda al producto actual ni a la continuidad del proyecto, no debería estar en la capa principal del repo.

## 4. Cómo continuar cuando se toma una decisión

Antes de cambiar lógica o arquitectura, conviene:

1. leer README.md
2. validar el alcance en docs/PLAN_TECNICO.md
3. revisar la estructura técnica en docs/ESTRUCTURA_TECNICA.md
4. mantener la capa de dominio separada de infraestructura y de interfaz
5. no inventar datos ni dosis ni resultados clínicos

## 5. Criterio de limpieza

Un documento solo debe mantenerse en la capa principal si:

- refleja la arquitectura y restricciones reales del producto
- ayuda a otro desarrollador o a otra IA a continuar sin perder contexto
- no es un registro de eventos internos, ramas, pruebas pasajeras o conversaciones

Cuando un documento ya no cumple eso, debe quedar en una zona de histórico o prototipo y no en el flujo principal.

## 6. Prototipado antiguo y uso de Streamlit

Streamlit se usó en una etapa temprana del proyecto como herramienta de prototipado, visualización rápida y compartición del trabajo entre miembros del equipo. Fue útil para mostrar ideas de flujo, validar la experiencia de usuario y discutir decisiones de negocio antes de consolidar la versión MVP con FastAPI y frontend estático.

Ese uso histórico sigue siendo relevante como referencia para entender cómo evolucionó el proyecto, pero no forma parte del producto activo. Por eso se conserva en la carpeta de prototipado antiguo, como material de contexto y legado técnico, no como base operativa del sistema actual.

## 7. Regla final

El repositorio debe sentirse como un sistema vivo y mantenido, no como un archivo de conversación o de trabajo en curso. La documentación principal debe entrar por el producto actual y por la arquitectura vigente, no por el historial de mezclas ni por notas operativas de sesión.

La regla institucional sigue intacta: no atiende mayores de 18 años bajo ninguna circunstancia.
