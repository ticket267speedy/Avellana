"""BLOQUEANTE — el receptor solo ve las referencias dirigidas a su establecimiento.

═══════════════════════════════════════════════════════════════════════════════
POR QUE PROFESIONAL_INSN Y PROFESIONAL_RECEPTOR NO SON EL MISMO ROL
═══════════════════════════════════════════════════════════════════════════════

Estan en instituciones distintas. Unificarlos le daria al receptor visibilidad
sobre toda la cohorte pediatrica del INSN, que es exactamente el problema de
proteccion de datos que decimos evitar: un medico del Hospital Dos de Mayo no
tiene ninguna base legal para ver el expediente de un paciente que nunca le fue
referido.

═══════════════════════════════════════════════════════════════════════════════
Y POR QUE 404 Y NO 403
═══════════════════════════════════════════════════════════════════════════════

Un 403 CONFIRMA QUE EL PACIENTE EXISTE. Con eso, cualquiera con una cuenta de
receptor podria averiguar, probando identificadores, quienes estan en la
cohorte pediatrica del INSN — sin llegar a ver un solo dato clinico y sin
romper ninguna comprobacion de permisos.

La fuga por codigo de estado es de las mas faciles de introducir sin darse
cuenta, y de las que un jurado tecnico pregunta.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

OTRO_HOSPITAL = "HOSPITAL NACIONAL ARZOBISPO LOAYZA"


@pytest.fixture
def otro_receptor() -> dict[str, str]:
    """Un profesional de un establecimiento al que no se refirio nada."""
    return {
        "X-Relevo-Rol": "profesional_receptor",
        "X-Relevo-Establecimiento": OTRO_HOSPITAL,
    }


# ═══════════════════════════════════════════════════════════════════════════
# La regla
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_un_receptor_ajeno_recibe_404_y_no_403(
    cliente: TestClient, otro_receptor: dict[str, str]
) -> None:
    """El paciente DEMO-0001 existe y fue referido a otro hospital.

    404 y no 403: un 403 confirmaria su existencia.
    """
    respuesta = cliente.get("/api/pacientes/DEMO-0001/ciclo", headers=otro_receptor)

    assert respuesta.status_code == 404, (
        f"Respondio {respuesta.status_code}. Un 403 confirmaria que el paciente "
        "existe, y con eso se puede enumerar la cohorte pediatrica del INSN "
        "probando identificadores."
    )


@pytest.mark.bloqueante
def test_el_404_del_ajeno_es_indistinguible_del_de_un_id_inventado(
    cliente: TestClient, otro_receptor: dict[str, str]
) -> None:
    """La comprobacion de verdad: los dos casos tienen que ser IGUALES.

    Si el cuerpo, la cabecera o el codigo difirieran, la fuga seguiria abierta
    aunque los dos devolvieran 404.
    """
    ajeno = cliente.get("/api/pacientes/DEMO-0001/ciclo", headers=otro_receptor)
    inventado = cliente.get("/api/pacientes/NO-EXISTE-JAMAS/ciclo", headers=otro_receptor)

    assert ajeno.status_code == inventado.status_code
    assert ajeno.json() == inventado.json()


@pytest.mark.bloqueante
def test_el_receptor_correcto_si_ve_su_referencia(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """La otra mitad: el aislamiento tiene que dejar pasar a quien corresponde,
    o no seria aislamiento sino un muro."""
    respuesta = cliente.get("/api/pacientes/DEMO-0001/ciclo", headers=receptor)
    assert respuesta.status_code == 200
    assert respuesta.json()["paciente_id"] == "DEMO-0001"


@pytest.mark.bloqueante
def test_la_bandeja_de_un_receptor_ajeno_sale_vacia(
    cliente: TestClient, otro_receptor: dict[str, str]
) -> None:
    respuesta = cliente.get("/api/receptor/bandeja", headers=otro_receptor)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


@pytest.mark.bloqueante
def test_un_receptor_sin_establecimiento_declarado_no_ve_nada(
    cliente: TestClient
) -> None:
    """Si la cabecera falta por un error, el fallo tiene que dejar ver MENOS."""
    sin_establecimiento = {"X-Relevo-Rol": "profesional_receptor"}

    assert (
        cliente.get(
            "/api/pacientes/DEMO-0001/ciclo", headers=sin_establecimiento
        ).status_code
        == 404
    )
    assert (
        cliente.get("/api/receptor/bandeja", headers=sin_establecimiento).status_code
        == 400
    )


@pytest.mark.bloqueante
def test_un_receptor_ajeno_no_puede_actuar_sobre_un_ciclo_que_no_es_suyo(
    cliente: TestClient, otro_receptor: dict[str, str]
) -> None:
    """El aislamiento vale para escritura igual que para lectura. Si solo
    filtrara las lecturas, bastaria un POST a ciegas para mover el ciclo de un
    paciente de otro hospital."""
    respuesta = cliente.post(
        "/api/receptor/DEMO-0001/confirmar_recepcion",
        headers=otro_receptor,
        json={"quien": "intruso"},
    )
    assert respuesta.status_code == 404


@pytest.mark.bloqueante
def test_el_receptor_no_tiene_acceso_al_radar_de_la_cohorte(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """El receptor tiene bandeja, no radar. Darle la cohorte entera del INSN es
    el problema de proteccion de datos que decimos evitar.

    Aqui SI es 403 y no 404, y la diferencia es deliberada: el radar existe
    —no es un secreto que exista— y lo que se le niega es el acceso, no su
    existencia. El 404 protege la identidad de un paciente concreto; aqui no
    hay ninguna identidad que proteger.
    """
    assert cliente.get("/api/pacientes", headers=receptor).status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# El administrador: sin lectura clinica
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_el_administrador_no_abre_un_pasaporte_ni_una_historia(
    cliente: TestClient, administrador: dict[str, str]
) -> None:
    """Puede administrar el sistema; no puede leer expedientes."""
    for ruta in (
        "/api/pacientes",
        "/api/pacientes/DEMO-0001",
        "/api/pacientes/DEMO-0001/pasaporte",
        "/api/pacientes/DEMO-0001/aprendizaje",
    ):
        respuesta = cliente.get(ruta, headers=administrador)
        assert respuesta.status_code == 403, f"{ruta} respondio {respuesta.status_code}"


def test_el_administrador_si_ve_metricas_agregadas_y_la_cadena(
    cliente: TestClient, administrador: dict[str, str]
) -> None:
    """No hay dato clinico en un recuento.

    Y la verificacion de la cadena es justamente su trabajo: es la respuesta a
    "¿quien vigila al vigilante?". Su acceso al archivo SQLite es inevitable;
    lo que la cadena garantiza es que si toca algo, se nota.
    """
    assert (
        cliente.get("/api/metricas/corte-etario", headers=administrador).status_code
        == 200
    )
    estado = cliente.get("/api/demo/estado", headers=administrador)
    assert estado.status_code == 200
    assert estado.json()["cadena_intacta"] is True


# ═══════════════════════════════════════════════════════════════════════════
# El defecto seguro
# ═══════════════════════════════════════════════════════════════════════════


def test_sin_cabecera_de_rol_se_asume_el_rol_con_menos_alcance(
    cliente: TestClient,
) -> None:
    """Por defecto PACIENTE y no ADMINISTRADOR: si la cabecera falta por un
    error, el fallo tiene que dejar ver menos, nunca mas."""
    respuesta = cliente.get("/api/pacientes/DEMO-0001", headers={})
    assert respuesta.status_code == 200

    # Un valor invalido cae al mismo sitio, no a uno privilegiado.
    invalido = cliente.get(
        "/api/pacientes", headers={"X-Relevo-Rol": "jefe_supremo"}
    )
    assert invalido.status_code == 200  # cae a PACIENTE, que si puede leer
