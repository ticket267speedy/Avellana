# Relevo

Sistema de acompañamiento para la transición pediátrico-adulto del INSN San Borja.

## Objetivo

Detectar pacientes crónicos, raros o complejos que se acercan a los 18 años, priorizarlos con reglas audibles, generar un documento de traspaso, avisar por correo o WhatsApp y seguir el ciclo hasta confirmar que el paciente llegó al servicio de adultos.

La regla de negocio central es dura: el INSN no atiende mayores de 18 años bajo ninguna circunstancia. El corte es exacto y total.

## Arquitectura hexagonal

El proyecto sigue una arquitectura hexagonal con capas internas y externas:

- dominio: reglas de negocio, entidades, validaciones, puertos
- aplicacion: casos de uso
- infraestructura: adaptadores, persistencia, OCR, FHIR, notificaciones
- interfaz: API web y navegadores

Las dependencias apuntan hacia adentro. El dominio no depende de frameworks ni de servicios externos.

## Requisitos

- Python 3.12+
- Ollama instalado localmente para OCR
- acceso local a la red de la máquina
- entorno sin internet para la operación principal

## Dependencias

Instalar el entorno del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e ".[api,dev,fhir,pdf]"
```

Si se quiere conservar el soporte de la vista web antigua con Streamlit, también se puede instalar:

```powershell
pip install -e ".[web]"
```

## Inicio del sistema

### 1. Arrancar la API y la web estática

```powershell
.\.venv\Scripts\python.exe -m uvicorn relevo.interfaz.api.principal:app --host 0.0.0.0 --port 8000
```

Abrir en el navegador:

- http://localhost:8000

### 2. Verificar que el OCR local esté disponible

Instalar y levantar Ollama en la máquina local:

```powershell
ollama pull glm-ocr
ollama serve
```

La aplicación consulta el endpoint de Ollama en localhost, usando el modelo configurado por la infraestructura local. Si el modelo corre fuera de esta máquina (por ejemplo, por un túnel o un equipo del laboratorio), se puede redirigir con la variable de entorno:

```powershell
$env:RELEVO_OLLAMA_HOST = "http://localhost:11434"
# o un host remoto expuesto por tunel, por ejemplo:
# $env:RELEVO_OLLAMA_HOST = "http://host-del-tunel:11434"
```

La app usa este valor si existe; si no, vuelve a `http://localhost:11434`.

### 3. Ejecutar pruebas relevantes

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Estructura principal

- src/relevo/dominio/: reglas y entidades del negocio
- src/relevo/aplicacion/: casos de uso
- src/relevo/infraestructura/: adaptadores, OCR, FHIR, almacenamiento, notificaciones
- src/relevo/interfaz/: API web y capas de entrada
- tests/: pruebas del dominio, infraestructura e interfaz
- config/: reglas clínicas, destinos y semilla de demo
- data/corpus_demo/: corpus sintético de demo que se entrega con el repo para que la OCR funcione sin regenerar fichas
- data/corpus/: corpus local generado por la máquina, no versionado ni entregado como dato real

## Reglas de calidad

- el dominio no puede importar librerías externas ni frameworks
- las validaciones no deben dar lugar a valores inventados
- la salida clínica requiere revisión humana
- todo dato sintético y no real
- la lógica de corte por edad es estricta y no negociable

## Documentación útil

- docs/PLAN_TECNICO.md: especificación técnica del proyecto
- docs/DOSSIER.md: contexto funcional y de negocio
- docs/ARQUITECTURA.md: explicación general de la arquitectura
- docs/GUIA_OLLAMA.md: guía de instalación y uso local del OCR
- docs/ARQUITECTURA_SOFTWARE.md: resumen técnico para integración y mantenimiento
- docs/ESTRUCTURA_TECNICA.md: estructura técnica del repositorio y cómo se organiza el software
- docs/CONTEXTO_IA.md: contexto compacto para alimentar una IA de apoyo

## Limitaciones del MVP

- no se escribe en sistemas del hospital
- no se usan APIs de pago ni licencias comerciales
- no se depende de internet para el funcionamiento principal
- los mensajes de WhatsApp no contienen diagnósticos ni dosis ni resultados
- el resumen clínico requiere firma del médico
