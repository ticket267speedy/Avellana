"""Persistencia en SQLite. Un archivo, cero servidor, cero costo.

DECISION DE DISENO: documento indexado, no mapeo relacional completo
─────────────────────────────────────────────────────────────────────────────
Cada agregado se guarda como JSON en una columna, y solo se suben a columnas
propias los campos por los que de verdad se consulta o se ordena.

Por que asi y no una tabla por entidad:

  · El modelo de dominio todavia se mueve. Un mapeo relacional completo hay que
    reescribirlo cada vez que se agrega un campo, y a mitad de hackathon eso es
    tiempo tirado.
  · Se consulta por muy poco: id, cohorte, estado del semaforo, IUT, dias sin
    contacto. Todo eso son columnas indexadas aqui.
  · SQLite tiene JSON1 desde hace anios: si manana hace falta filtrar por algo
    que esta dentro del documento, se hace con `json_extract` sin migrar nada.

Lo que se pierde: integridad referencial declarativa y consultas relacionales
ricas. A este volumen —del orden de 10^2 pacientes al anio— no compensa.

MIGRAR A POSTGRES no obliga a tocar nada mas: este archivo implementa el mismo
puerto que `RepositorioPacientesMemoria`. Se escribe `repositorio_postgres.py`
y se cambia una linea en `interfaz/arranque.py`.

AVISO DE DESPLIEGUE: el dia que haya datos reales, este archivo NO puede vivir
en la maquina de nadie del equipo ni en un servicio en la nube fuera del
hospital. Va en infraestructura del INSN.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

# v1 -> v2: nueve estados del ciclo, y tres agregados nuevos —progreso de
# aprendizaje, conciliacion de medicacion y acceso del apoderado. La migracion
# de los estados persistidos vive en `migraciones.py`. Nada se borra.
ESQUEMA_VERSION = 2

_ESQUEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS esquema_version (
    version   INTEGER PRIMARY KEY,
    aplicado  TEXT NOT NULL
);

-- Un paciente. Las columnas sueltas son SOLO las que se consultan u ordenan;
-- el resto vive en `documento` y se lee con json_extract si hace falta.
CREATE TABLE IF NOT EXISTS paciente (
    id                TEXT PRIMARY KEY,
    fecha_nacimiento  TEXT NOT NULL,
    cohorte           TEXT,
    iut               REAL,
    estado_semaforo   TEXT,
    confianza         REAL,
    tiene_contacto    INTEGER NOT NULL DEFAULT 0,
    documento         TEXT NOT NULL,
    creado            TEXT NOT NULL,
    actualizado       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_paciente_iut     ON paciente(iut DESC);
CREATE INDEX IF NOT EXISTS ix_paciente_cohorte ON paciente(cohorte);
CREATE INDEX IF NOT EXISTS ix_paciente_estado  ON paciente(estado_semaforo);

CREATE TABLE IF NOT EXISTS ciclo (
    id            TEXT PRIMARY KEY,
    paciente_id   TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    estado        TEXT NOT NULL,
    fecha_estado  TEXT NOT NULL,
    cerrado       INTEGER NOT NULL DEFAULT 0,
    documento     TEXT NOT NULL,
    creado        TEXT NOT NULL,
    actualizado   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ciclo_paciente ON ciclo(paciente_id);
CREATE INDEX IF NOT EXISTS ix_ciclo_abierto  ON ciclo(cerrado, estado);

-- Registro de auditoria. SOLO INSERT: nada lo actualiza ni lo borra.
--
-- Es lo que convierte "Revisado por: Luis Huapaya" en algo que significa algo.
-- Cada fila encadena con la anterior por hash, de modo que borrar o editar una
-- fila intermedia rompe la cadena y se nota.
CREATE TABLE IF NOT EXISTS auditoria (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    momento       TEXT NOT NULL,
    actor         TEXT NOT NULL,
    accion        TEXT NOT NULL,
    entidad       TEXT NOT NULL,
    entidad_id    TEXT,
    campo         TEXT,
    valor_antes   TEXT,
    valor_despues TEXT,
    contexto      TEXT,
    hash_previo   TEXT NOT NULL,
    hash          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_auditoria_entidad ON auditoria(entidad, entidad_id);

-- Marca de la semilla: permite saber si la base es de demo y con que semilla
-- se genero, para poder reproducirla identica.
CREATE TABLE IF NOT EXISTS semilla (
    clave  TEXT PRIMARY KEY,
    valor  TEXT NOT NULL
);

-- ── v2 ──────────────────────────────────────────────────────────────────────

-- El recorrido Entrenate. Va en tabla propia y no dentro del documento del
-- paciente porque lo alimenta el PACIENTE, no el personal de salud: mezclarlo
-- con el expediente clinico invitaria a que alguien del INSN lo rellenara
-- "para que quede completo", y ahi el dato pierde todo su valor.
CREATE TABLE IF NOT EXISTS progreso_aprendizaje (
    paciente_id  TEXT PRIMARY KEY REFERENCES paciente(id) ON DELETE CASCADE,
    logradas     INTEGER NOT NULL DEFAULT 0,
    documento    TEXT NOT NULL,
    actualizado  TEXT NOT NULL
);

-- Casos de conciliacion de medicacion. `abierto` es columna propia porque es
-- la unica consulta que se hace: la cola de trabajo del equipo del INSN.
CREATE TABLE IF NOT EXISTS conciliacion (
    id             TEXT PRIMARY KEY,
    paciente_id    TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    abierto        INTEGER NOT NULL DEFAULT 1,
    discrepancias  INTEGER NOT NULL DEFAULT 0,
    documento      TEXT NOT NULL,
    creado         TEXT NOT NULL,
    actualizado    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_conciliacion_abierta ON conciliacion(abierto);

-- Acceso del apoderado. NO hay columna `tiene_acceso`: la base legal se
-- calcula en cada consulta a partir de la fecha. Un booleano persistido
-- seguiria valiendo 1 el dia despues del cumpleanos 18, que es exactamente el
-- fallo que el modulo de dominio existe para hacer imposible.
CREATE TABLE IF NOT EXISTS acceso_apoderado (
    id           TEXT PRIMARY KEY,
    paciente_id  TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    fecha_corte  TEXT NOT NULL,
    documento    TEXT NOT NULL,
    actualizado  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_acceso_paciente ON acceso_apoderado(paciente_id);
"""


class Serializable(Protocol):
    """Lo minimo que el repositorio necesita saber de un agregado."""

    id: str


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(valor: Any) -> str:
    """Serializa a JSON tolerando date, datetime, Enum y dataclass."""

    def por_defecto(o: Any) -> Any:
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if hasattr(o, "value"):  # Enum
            return o.value
        if hasattr(o, "__dataclass_fields__"):
            return {c: getattr(o, c) for c in o.__dataclass_fields__}
        if isinstance(o, (set, frozenset, tuple)):
            return list(o)
        return str(o)

    return json.dumps(valor, ensure_ascii=False, default=por_defecto)


@dataclass
class BaseDatos:
    """Conexion y esquema. Se crea sola la primera vez."""

    ruta: Path

    def __post_init__(self) -> None:
        """Crea el archivo y aplica el esquema si hace falta.

        Fuera del gestor de transacciones a proposito: `executescript` hace
        COMMIT implicito antes de ejecutar, asi que dentro de un BEGIN dejaria
        la transaccion cerrada y el COMMIT posterior fallaria.
        """
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        cx = sqlite3.connect(self.ruta)
        try:
            cx.executescript(_ESQUEMA)
            cx.execute(
                "INSERT OR IGNORE INTO esquema_version (version, aplicado) VALUES (?, ?)",
                (ESQUEMA_VERSION, _ahora()),
            )
            cx.commit()
        finally:
            cx.close()

    @contextmanager
    def conectar(self) -> Iterator[sqlite3.Connection]:
        cx = sqlite3.connect(self.ruta, isolation_level=None)
        cx.row_factory = sqlite3.Row
        try:
            cx.execute("BEGIN")
            yield cx
            # `in_transaction` porque algunas sentencias (executescript, DDL en
            # ciertas versiones) hacen COMMIT implicito: sin comprobarlo,
            # el COMMIT de aqui reventaria con "no transaction is active".
            if cx.in_transaction:
                cx.execute("COMMIT")
        except Exception:
            if cx.in_transaction:
                cx.execute("ROLLBACK")
            raise
        finally:
            cx.close()

    # ── Reinicio ─────────────────────────────────────────────────────────────

    def vaciar(self, conservar_auditoria: bool = False) -> None:
        """Borra los datos y deja el esquema.

        `conservar_auditoria=True` respeta el registro de auditoria, que es lo
        correcto si algun dia esto corre con datos reales: un log de auditoria
        que se puede borrar no es un log de auditoria.

        En demo se borra todo, para que cada corrida arranque igual.
        """
        tablas = [
            "conciliacion",
            "acceso_apoderado",
            "progreso_aprendizaje",
            "ciclo",
            "paciente",
            "semilla",
        ]
        if not conservar_auditoria:
            tablas.append("auditoria")
        with self.conectar() as cx:
            for t in tablas:
                cx.execute(f"DELETE FROM {t}")
            cx.execute("DELETE FROM sqlite_sequence WHERE name='auditoria'")

    def marcar_semilla(self, datos: dict[str, str]) -> None:
        with self.conectar() as cx:
            for k, v in datos.items():
                cx.execute(
                    "INSERT OR REPLACE INTO semilla (clave, valor) VALUES (?, ?)",
                    (k, str(v)),
                )

    def info_semilla(self) -> dict[str, str]:
        with self.conectar() as cx:
            return {r["clave"]: r["valor"] for r in cx.execute("SELECT * FROM semilla")}

    def contar(self) -> dict[str, int]:
        with self.conectar() as cx:
            return {
                t: cx.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
                for t in ("paciente", "ciclo", "auditoria")
            }


@dataclass
class RepositorioPacientesSQLite:
    """Implementa el puerto `RepositorioPacientes` sobre SQLite.

    `a_documento` y `desde_documento` se inyectan: el repositorio no conoce la
    forma interna del agregado, solo como serializarlo. Asi un cambio en el
    dominio no obliga a tocar SQL.
    """

    bd: BaseDatos
    a_documento: Any  # Callable[[Paciente], dict]
    desde_documento: Any  # Callable[[dict], Paciente]

    def guardar(self, paciente: Any, indices: dict[str, Any] | None = None) -> None:
        ix = indices or {}
        doc = self.a_documento(paciente)
        ahora = _ahora()
        with self.bd.conectar() as cx:
            cx.execute(
                """
                INSERT INTO paciente (id, fecha_nacimiento, cohorte, iut,
                                      estado_semaforo, confianza, tiene_contacto,
                                      documento, creado, actualizado)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    fecha_nacimiento = excluded.fecha_nacimiento,
                    cohorte          = excluded.cohorte,
                    iut              = excluded.iut,
                    estado_semaforo  = excluded.estado_semaforo,
                    confianza        = excluded.confianza,
                    tiene_contacto   = excluded.tiene_contacto,
                    documento        = excluded.documento,
                    actualizado      = excluded.actualizado
                """,
                (
                    paciente.id,
                    str(ix.get("fecha_nacimiento", doc.get("fecha_nacimiento", ""))),
                    ix.get("cohorte"),
                    ix.get("iut"),
                    ix.get("estado_semaforo"),
                    ix.get("confianza"),
                    int(bool(ix.get("tiene_contacto", False))),
                    _json(doc),
                    ahora,
                    ahora,
                ),
            )

    def obtener(self, paciente_id: str) -> Any | None:
        with self.bd.conectar() as cx:
            fila = cx.execute(
                "SELECT documento FROM paciente WHERE id = ?", (paciente_id,)
            ).fetchone()
        return self.desde_documento(json.loads(fila["documento"])) if fila else None

    def todos(self) -> tuple[Any, ...]:
        with self.bd.conectar() as cx:
            filas = cx.execute("SELECT documento FROM paciente ORDER BY id").fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)

    def por_estado(self, estado: str) -> tuple[Any, ...]:
        """Consulta por columna indexada: no deserializa lo que no hace falta."""
        with self.bd.conectar() as cx:
            filas = cx.execute(
                "SELECT documento FROM paciente WHERE estado_semaforo = ? "
                "ORDER BY iut DESC",
                (estado,),
            ).fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)

    def priorizados(self, limite: int | None = None) -> tuple[Any, ...]:
        sql = "SELECT documento FROM paciente ORDER BY iut DESC"
        if limite:
            sql += f" LIMIT {int(limite)}"
        with self.bd.conectar() as cx:
            filas = cx.execute(sql).fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)

    def eliminar(self, paciente_id: str) -> None:
        with self.bd.conectar() as cx:
            cx.execute("DELETE FROM paciente WHERE id = ?", (paciente_id,))


@dataclass
class RepositorioCiclosSQLite:
    """Igual que el de pacientes, para los ciclos de transicion."""

    bd: BaseDatos
    a_documento: Any
    desde_documento: Any

    def guardar(self, ciclo: Any, indices: dict[str, Any] | None = None) -> None:
        ix = indices or {}
        doc = self.a_documento(ciclo)
        ahora = _ahora()
        with self.bd.conectar() as cx:
            cx.execute(
                """
                INSERT INTO ciclo (id, paciente_id, estado, fecha_estado, cerrado,
                                   documento, creado, actualizado)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    estado       = excluded.estado,
                    fecha_estado = excluded.fecha_estado,
                    cerrado      = excluded.cerrado,
                    documento    = excluded.documento,
                    actualizado  = excluded.actualizado
                """,
                (
                    # Un ciclo no tiene identificador propio: hay uno por
                    # paciente y el paciente ya lo identifica. Se admite un
                    # `id` explicito en los indices para el dia que un paciente
                    # tenga dos ciclos —un reingreso hacia otro destino—, pero
                    # mientras no lo haya, inventar una clave sinteticaria una
                    # entidad que no existe.
                    ix.get("id", getattr(ciclo, "id", None))
                    or getattr(ciclo, "paciente_id", ""),
                    ix.get("paciente_id", getattr(ciclo, "paciente_id", "")),
                    str(ix.get("estado", "")),
                    str(ix.get("fecha_estado", "")),
                    int(bool(ix.get("cerrado", False))),
                    _json(doc),
                    ahora,
                    ahora,
                ),
            )

    def abiertos(self) -> tuple[Any, ...]:
        with self.bd.conectar() as cx:
            filas = cx.execute(
                "SELECT documento FROM ciclo WHERE cerrado = 0 ORDER BY fecha_estado"
            ).fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)

    def de_paciente(self, paciente_id: str) -> tuple[Any, ...]:
        with self.bd.conectar() as cx:
            filas = cx.execute(
                "SELECT documento FROM ciclo WHERE paciente_id = ?", (paciente_id,)
            ).fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)

    def todos(self) -> tuple[Any, ...]:
        with self.bd.conectar() as cx:
            filas = cx.execute("SELECT documento FROM ciclo ORDER BY id").fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)


@dataclass
class RepositorioDocumentos:
    """Almacen generico de agregados por paciente, sobre una tabla cualquiera.

    Lo usan los tres agregados que llegaron con la fusion —progreso de
    aprendizaje, conciliacion y acceso del apoderado— porque los tres tienen la
    misma forma de acceso: guardar por clave, leer por paciente. Escribir tres
    repositorios identicos habria sido triplicar el mismo SQL para no ganar
    nada.

    `columnas_extra` recibe las columnas indexadas de cada tabla, que son las
    unicas que difieren. Igual que en los otros repositorios: solo se sube a
    columna lo que de verdad se consulta.
    """

    bd: BaseDatos
    tabla: str
    a_documento: Any
    desde_documento: Any
    columna_clave: str = "id"

    def guardar(
        self, clave: str, agregado: Any, columnas_extra: dict[str, Any] | None = None
    ) -> None:
        extra = columnas_extra or {}
        doc = self.a_documento(agregado)
        ahora = _ahora()
        campos = [self.columna_clave, *extra.keys(), "documento", "actualizado"]
        valores = [clave, *extra.values(), _json(doc), ahora]
        marcas = ",".join("?" for _ in campos)
        actualizaciones = ",".join(
            f"{c} = excluded.{c}" for c in campos if c != self.columna_clave
        )
        with self.bd.conectar() as cx:
            cx.execute(
                f"INSERT INTO {self.tabla} ({','.join(campos)}) VALUES ({marcas}) "
                f"ON CONFLICT({self.columna_clave}) DO UPDATE SET {actualizaciones}",
                tuple(valores),
            )

    def obtener(self, clave: str) -> Any | None:
        with self.bd.conectar() as cx:
            fila = cx.execute(
                f"SELECT documento FROM {self.tabla} WHERE {self.columna_clave} = ?",
                (clave,),
            ).fetchone()
        return self.desde_documento(json.loads(fila["documento"])) if fila else None

    def de_paciente(self, paciente_id: str) -> tuple[Any, ...]:
        with self.bd.conectar() as cx:
            filas = cx.execute(
                f"SELECT documento FROM {self.tabla} WHERE paciente_id = ?",
                (paciente_id,),
            ).fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)

    def todos(self) -> tuple[Any, ...]:
        with self.bd.conectar() as cx:
            filas = cx.execute(
                f"SELECT documento FROM {self.tabla} ORDER BY {self.columna_clave}"
            ).fetchall()
        return tuple(self.desde_documento(json.loads(f["documento"])) for f in filas)
