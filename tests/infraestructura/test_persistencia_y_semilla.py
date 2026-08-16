"""La base persiste, la semilla es determinista y la auditoria se llama sola.

Tres cosas que hasta la fusion estaban construidas y no enchufadas:

1. `app.py` importaba CERO modulos de infraestructura, asi que nada de lo
   construido corria de verdad.
2. `contenedor.sembrar_demo()` lo llamaba `sembrar.py` y no existia.
3. La cadena de hash de auditoria funcionaba y estaba probada, pero no la
   llamaba nadie.

Lo que se comprueba aqui es que las tres esten conectadas — no que funcionen,
que ya se sabia, sino que ALGUIEN LAS USE.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from relevo.dominio.entidades.ciclo_transicion import EstadoCiclo
from relevo.interfaz.arranque import construir

HOY = date(2026, 8, 16)


@pytest.fixture
def contenedor(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Un sistema completo sobre una base temporal.

    Base temporal y no la del proyecto: un test que escribe en `data/relevo.db`
    destruiria la cohorte que el equipo tiene preparada para ensayar el pitch.
    """
    return construir(persistente=True, ruta_bd=tmp_path / "prueba.db")


def _sembrar(contenedor, hoy: date = HOY) -> dict[str, int]:  # type: ignore[no-untyped-def]
    return contenedor.sembrar_demo(
        n_pacientes=42,
        semilla_aleatoria=20260816,
        hoy=hoy,
        ciclos_abiertos=18,
        reparto_estados={},
        vencidos_forzados=3,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Que la siembra exista y persista
# ═══════════════════════════════════════════════════════════════════════════


def test_sembrar_demo_existe_y_devuelve_lo_que_el_cli_espera(contenedor) -> None:  # type: ignore[no-untyped-def]
    """`sembrar.py` lleva desde el cierre del MVP llamando a un metodo que no
    existia."""
    resultado = _sembrar(contenedor)

    assert set(resultado) >= {"pacientes", "ciclos", "vencidos"}
    assert resultado["pacientes"] == 42
    assert resultado["ciclos"] > 0


def test_cerrar_y_reabrir_no_borra_los_pacientes(tmp_path: Path) -> None:
    """El criterio de aceptacion literal del cierre del MVP: cerrar la app,
    reabrirla, y que los pacientes sigan ahi.

    Si la demo no persiste, no es la demo de un sistema: es la de una pantalla.
    """
    ruta = tmp_path / "persiste.db"
    primero = construir(persistente=True, ruta_bd=ruta)
    _sembrar(primero)
    ids_antes = {p.id for p in primero.pacientes()}

    # Otro contenedor, como si se hubiera reiniciado el proceso.
    segundo = construir(persistente=True, ruta_bd=ruta)

    assert {p.id for p in segundo.pacientes()} == ids_antes
    assert len(segundo.ciclos()) == len(primero.ciclos())


def test_dos_siembras_producen_la_misma_cohorte(tmp_path: Path) -> None:
    """Misma semilla = misma cohorte. Si no, hay una fuente de aleatoriedad sin
    sembrar, y el ensayo del pitch deja de ser reproducible."""
    uno = construir(persistente=True, ruta_bd=tmp_path / "a.db")
    dos = construir(persistente=True, ruta_bd=tmp_path / "b.db")
    _sembrar(uno)
    _sembrar(dos)

    def huella(contenedor) -> list[tuple[str, str, str]]:  # type: ignore[no-untyped-def]
        return sorted(
            (p.id, p.fecha_nacimiento.isoformat(), str(p.diagnostico_principal))
            for p in contenedor.pacientes()
        )

    assert huella(uno) == huella(dos)


# ═══════════════════════════════════════════════════════════════════════════
# Los dos casos con nombre
# ═══════════════════════════════════════════════════════════════════════════


def test_el_caso_protagonista_es_hunter_y_tiene_17_anios_y_4_meses(contenedor) -> None:  # type: ignore[no-untyped-def]
    """Un unico valor de edad en documentos, codigo y diapositivas."""
    _sembrar(contenedor)
    mateo = contenedor.paciente("DEMO-0001")

    assert mateo is not None
    assert mateo.edad(HOY) == 17
    assert mateo.ventana(HOY).meses_restantes == 8  # 17 anios y 4 meses
    principal = mateo.diagnostico_principal
    assert principal is not None
    assert principal.codigo.valor.startswith("E76.1")
    assert principal.es_raro


def test_la_dosis_de_idursulfasa_no_esta_inventada(contenedor) -> None:  # type: ignore[no-untyped-def]
    """REGLA 8. Sale como hueco en el Pasaporte, no como un numero plausible."""
    _sembrar(contenedor)
    mateo = contenedor.paciente("DEMO-0001")
    assert mateo is not None

    idursulfasa = next(m for m in mateo.medicamentos if m.nombre == "Idursulfasa")
    assert idursulfasa.dosis is None
    assert idursulfasa.requiere_completar_manualmente
    assert "____" in idursulfasa.texto_seguro()


def test_hay_un_caso_de_contraste_con_destino(contenedor) -> None:  # type: ignore[no-untyped-def]
    """Sin el, "sin destino identificado" se lee como un fallo del software y
    no como el hallazgo del sistema de salud que es."""
    _sembrar(contenedor)
    lucia = contenedor.paciente("DEMO-0002")
    ciclo = contenedor.ciclo_de("DEMO-0002")

    assert lucia is not None
    assert ciclo is not None
    assert ciclo.estado is EstadoCiclo.ACEPTADO_CON_SERVICIO
    assert ciclo.tiene_destino_asegurado
    assert ciclo.servicio_asignado


# ═══════════════════════════════════════════════════════════════════════════
# La auditoria, por fin llamada
# ═══════════════════════════════════════════════════════════════════════════


def test_guardar_un_ciclo_deja_rastro_en_la_auditoria(contenedor) -> None:  # type: ignore[no-untyped-def]
    """La cadena de hash funcionaba y estaba probada. Faltaba que alguien la
    llamara."""
    _sembrar(contenedor)

    assert contenedor.auditoria is not None
    entradas = contenedor.auditoria.de_entidad("ciclo", "DEMO-0001")
    assert entradas, "guardar un ciclo no dejo rastro"
    assert entradas[0]["accion"] == "avanzar_ciclo"
    # El responsable va en el contexto: es la respuesta a "¿de quien era el
    # turno cuando esto paso?".
    assert "responsable" in entradas[0]["contexto"]


def test_la_cadena_de_auditoria_verifica_tras_sembrar(contenedor) -> None:  # type: ignore[no-untyped-def]
    _sembrar(contenedor)
    intacta, rota = contenedor.verificar_auditoria()
    assert intacta and rota is None


def test_editar_una_fila_por_sql_rompe_la_cadena(contenedor) -> None:  # type: ignore[no-untyped-def]
    """La respuesta a "¿quien vigila al vigilante?".

    Quien administre el servidor tendra acceso al archivo SQLite —eso es
    inevitable— y por eso la cadena de hash existe: si toca una fila por fuera,
    esto lo delata.
    """
    _sembrar(contenedor)
    assert contenedor.bd is not None

    with contenedor.bd.conectar() as cx:
        cx.execute("UPDATE auditoria SET actor = 'otro' WHERE id = 1")

    intacta, rota = contenedor.verificar_auditoria()
    assert not intacta
    assert rota == 1


# ═══════════════════════════════════════════════════════════════════════════
# Migracion
# ═══════════════════════════════════════════════════════════════════════════


def test_un_ciclo_persistido_con_estados_viejos_se_migra_sin_borrarse(
    tmp_path: Path,
) -> None:
    """Nada se borra para simplificar la migracion."""
    from relevo.infraestructura.persistencia.migraciones import migrar
    from relevo.infraestructura.persistencia.repositorio_sqlite import (
        ESQUEMA_VERSION,
        BaseDatos,
    )

    ruta = tmp_path / "vieja.db"
    bd = BaseDatos(ruta)
    with bd.conectar() as cx:
        cx.execute(
            "INSERT INTO paciente (id, fecha_nacimiento, documento, creado, "
            "actualizado) VALUES ('PAC-V','2008-01-01','{}','x','x')"
        )
        cx.execute(
            "INSERT INTO ciclo (id, paciente_id, estado, fecha_estado, documento, "
            "creado, actualizado) VALUES (?,?,?,?,?,?,?)",
            (
                "PAC-V",
                "PAC-V",
                "REFERENCIA_ACEPTADA",
                "2025-03-05",
                '{"paciente_id":"PAC-V","fecha_inicio":"2025-01-10","historial":'
                '[{"estado":"PASAPORTE_EMITIDO","fecha":"2025-01-10"},'
                '{"estado":"REFERENCIA_ACEPTADA","fecha":"2025-03-05"}]}',
                "x",
                "x",
            ),
        )

    informe = migrar(bd, ESQUEMA_VERSION)

    assert informe.ciclos_traducidos == 1
    assert "REFERENCIA_ACEPTADA" in informe.estados_encontrados

    with bd.conectar() as cx:
        fila = cx.execute("SELECT estado, documento FROM ciclo").fetchone()
    assert fila["estado"] == EstadoCiclo.ACEPTADO_CON_SERVICIO.value
    assert "PASAPORTE_EMITIDO" not in fila["documento"]
    assert "preparacion" in fila["documento"]

    # Idempotente: correrla otra vez no cambia nada.
    segunda = migrar(bd, ESQUEMA_VERSION)
    assert segunda.ciclos_traducidos == 0
