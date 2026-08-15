"""Registro de auditoria encadenado por hash. Solo se agrega; nada se edita.

POR QUE HACE FALTA
Hoy el acta de digitalizacion dice "Revisado por: Luis Huapaya" porque alguien
lo escribio en una caja de texto. Eso no significa nada: no hay usuario
autenticado, no hay constancia de que campo se cambio ni de que valor a cual, y
el acta se puede editar despues de firmada sin que nadie se entere.

Este modulo cierra lo segundo y lo tercero. Lo primero —autenticacion de verdad—
es otro problema y se declara pendiente en vez de fingirlo.

LA CADENA DE HASH
Cada entrada incluye el hash de la anterior. Si alguien borra o modifica una
fila intermedia, todas las posteriores dejan de verificar, y `verificar_cadena`
dice exactamente en cual se rompio.

No es criptografia fuerte ni pretende serlo: no impide que alguien con acceso a
la base reescriba la cadena entera. Lo que impide es la edicion silenciosa, que
es el escenario realista — alguien corrige un dato "para que cuadre" y no queda
rastro.

SOBRE LA IP Y LA MAC
Se registran como CONTEXTO, nunca como identidad:

  · La MAC es capa 2 y no atraviesa el router. Servido desde un servidor, este
    codigo veria la MAC del propio servidor, identica para todos los usuarios.
    Hoy "funciona" solo porque Streamlit corre en la misma maquina.
  · Los sistemas operativos aleatorizan la MAC en WiFi por defecto.
  · `uuid.getnode()` devuelve un numero ALEATORIO si no puede leerla, y hay que
    revisar el bit 41 para enterarse.
  · Y lo de fondo: identifican la maquina, no a la persona. En una estacion
    compartida del servicio, eso no sirve para una auditoria clinica.

Lo que el INSN usa de verdad para firmar esta impreso en su propia historia
clinica: firma digital con certificado (FAU). Ese es el camino de despliegue.
Aqui se deja el hash del contenido, que es el equivalente honesto para un MVP.
"""

from __future__ import annotations

import hashlib
import json
import socket
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

HASH_GENESIS = "0" * 64


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def contexto_de_maquina() -> dict[str, str]:
    """Metadato forense. NUNCA identidad.

    Se marca explicitamente si la MAC es aleatoria: el bit 41 del entero que
    devuelve `uuid.getnode()` esta a 1 cuando la libreria no pudo leer una MAC
    real y genero una. Registrar ese numero como si fuera un identificador de
    equipo seria registrar ruido con aspecto de dato.
    """
    nodo = uuid.getnode()
    mac_es_aleatoria = bool((nodo >> 40) & 1)
    try:
        host = socket.gethostname()
        ip = socket.gethostbyname(host)
    except OSError:
        host, ip = "desconocido", "desconocido"

    return {
        "hostname": host,
        "ip_local": ip,
        "mac": "aleatoria-no-fiable" if mac_es_aleatoria else f"{nodo:012x}",
        "advertencia": (
            "Contexto forense, no identidad. La MAC no atraviesa el router y "
            "los sistemas operativos la aleatorizan; la IP cambia con DHCP. "
            "Ninguno de los dos identifica a la persona que firmo."
        ),
    }


@dataclass(frozen=True, slots=True)
class EntradaAuditoria:
    """Una cosa que alguien hizo. Inmutable."""

    momento: str
    actor: str
    accion: str
    entidad: str
    entidad_id: str | None = None
    campo: str | None = None
    valor_antes: str | None = None
    valor_despues: str | None = None
    contexto: dict[str, Any] = field(default_factory=dict)

    def huella(self, hash_previo: str) -> str:
        """Hash de esta entrada encadenado con la anterior.

        El orden de los campos es fijo y `sort_keys=True`: si el hash dependiera
        del orden de un dict, la verificacion fallaria por motivos que no son
        manipulacion.
        """
        cuerpo = json.dumps(
            {
                "momento": self.momento,
                "actor": self.actor,
                "accion": self.accion,
                "entidad": self.entidad,
                "entidad_id": self.entidad_id,
                "campo": self.campo,
                "valor_antes": self.valor_antes,
                "valor_despues": self.valor_despues,
                "contexto": self.contexto,
                "hash_previo": hash_previo,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return _sha256(cuerpo)


@dataclass
class RegistroAuditoria:
    """Bitacora append-only sobre la tabla `auditoria`."""

    bd: Any  # BaseDatos

    def registrar(
        self,
        actor: str,
        accion: str,
        entidad: str,
        entidad_id: str | None = None,
        campo: str | None = None,
        valor_antes: str | None = None,
        valor_despues: str | None = None,
        contexto: dict[str, Any] | None = None,
    ) -> str:
        entrada = EntradaAuditoria(
            momento=datetime.now().isoformat(timespec="seconds"),
            actor=actor,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            campo=campo,
            valor_antes=valor_antes,
            valor_despues=valor_despues,
            contexto={**contexto_de_maquina(), **(contexto or {})},
        )
        with self.bd.conectar() as cx:
            ultimo = cx.execute(
                "SELECT hash FROM auditoria ORDER BY id DESC LIMIT 1"
            ).fetchone()
            previo = ultimo["hash"] if ultimo else HASH_GENESIS
            h = entrada.huella(previo)
            cx.execute(
                """INSERT INTO auditoria
                   (momento, actor, accion, entidad, entidad_id, campo,
                    valor_antes, valor_despues, contexto, hash_previo, hash)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    entrada.momento, entrada.actor, entrada.accion, entrada.entidad,
                    entrada.entidad_id, entrada.campo, entrada.valor_antes,
                    entrada.valor_despues,
                    json.dumps(entrada.contexto, ensure_ascii=False),
                    previo, h,
                ),
            )
        return h

    def registrar_correccion_humana(
        self, actor: str, documento_id: str, campo: str,
        valor_leido: str | None, valor_corregido: str,
    ) -> str:
        """La correccion de un campo por una persona.

        Es la contraparte de `AjusteCatalogo`: ese guarda que corrigio el
        sistema, este guarda que corrigio el humano. Sin los dos, un acta
        firmada no se puede auditar.
        """
        return self.registrar(
            actor=actor, accion="corregir_campo", entidad="digitalizacion",
            entidad_id=documento_id, campo=campo,
            valor_antes=valor_leido, valor_despues=valor_corregido,
        )

    def verificar_cadena(self) -> tuple[bool, int | None]:
        """(intacta, id_de_la_primera_rota).

        Recorre en orden recalculando cada hash. Si alguien edito o borro una
        fila, aqui aparece.
        """
        with self.bd.conectar() as cx:
            filas = cx.execute("SELECT * FROM auditoria ORDER BY id").fetchall()

        previo = HASH_GENESIS
        for f in filas:
            entrada = EntradaAuditoria(
                momento=f["momento"], actor=f["actor"], accion=f["accion"],
                entidad=f["entidad"], entidad_id=f["entidad_id"], campo=f["campo"],
                valor_antes=f["valor_antes"], valor_despues=f["valor_despues"],
                contexto=json.loads(f["contexto"]) if f["contexto"] else {},
            )
            if f["hash_previo"] != previo or entrada.huella(previo) != f["hash"]:
                return False, int(f["id"])
            previo = f["hash"]
        return True, None

    def de_entidad(self, entidad: str, entidad_id: str) -> list[dict[str, Any]]:
        with self.bd.conectar() as cx:
            filas = cx.execute(
                "SELECT * FROM auditoria WHERE entidad = ? AND entidad_id = ? "
                "ORDER BY id",
                (entidad, entidad_id),
            ).fetchall()
        return [dict(f) for f in filas]


def sello_de_contenido(campos: dict[str, Any]) -> str:
    """Hash de los campos validados. Va impreso al pie del acta.

    Sin esto, un acta firmada se puede editar despues y nadie se entera. Con
    esto, cualquiera puede recalcular el sello y comprobar que el documento
    dice lo mismo que decia cuando se firmo.

    Se imprimen los primeros 16 caracteres: suficiente para cotejar a ojo y no
    ocupa media pagina.
    """
    return _sha256(json.dumps(campos, sort_keys=True, ensure_ascii=False))
