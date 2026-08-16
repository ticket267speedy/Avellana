"""Autenticacion institucional basada en sesiones de servidor y argon2id.

PLAN_TECNICO §8.3 / FUSION_RELEVO_INSTRUCCIONES §8.3:

═══════════════════════════════════════════════════════════════════════════════
POR QUE SESION DE SERVIDOR Y NO JWT
═══════════════════════════════════════════════════════════════════════════════

Un JWT va FIRMADO, no cifrado: su contenido es base64 y cualquiera lo lee.
Aporta integridad y autenticidad, no confidencialidad. La confidencialidad en
transito la da TLS, y la de reposo el cifrado del almacenamiento.

Elegimos sesion de servidor y no JWT porque la ventaja del JWT es no guardar
estado entre varios microservicios distribuidos, y aqui hay un unico servidor
institucional on-premise; y porque un JWT NO se puede revocar de forma inmediata
sin una lista negra que ya es estado del servidor (con lo cual se pierde lo unico
que se ganaba). Con sesion de servidor, expulsar a un usuario o revocar un acceso
es simplemente invalidar una sesion en memoria.

Cada inicio, cierre de sesion e intento fallido genera un asiento en la cadena
de hash de auditoria.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from relevo.interfaz.api.roles import Rol

NOMBRE_COOKIE_SESION = "relevo_sesion"
DURACION_SESION_HORAS = 12

_HASHER = PasswordHasher()


@dataclass(frozen=True, slots=True)
class Usuario:
    username: str
    nombre_completo: str
    rol: Rol
    password_hash: str
    establecimiento: str = ""
    id_paciente: str = ""


@dataclass(frozen=True, slots=True)
class Sesion:
    token: str
    username: str
    nombre_completo: str
    rol: Rol
    establecimiento: str
    id_paciente: str
    creada_en: datetime
    expira_en: datetime

    @property
    def esta_expirada(self) -> bool:
        return datetime.now(timezone.utc) > self.expira_en


# Usuarios institucionales de demostracion precargados con argon2id
USUARIOS_DEMO: dict[str, Usuario] = {
    "paciente_mateo": Usuario(
        username="paciente_mateo",
        nombre_completo="Mateo Silva Quispe",
        rol=Rol.PACIENTE,
        password_hash=_HASHER.hash("mateo18"),
        id_paciente="DEMO-0001",
    ),
    "apoderado_rosa": Usuario(
        username="apoderado_rosa",
        nombre_completo="Rosa Quispe (Madre/Apoderada)",
        rol=Rol.APODERADO,
        password_hash=_HASHER.hash("rosa18"),
        id_paciente="DEMO-0001",
    ),
    "dra_valdez": Usuario(
        username="dra_valdez",
        nombre_completo="Dra. Carmen Valdez (Coord. Transición INSN SB)",
        rol=Rol.PROFESIONAL_INSN,
        password_hash=_HASHER.hash("insn2026"),
        establecimiento="INSN San Borja",
    ),
    "dr_mendoza": Usuario(
        username="dr_mendoza",
        nombre_completo="Dr. Luis Mendoza (Medicina Adultos)",
        rol=Rol.PROFESIONAL_RECEPTOR,
        password_hash=_HASHER.hash("dosdemayo2026"),
        establecimiento="Hospital Nacional Dos de Mayo",
    ),
    "admin": Usuario(
        username="admin",
        nombre_completo="Administrador de Sistema Relevo",
        rol=Rol.ADMINISTRADOR,
        password_hash=_HASHER.hash("admin2026"),
    ),
}


class GestorAutenticacion:
    """Administra credenciales, verificacion argon2id y ciclo de vida de sesiones."""

    def __init__(self, usuarios: dict[str, Usuario] | None = None) -> None:
        self._usuarios: dict[str, Usuario] = dict(usuarios or USUARIOS_DEMO)
        self._sesiones_activas: dict[str, Sesion] = {}

    def autenticar(
        self,
        username: str,
        password_plano: str,
        auditoria: Any | None = None,
    ) -> Sesion | None:
        """Verifica credenciales con argon2id y emite una nueva sesion."""
        usuario = self._usuarios.get(username.strip().lower())
        if usuario is None:
            if auditoria is not None:
                # `registrar()` exige `actor`, `accion` y `entidad` en ese
                # orden. Las llamadas anteriores usaban nombres que no existen
                # en la firma real (`responsable`, `id_referencia`,
                # `detalles`), asi que lanzaban TypeError en cada intento — y
                # un `except Exception: pass` alrededor lo escondia. El
                # resultado: ningun inicio ni intento fallido de sesion llegaba
                # jamas a la cadena de auditoria, sin que nada lo delatara.
                auditoria.registrar(
                    actor="anonimo",
                    accion="intento_fallido_sesion",
                    entidad="sesion",
                    entidad_id=username,
                    contexto={"motivo": "usuario_no_encontrado"},
                )
            return None

        try:
            _HASHER.verify(usuario.password_hash, password_plano)
        except VerifyMismatchError:
            if auditoria is not None:
                auditoria.registrar(
                    actor=usuario.username,
                    accion="intento_fallido_sesion",
                    entidad="sesion",
                    entidad_id=usuario.username,
                    contexto={"motivo": "password_incorrecto", "rol": usuario.rol.value},
                )
            return None

        ahora = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        sesion = Sesion(
            token=token,
            username=usuario.username,
            nombre_completo=usuario.nombre_completo,
            rol=usuario.rol,
            establecimiento=usuario.establecimiento,
            id_paciente=usuario.id_paciente,
            creada_en=ahora,
            expira_en=ahora + timedelta(hours=DURACION_SESION_HORAS),
        )
        self._sesiones_activas[token] = sesion

        if auditoria is not None:
            auditoria.registrar(
                actor=usuario.username,
                accion="inicio_sesion",
                entidad="sesion",
                entidad_id=usuario.username,
                contexto={
                    "rol": usuario.rol.value,
                    "establecimiento": usuario.establecimiento,
                    "id_paciente": usuario.id_paciente,
                },
            )

        return sesion

    def crear_sesion_para_rol(
        self,
        rol: Rol,
        establecimiento: str | None = None,
        id_paciente: str | None = None,
    ) -> Sesion:
        """Crea una sesion rapida para el cambio de rol en la barra demo."""
        username_map = {
            Rol.PACIENTE: "paciente_mateo",
            Rol.APODERADO: "apoderado_rosa",
            Rol.PROFESIONAL_INSN: "dra_valdez",
            Rol.PROFESIONAL_RECEPTOR: "dr_mendoza",
            Rol.ADMINISTRADOR: "admin",
        }
        user = self._usuarios.get(username_map.get(rol, "admin"))
        ahora = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)

        est_final = (
            establecimiento
            if establecimiento is not None
            else (user.establecimiento if user else "")
        )
        pac_final = (
            id_paciente
            if id_paciente is not None
            else (user.id_paciente if user else "")
        )

        sesion = Sesion(
            token=token,
            username=user.username if user else rol.value,
            nombre_completo=user.nombre_completo if user else f"Usuario {rol.etiqueta}",
            rol=rol,
            establecimiento=est_final,
            id_paciente=pac_final,
            creada_en=ahora,
            expira_en=ahora + timedelta(hours=DURACION_SESION_HORAS),
        )
        self._sesiones_activas[token] = sesion
        return sesion

    def validar_token(self, token: str) -> Sesion | None:
        """Devuelve la sesion activa o None si no existe o expiro."""
        if not token:
            return None
        sesion = self._sesiones_activas.get(token)
        if sesion is None:
            return None
        if sesion.esta_expirada:
            self._sesiones_activas.pop(token, None)
            return None
        return sesion

    def cerrar_sesion(self, token: str, auditoria: Any | None = None) -> bool:
        """Invalida la sesion.

        Devuelve True si HABIA una sesion que cerrar, sin condicionarlo a que
        la auditoria este disponible: antes, sin `auditoria` (arranque sin
        persistencia), un cierre de sesion valido se reportaba como False.
        """
        sesion = self._sesiones_activas.pop(token, None)
        if sesion is None:
            return False
        if auditoria is not None:
            auditoria.registrar(
                actor=sesion.username,
                accion="cierre_sesion",
                entidad="sesion",
                entidad_id=sesion.username,
                contexto={"rol": sesion.rol.value},
            )
        return True
