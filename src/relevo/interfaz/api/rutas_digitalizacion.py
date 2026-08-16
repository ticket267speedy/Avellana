"""Digitalizacion de documentos escaneados desde la API del producto.

La OCR ya existe como capacidad diferencial del proyecto: no es un bloqueador
ni una app separada. Este router la expone como servicio HTTP para la misma
interfaz que el radar y la bandeja.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from relevo.interfaz.api.dependencias import ContenedorDep, RolDep, exigir_lectura_clinica

router = APIRouter(prefix="/api/digitalizacion", tags=["digitalizacion"])


@router.get("/estado")
def estado_lector(contenedor: ContenedorDep) -> dict[str, str | bool]:
    """Informa si el lector local de OCR está disponible y en qué host vive."""
    estado = contenedor.estado_lector()
    return {
        "activo": estado.activo,
        "modelo": estado.modelo,
        "host": estado.host,
        "fuente": "Ollama local",
    }


@router.get("/ejemplos")
def listar_ejemplos(contenedor: ContenedorDep) -> list[dict[str, str]]:
    """Devuelve los documentos generados artificialmente del corpus para la demo."""
    muestras = contenedor.revisar_corpus.muestras()
    salida: list[dict[str, str]] = []
    for muestra in muestras:
        salida.append(
            {
                "id": muestra.id,
                "variante": muestra.variante,
                "imagen_url": f"/data/corpus/imagenes/{muestra.id}.jpg",
            }
        )
    return salida


@router.post("/leer")
async def leer_documento(
    archivo: Annotated[UploadFile, File(description="Documento a digitalizar")],
    contenedor: ContenedorDep,
    rol: RolDep,
) -> dict[str, object]:
    """Transcribe un documento subido y devuelve los campos extraidos."""
    exigir_lectura_clinica(rol)

    if archivo.filename is None or not archivo.filename.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Hace falta un nombre de archivo para digitalizar este documento.",
        )

    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El archivo enviado esta vacio.",
        )

    lectura = contenedor.revisar_subida.leer(archivo.filename, contenido)
    documento = lectura.documento

    return {
        "documento_id": documento.documento_id,
        "texto": documento.texto,
        "lector": documento.lector,
        "desde_cache": documento.desde_cache,
        "tasa_captura": documento.tasa_captura,
        "requieren_revision": [
            {
                "nombre": campo.nombre,
                "valor": campo.valor,
                "crudo": getattr(campo, "crudo", ""),
                "motivo": getattr(campo, "motivo", ""),
            }
            for campo in documento.requieren_revision
        ],
        "campos": [
            {
                "nombre": campo.nombre,
                "valor": campo.valor,
                "crudo": getattr(campo, "crudo", ""),
                "motivo": getattr(campo, "motivo", ""),
                "requiere_revision": getattr(campo, "requiere_revision", campo.valor is None),
            }
            for campo in documento.campos
        ],
        "origen": lectura.origen,
        "verdad": lectura.verdad,
    }
