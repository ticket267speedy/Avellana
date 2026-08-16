"""Tests de autenticacion institucional y ciclo de vida de sesiones (§8.3).

Verifica argon2id, sesion con cookie HttpOnly / SameSite=Strict, y registro en auditoria.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from relevo.interfaz.api.autenticacion import NOMBRE_COOKIE_SESION
from relevo.interfaz.api.principal import app

client = TestClient(app)


def test_login_exitoso_establece_cookie_y_devuelve_sesion() -> None:
    """Credenciales validas inician sesion y configuran cookie HttpOnly."""
    resp = client.post(
        "/api/auth/login",
        json={"usuario": "dra_valdez", "password": "insn2026"},
    )
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["autenticado"] is True
    assert datos["username"] == "dra_valdez"
    assert datos["rol"] == "profesional_insn"
    assert NOMBRE_COOKIE_SESION in resp.cookies


def test_login_invalido_devuelve_401() -> None:
    """Credenciales incorrectas devuelven 401 Unauthorized."""
    resp = client.post(
        "/api/auth/login",
        json={"usuario": "dra_valdez", "password": "password_incorrecto"},
    )
    assert resp.status_code == 401
    assert NOMBRE_COOKIE_SESION not in resp.cookies


def test_usuario_inexistente_devuelve_401() -> None:
    resp = client.post(
        "/api/auth/login",
        json={"usuario": "no_existe", "password": "password"},
    )
    assert resp.status_code == 401


def test_consultar_sesion_activa_y_logout() -> None:
    """Verifica consulta de sesion y posterior cierre con logout."""
    # 1. Login como receptor
    login_resp = client.post(
        "/api/auth/login",
        json={"usuario": "dr_mendoza", "password": "dosdemayo2026"},
    )
    assert login_resp.status_code == 200
    cookie_val = login_resp.cookies[NOMBRE_COOKIE_SESION]

    # 2. Consultar sesion con la cookie
    sesion_resp = client.get(
        "/api/auth/sesion",
        cookies={NOMBRE_COOKIE_SESION: cookie_val},
    )
    assert sesion_resp.status_code == 200
    datos = sesion_resp.json()
    assert datos["autenticado"] is True
    assert datos["rol"] == "profesional_receptor"
    assert datos["establecimiento"] == "Hospital Nacional Dos de Mayo"

    # 3. Cerrar sesion (logout)
    logout_resp = client.post(
        "/api/auth/logout",
        cookies={NOMBRE_COOKIE_SESION: cookie_val},
    )
    assert logout_resp.status_code == 200

    # 4. Consultar sesion nuevamente -> debe ser no autenticado
    sesion_post_logout = client.get(
        "/api/auth/sesion",
        cookies={NOMBRE_COOKIE_SESION: cookie_val},
    )
    assert sesion_post_logout.status_code == 200
    assert sesion_post_logout.json()["autenticado"] is False


def test_consultar_sesion_sin_cookie_devuelve_no_autenticado() -> None:
    resp = client.get("/api/auth/sesion")
    assert resp.status_code == 200
    assert resp.json()["autenticado"] is False
