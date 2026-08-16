"""BLOQUEANTE — el acceso del apoderado se corta el dia del cumpleanos 18.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTO NO ES UNA PANTALLA
═══════════════════════════════════════════════════════════════════════════════

Antes de los 18 el apoderado accede por patria potestad (Codigo Civil, arts.
418 y ss.). Desde el dia del cumpleanos esa base legal desaparece: el paciente
adquiere capacidad de ejercicio y sus datos de salud son datos sensibles suyos
(Ley 29733, art. 2.5).

El fallo que estos tests hacen imposible es concreto y es el que se comete
siempre: guardar `tiene_acceso: bool` en la base de datos. Ese booleano seguiria
valiendo True el dia despues del cumpleanos, y nadie se enteraria. Por eso la
base legal se CALCULA en cada consulta a partir de la fecha.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from relevo.dominio.entidades.acceso_apoderado import (
    AccesoApoderado,
    AccesoDenegado,
    BaseLegalAcceso,
    ConsentimientoExplicito,
)

NACIMIENTO = date(2008, 8, 16)
CUMPLE_18 = date(2026, 8, 16)


def acceso() -> AccesoApoderado:
    return AccesoApoderado(
        paciente_id="PAC-HUNTER",
        fecha_nacimiento_paciente=NACIMIENTO,
        nombre_apoderado="Rosa Quispe",
        parentesco="madre",
    )


# ═══════════════════════════════════════════════════════════════════════════
# La regla
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_sin_consentimiento_el_acceso_se_corta_el_dia_del_cumpleanios() -> None:
    """El corte es EN la fecha, no al dia siguiente ni el mes siguiente."""
    a = acceso()

    vispera = CUMPLE_18 - timedelta(days=1)
    assert a.tiene_acceso(vispera)
    assert a.base_legal(vispera) is BaseLegalAcceso.PATRIA_POTESTAD

    assert not a.tiene_acceso(CUMPLE_18)
    assert a.base_legal(CUMPLE_18) is BaseLegalAcceso.SIN_BASE

    with pytest.raises(AccesoDenegado):
        a.exigir_acceso(CUMPLE_18)


@pytest.mark.bloqueante
def test_el_acceso_no_se_guarda_como_booleano_sino_que_se_calcula() -> None:
    """El fallo clasico: un `tiene_acceso: bool` persistido seguiria valiendo
    True el dia despues del cumpleanos y nadie se enteraria.

    El mismo objeto, sin tocarlo, tiene que responder distinto en dos fechas.
    """
    a = acceso()
    assert a.tiene_acceso(CUMPLE_18 - timedelta(days=1))
    assert not a.tiene_acceso(CUMPLE_18)

    campos = {c for c in vars(a)}
    assert "tiene_acceso" not in campos
    assert "acceso_activo" not in campos


@pytest.mark.bloqueante
def test_con_consentimiento_explicito_el_acceso_continua() -> None:
    """La otra mitad de la regla: el paciente puede autorizarlo, y solo el."""
    a = acceso()
    a.otorgar(
        ConsentimientoExplicito(
            otorgado_por_paciente="Mateo Silva Quispe",
            fecha=CUMPLE_18 - timedelta(days=30),
            alcance="estado del ciclo de transicion",
            medio="en consulta, por escrito",
        )
    )

    assert a.tiene_acceso(CUMPLE_18)
    assert a.base_legal(CUMPLE_18) is BaseLegalAcceso.CONSENTIMIENTO_DEL_PACIENTE
    a.exigir_acceso(CUMPLE_18 + timedelta(days=365))


def test_un_consentimiento_con_fecha_futura_no_vale_todavia() -> None:
    a = acceso()
    a.otorgar(
        ConsentimientoExplicito(
            otorgado_por_paciente="Mateo Silva Quispe",
            fecha=CUMPLE_18 + timedelta(days=10),
        )
    )
    assert not a.tiene_acceso(CUMPLE_18)
    assert a.tiene_acceso(CUMPLE_18 + timedelta(days=10))


def test_revocar_corta_el_acceso_sin_borrar_el_registro() -> None:
    """Borrar el consentimiento haria imposible responder despues a "¿quien
    pudo ver esto y cuando?"."""
    a = acceso()
    a.otorgar(
        ConsentimientoExplicito(
            otorgado_por_paciente="Mateo Silva Quispe", fecha=CUMPLE_18
        )
    )
    revocacion = CUMPLE_18 + timedelta(days=100)
    a.revocar(revocacion)

    assert a.tiene_acceso(revocacion - timedelta(days=1))
    assert not a.tiene_acceso(revocacion)
    assert a.consentimiento is not None
    assert [tipo for tipo, _ in a.historial] == ["otorgado", "revocado"]


def test_no_se_revoca_lo_que_no_se_otorgo() -> None:
    """El acceso por patria potestad caduca solo. No hay nada que revocar."""
    with pytest.raises(AccesoDenegado):
        acceso().revocar(CUMPLE_18 - timedelta(days=10))


def test_un_consentimiento_sin_quien_lo_otorga_no_es_un_consentimiento() -> None:
    with pytest.raises(ValueError):
        ConsentimientoExplicito(otorgado_por_paciente="   ", fecha=CUMPLE_18)


# ═══════════════════════════════════════════════════════════════════════════
# El aviso: el corte no puede ser una sorpresa
# ═══════════════════════════════════════════════════════════════════════════


def test_se_avisa_con_noventa_dias_de_antelacion() -> None:
    """La familia tiene que poder hablarlo antes, no descubrirlo el dia que
    deja de funcionar. Noventa dias coincide con el horizonte del corte etario,
    de modo que las dos cuentas atras del sistema hablan de la misma ventana."""
    a = acceso()

    assert a.aviso_de_caducidad(CUMPLE_18 - timedelta(days=200)) is None

    aviso = a.aviso_de_caducidad(CUMPLE_18 - timedelta(days=60))
    assert aviso is not None
    assert "60 dias" in aviso


def test_despues_del_corte_el_aviso_explica_quien_puede_reactivarlo() -> None:
    aviso = acceso().aviso_de_caducidad(CUMPLE_18 + timedelta(days=5))
    assert aviso is not None
    assert "Solo el paciente" in aviso


def test_con_consentimiento_el_aviso_recuerda_que_se_puede_retirar() -> None:
    a = acceso()
    a.otorgar(
        ConsentimientoExplicito(
            otorgado_por_paciente="Mateo Silva Quispe", fecha=CUMPLE_18
        )
    )
    aviso = a.aviso_de_caducidad(CUMPLE_18 + timedelta(days=5))
    assert aviso is not None
    assert "puede retirarlo" in aviso


def test_cada_base_legal_dice_su_norma() -> None:
    """Sin la norma citada, "no puede usted ver esto" es una decision
    arbitraria del software."""
    for base in BaseLegalAcceso:
        assert base.norma.strip()
    assert "29733" in BaseLegalAcceso.CONSENTIMIENTO_DEL_PACIENTE.norma
    assert "418" in BaseLegalAcceso.PATRIA_POTESTAD.norma
