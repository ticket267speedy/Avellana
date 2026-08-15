"""El motor anti-error-silencioso.

Cada test responde una pregunta que un jurado clinico puede hacer en voz alta.
No hay mocks, ni base de datos, ni red, ni imagenes: es dominio puro.
"""

from __future__ import annotations

from datetime import date

import pytest

from relevo.dominio.objetos_valor.campo_extraido import EstadoCampo, Motivo
from relevo.dominio.servicios.verificador_extraccion import (
    EspecificacionCampo,
    VerificadorExtraccion,
    distancia_edicion,
    medir,
    regla_edad_coherente_con_nacimiento,
)

CIE10 = ("E84.0", "E84.1", "E10.9", "N18.5", "Q21.3", "G80.9", "D57.1", "K86.8")
ESPECIALIDADES = ("Pediatria", "Medicina", "Cirugia", "Gineco-Obst", "Laboratorio")


@pytest.fixture
def specs() -> dict[str, EspecificacionCampo]:
    return {
        "dni": EspecificacionCampo("dni", "DNI", patron=r"\d{8}", descripcion_formato="ocho digitos"),
        "celular": EspecificacionCampo("celular", "Celular", patron=r"9\d{8}", obligatorio=False),
        "fecha_nacimiento": EspecificacionCampo("fecha_nacimiento", "F. nacimiento", patron=r"\d{2}/\d{2}/\d{4}"),
        "edad_anios": EspecificacionCampo("edad_anios", "Edad", patron=r"\d{1,2}"),
        "cie10_1": EspecificacionCampo("cie10_1", "CIE-10", catalogo=CIE10, distancia_maxima=2.0),
        "especialidad": EspecificacionCampo("especialidad", "Especialidad", catalogo=ESPECIALIDADES, distancia_maxima=3.0),
    }


@pytest.fixture
def verificador(specs) -> VerificadorExtraccion:
    return VerificadorExtraccion(
        especificaciones=specs,
        reglas_cruzadas=(regla_edad_coherente_con_nacimiento(hoy=date(2026, 8, 14)),),
    )


@pytest.fixture
def verdad() -> dict[str, str]:
    return {
        "dni": "71234567",
        "celular": "987654321",
        "fecha_nacimiento": "14/03/2009",
        "edad_anios": "17",
        "cie10_1": "E84.0",
        "especialidad": "Pediatria",
    }


# ── distancia ponderada por confusiones de lectura ───────────────────────────


def test_confusion_cero_o_cuesta_menos_que_un_digito_distinto() -> None:
    """Un lector que ve 'E84.O' quiso decir 'E84.0', no 'E84.1'.

    Con Levenshtein plano las dos sustituciones cuestan 1 y el campo queda
    ambiguo sin necesidad. La distancia ponderada usa esa informacion.
    """
    assert distancia_edicion("e84.o", "e84.0") < distancia_edicion("e84.o", "e84.1")


def test_distancia_es_cero_para_iguales() -> None:
    assert distancia_edicion("n18.5", "n18.5") == 0.0


# ── lo que se corrige solo ───────────────────────────────────────────────────


def test_o_por_cero_se_corrige_y_queda_verde(verificador, verdad) -> None:
    r = verificador.verificar({**verdad, "cie10_1": "E84.O"})
    c = r.campos["cie10_1"]
    assert c.estado is EstadoCampo.VERDE
    assert c.valor == "E84.0"
    assert c.fue_corregido
    assert c.ajuste is not None and c.ajuste.valor_leido == "E84.O"


def test_la_correccion_conserva_el_valor_crudo(verificador, verdad) -> None:
    """Sin el rastro, una correccion automatica es indistinguible de una alucinacion."""
    r = verificador.verificar({**verdad, "especialidad": "Pediatna"})
    c = r.campos["especialidad"]
    assert c.valor == "Pediatria"
    assert c.valor_crudo == "Pediatna"
    assert Motivo.AJUSTADO_A_CATALOGO in c.motivos


# ── lo que se detecta ────────────────────────────────────────────────────────


def test_dni_de_siete_digitos_no_pasa(verificador, verdad) -> None:
    r = verificador.verificar({**verdad, "dni": "7123456"})
    assert r.campos["dni"].estado is EstadoCampo.ROJO
    assert not r.utilizable


def test_codigo_inexistente_no_se_inventa(verificador, verdad) -> None:
    """Fuera del catalogo y lejos de todo: rojo. Corregir a ciegas seria inventar."""
    c = verificador.verificar({**verdad, "cie10_1": "XYZ99"}).campos["cie10_1"]
    assert c.estado is EstadoCampo.ROJO
    assert c.valor is None
    assert Motivo.FUERA_DE_CATALOGO in c.motivos


def test_catalogo_ambiguo_va_a_revision(verificador, verdad) -> None:
    """'E84.5' esta igual de cerca de E84.0 que de E84.1. Decide una persona."""
    c = verificador.verificar({**verdad, "cie10_1": "E84.5"}).campos["cie10_1"]
    assert c.estado is EstadoCampo.AMBAR
    assert Motivo.CATALOGO_AMBIGUO in c.motivos


def test_edad_incoherente_marca_los_dos_campos(verificador, verdad) -> None:
    """El modelo puede leer mal la edad o la fecha, pero no las dos de forma coherente."""
    r = verificador.verificar({**verdad, "edad_anios": "12"})
    for nombre in ("edad_anios", "fecha_nacimiento"):
        c = r.campos[nombre]
        assert c.estado is EstadoCampo.AMBAR
        assert Motivo.INCONSISTENTE_CON_OTRO_CAMPO in c.motivos


def test_desacuerdo_entre_dos_lecturas(verificador, verdad) -> None:
    """Senal de confianza gratis cuando el modelo no expone probabilidades."""
    r = verificador.verificar(verdad, segunda_lectura={"dni": "71284567"})
    c = r.campos["dni"]
    assert c.estado is EstadoCampo.AMBAR
    assert Motivo.DESACUERDO_ENTRE_MODELOS in c.motivos


def test_confianza_baja_nunca_mejora_el_estado(verificador, verdad) -> None:
    r = verificador.verificar(verdad, confianzas={"dni": 0.31})
    assert r.campos["dni"].estado is EstadoCampo.AMBAR


def test_campo_obligatorio_vacio_es_rojo(verificador, verdad) -> None:
    c = verificador.verificar({**verdad, "dni": ""}).campos["dni"]
    assert c.estado is EstadoCampo.ROJO
    assert Motivo.VACIO in c.motivos


def test_campo_opcional_vacio_es_ambar_no_rojo(verificador, verdad) -> None:
    """Un celular ausente no invalida el documento; solo hay que preguntarlo."""
    r = verificador.verificar({**verdad, "celular": ""})
    assert r.campos["celular"].estado is EstadoCampo.AMBAR
    assert r.utilizable


# ── la metrica ───────────────────────────────────────────────────────────────


def test_lectura_perfecta_no_pide_revision(verificador, verdad) -> None:
    m = medir(verificador.verificar(verdad), verdad)
    assert m.exactitud_bruta == 1.0
    assert m.tasa_error_no_detectado == 0.0
    assert m.carga_de_revision == 0.0


def test_errores_corregibles_no_cuentan_como_error(verificador, verdad) -> None:
    """El sistema leyo mal y aun asi el valor final es correcto. Eso es el punto."""
    m = medir(verificador.verificar({**verdad, "cie10_1": "E84.O"}), verdad)
    assert m.exactitud_bruta == 1.0
    assert m.tasa_error_no_detectado == 0.0


def test_un_error_que_pasa_en_verde_cuenta_como_no_detectado() -> None:
    """LA metrica. Un campo sin estructura conocida no tiene como detectarse:
    por eso los campos libres nunca deberian salir en verde sin revision."""
    specs = {"nombres": EspecificacionCampo("nombres", "Nombres")}
    v = VerificadorExtraccion(especificaciones=specs)
    m = medir(v.verificar({"nombres": "Ana Lucia"}), {"nombres": "Ana Lucero"})
    assert m.errores_no_detectados == 1
    assert m.tasa_error_no_detectado == 1.0


def test_error_detectado_no_cuenta_como_no_detectado(verificador, verdad) -> None:
    m = medir(verificador.verificar({**verdad, "cie10_1": "XYZ99"}), verdad)
    assert m.errores_no_detectados == 0
    assert m.errores_detectados == 1


# ── invariantes del objeto de valor ──────────────────────────────────────────


def test_un_campo_verde_siempre_tiene_valor(verificador, verdad) -> None:
    for c in verificador.verificar(verdad).verdes:
        assert c.valor is not None


def test_todo_campo_declara_por_que_esta_como_esta(verificador, verdad) -> None:
    """Decirle a alguien 'revisa esto' sin decirle por que lo obliga a revisar todo."""
    for c in verificador.verificar({**verdad, "dni": "abc"}).campos.values():
        assert c.motivos, f"{c.nombre} no declara motivo"
        assert c.explicacion()
