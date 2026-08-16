"""Endpoints de autenticacion institucional y gestion de sesiones.

PLAN_TECNICO §8.3 / FUSION_RELEVO_INSTRUCCIONES §8.3:
Autenticacion con argon2id, sesion en cookie HttpOnly / SameSite=Strict y
asiento en la cadena de hash de auditoria.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from relevo.interfaz.api.autenticacion import NOMBRE_COOKIE_SESION
from relevo.interfaz.api.dependencias import (
    ContenedorDep,
    obtener_gestor_auth,
    obtener_sesion_actual,
)
from relevo.interfaz.api.esquemas import EntradaLogin, SalidaSesion

router = APIRouter(prefix="/api/auth", tags=["autenticacion"])


@router.post("/login", response_model=SalidaSesion)
def login(
    entrada: EntradaLogin,
    response: Response,
    contenedor: ContenedorDep,
) -> SalidaSesion:
    """Inicia sesion con credenciales argon2id y emite cookie HttpOnly."""
    gestor = obtener_gestor_auth()
    sesion = gestor.autenticar(
        username=entrada.usuario,
        password_plano=entrada.password,
        auditoria=contenedor.auditoria,
    )
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas. Verifique su usuario y contrasena.",
        )

    # Configurar cookie de sesion de servidor segura
    response.set_cookie(
        key=NOMBRE_COOKIE_SESION,
        value=sesion.token,
        httponly=True,
        samesite="strict",
        max_age=12 * 3600,  # 12 horas
    )

    return SalidaSesion(
        autenticado=True,
        username=sesion.username,
        nombre_completo=sesion.nombre_completo,
        rol=sesion.rol.value,
        rol_etiqueta=sesion.rol.etiqueta,
        establecimiento=sesion.establecimiento,
        id_paciente=sesion.id_paciente,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    contenedor: ContenedorDep,
) -> dict[str, str]:
    """Cierra la sesion del servidor e invalida la cookie."""
    token = request.cookies.get(NOMBRE_COOKIE_SESION) or ""
    gestor = obtener_gestor_auth()
    if token:
        gestor.cerrar_sesion(token, auditoria=contenedor.auditoria)

    response.delete_cookie(key=NOMBRE_COOKIE_SESION)
    return {"mensaje": "Sesion cerrada correctamente"}


@router.get("/sesion", response_model=SalidaSesion)
def consultar_sesion(request: Request) -> SalidaSesion:
    """Consulta la sesion activa actual."""
    sesion = obtener_sesion_actual(request)
    if sesion is None:
        return SalidaSesion(autenticado=False)

    return SalidaSesion(
        autenticado=True,
        username=sesion.username,
        nombre_completo=sesion.nombre_completo,
        rol=sesion.rol.value,
        rol_etiqueta=sesion.rol.etiqueta,
        establecimiento=sesion.establecimiento,
        id_paciente=sesion.id_paciente,
    )
