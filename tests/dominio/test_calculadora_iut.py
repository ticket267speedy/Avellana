"""Los cinco casos del IUT calculados a mano.

CRITERIO DE ACEPTACION DEL BLOQUE 3 (PLAN_TECNICO §12): cinco casos calculados
a mano en papel deben coincidir con el codigo.

Cada test lleva la aritmetica escrita entera. Si alguien cambia un beta en
`config/reglas_transicion.yaml` y no actualiza estas cuentas, el test falla —
que es exactamente lo que tiene que pasar: los pesos son politica clinica y
cambiarlos no puede ser silencioso.

Parametros: los de `conftest.py`, copia del YAML v0.1.0-provisional.
    beta_0 = -4.0
    x1 3.0 · x2 1.2 · x3 1.5 · x4 1.0 · x5 1.0 · x6 0.8 · x7 0.6 · x8 0.9
    (suman 10.0 -> z va de -4.0 a +6.0)

REVISION DEL 14/08: los casos 2 y 3 se recalcularon en papel tras redefinir x2
(categorias CCC distintas, no numero de diagnosticos) y x3 (severidad maxima,
no suma). Los casos 1, 4 y 5 no cambiaron. El caso 3 paso de verde a ambar.

Sin mocks, sin base de datos, sin red. Aritmetica pura.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from relevo.dominio.entidades.diagnostico import (
    CategoriaCCC,
    Diagnostico,
    Dispositivo,
    ResultadoTRAQ,
    TipoSeguro,
)
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.objetos_valor.codigo_cie10 import CodigoCIE10
from relevo.dominio.objetos_valor.indice_urgencia import (
    AporteFactor,
    EstadoSemaforo,
    IndiceUrgencia,
)
from relevo.dominio.servicios.calculadora_iut import (
    INALCANZABLE,
    X1_URGENCIA_TEMPORAL,
    X2_COMPLEJIDAD,
    X3_SEVERIDAD,
    X5_BRECHA_PREPARACION,
    X6_RIESGO_PERDIDA,
    X7_BARRERA_ACCESO,
    X8_CONTINUIDAD_SEGURO,
    CalculadoraIUT,
    calibrar_umbral_rojo,
)

# Fecha de referencia de todos los casos. Fija a proposito: un test que depende
# del dia en que se corre no es un test.
HOY = date(2026, 8, 14)

# El z se verifica exacto porque es una suma de productos hecha en papel.
# El IUT se verifica a cinco decimales: la sigmoide es libreria estandar y no
# es lo que estamos comprobando aqui.
TOLERANCIA_IUT = 5e-5


def factor(iut: IndiceUrgencia, nombre: str) -> AporteFactor:
    """El aporte de un factor concreto dentro del desglose."""
    return next(a for a in iut.aportes if a.nombre == nombre)


def dx(
    codigo: str,
    categoria: CategoriaCCC,
    activo: bool = True,
    raro: bool = False,
) -> Diagnostico:
    return Diagnostico(
        codigo=CodigoCIE10(codigo),
        descripcion=codigo,
        categoria=categoria,
        activo=activo,
        es_raro=raro,
    )


def paciente_con(id_paciente: str, diagnosticos: list[Diagnostico]) -> Paciente:
    """Un paciente de 17 anios con todos los datos completos, para aislar el
    efecto de los diagnosticos sobre x2 y x3."""
    return Paciente(
        id=id_paciente,
        fecha_nacimiento=date(2009, 6, 14),
        procedencia="Lima",
        tipo_seguro=TipoSeguro.ESSALUD,
        diagnosticos=diagnosticos,
        ultima_consulta=HOY,
        traq=ResultadoTRAQ(puntaje=5.0, fecha=HOY),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CASO 1 — El piso del indice
#
# Recien cumplidos 14: entra a la cohorte con la ventana completa por delante.
# Ningun factor de riesgo activo salvo el seguro privado.
#
#   x1 = 1 - 48/48 = 0        -> 3.0 * 0    = 0.00
#   x2 = 0 categorias / 5 = 0 -> 1.2 * 0    = 0.00
#   x3 = sin dx -> 0          -> 1.5 * 0    = 0.00
#   x4 = 0/6 = 0              -> 1.0 * 0    = 0.00
#   x5 = (5 - 5)/4 = 0        -> 1.0 * 0    = 0.00
#   x6 = 0/360 = 0            -> 0.8 * 0    = 0.00
#   x7 = Lima -> 0            -> 0.6 * 0    = 0.00
#   x8 = PRIVADO -> 0.3       -> 0.9 * 0.3  = 0.27  (no verificado)
#                                       suma = 0.27
#   z = -4.00 + 0.27 = -3.73
#   IUT = 1 / (1 + e^3.73) = 1 / 42.6791 = 0.02343
# ═══════════════════════════════════════════════════════════════════════════


def test_caso_1_piso_del_indice(calculadora: CalculadoraIUT) -> None:
    paciente = Paciente(
        id="CASO-1",
        fecha_nacimiento=date(2012, 8, 14),  # 14 anios exactos hoy
        procedencia="Lima",
        tipo_seguro=TipoSeguro.PRIVADO,
        ultima_consulta=HOY,
        traq=ResultadoTRAQ(puntaje=5.0, fecha=HOY),
    )

    iut = calculadora.calcular(paciente, HOY)

    assert paciente.meses_hasta_corte(HOY) == 48
    assert iut.z == pytest.approx(-3.73, abs=1e-9)
    assert iut.valor == pytest.approx(0.02343, abs=TOLERANCIA_IUT)
    assert iut.estado is EstadoSemaforo.VERDE
    # El unico supuesto es el seguro privado: el YAML lo marca `verificado:
    # false` porque la continuidad depende de la poliza familiar, que no
    # conocemos. Todo lo demas son datos reales del paciente.
    assert iut.factores_imputados == (X8_CONTINUIDAD_SEGURO,)


# ═══════════════════════════════════════════════════════════════════════════
# CASO 2 — Ana, el caso del pitch
#
# 17 anios, 10 meses hasta el corte. Enfermedad renal cronica en hemodialisis,
# anemia asociada, y un trastorno hidroelectrolitico agudo (categoria OTRA:
# no cuenta como cronico). EsSalud, procede de Huancavelica, TRAQ 3.0, seis
# meses sin control.
#
#   x1 = 1 - 10/48 = 38/48 = 0.791666...  -> 3.0 * 0.7916667 = 2.375
#   x2 = 2 categorias (renal, hematologica) / 5 = 0.4
#                                          -> 1.2 * 0.4      = 0.480
#   x3 = max(renal 3, hematologica 2) = 3; 3/3 = 1.0
#                                          -> 1.5 * 1.0      = 1.500
#   x4 = hemodialisis 3 / 6 = 0.5         -> 1.0 * 0.5       = 0.500
#   x5 = (5 - 3.0)/4 = 0.5                -> 1.0 * 0.5       = 0.500
#   x6 = 180/360 = 0.5                    -> 0.8 * 0.5       = 0.400
#   x7 = Huancavelica -> 1                -> 0.6 * 1         = 0.600
#   x8 = ESSALUD -> 1.0                   -> 0.9 * 1.0       = 0.900
#                                                     suma = 7.255
#   z = -4.000 + 7.255 = 3.255
#   IUT = 1 / (1 + e^-3.255) = 1 / 1.0385808 = 0.96285
# ═══════════════════════════════════════════════════════════════════════════


def test_caso_2_ana_prioridad_alta(calculadora: CalculadoraIUT) -> None:
    paciente = Paciente(
        id="CASO-2",
        fecha_nacimiento=date(2009, 6, 14),  # cumple 18 el 2027-06-14
        procedencia="Huancavelica",
        tipo_seguro=TipoSeguro.ESSALUD,
        diagnosticos=[
            dx("N18.5", CategoriaCCC.RENAL),
            dx("D63.8", CategoriaCCC.HEMATOLOGICA_INMUNOLOGICA),
            dx("E87.6", CategoriaCCC.OTRA),  # agudo: no cuenta
        ],
        dispositivos=[Dispositivo(tipo="hemodialisis")],
        ultima_consulta=HOY - timedelta(days=180),
        traq=ResultadoTRAQ(puntaje=3.0, fecha=HOY),
    )

    iut = calculadora.calcular(paciente, HOY)

    assert paciente.meses_hasta_corte(HOY) == 10
    assert iut.z == pytest.approx(3.255, abs=1e-9)
    assert iut.valor == pytest.approx(0.96285, abs=TOLERANCIA_IUT)
    assert iut.estado is EstadoSemaforo.ROJO

    # El desglose es el producto; el numero es solo el orden.
    principales = iut.principales(3)
    assert principales[0].nombre == X1_URGENCIA_TEMPORAL
    assert principales[0].aporte == pytest.approx(2.375, abs=1e-9)
    assert principales[1].nombre == X3_SEVERIDAD
    assert principales[2].nombre == X8_CONTINUIDAD_SEGURO
    assert principales[2].aporte == pytest.approx(0.900, abs=1e-9)


# ═══════════════════════════════════════════════════════════════════════════
# CASO 3 — Tres datos que no existen
#
# 16 anios, dos anios hasta el corte. Paralisis cerebral. Sin TRAQ, sin
# registro de ultima consulta, y con SIS: los tres se imputan y los tres se
# marcan.
#
#   x1 = 1 - 24/48 = 0.5              -> 3.0 * 0.5       = 1.500
#   x2 = 1 categoria / 5 = 0.2        -> 1.2 * 0.2       = 0.240
#   x3 = neuromuscular 2; 2/3 = 0.6666-> 1.5 * 0.6666667 = 1.000
#   x4 = 0/6 = 0                      -> 1.0 * 0         = 0.000
#   x5 = sin TRAQ -> 0.5 imputado     -> 1.0 * 0.5       = 0.500
#   x6 = sin consulta -> 0.5 imputado -> 0.8 * 0.5       = 0.400
#   x7 = Lima -> 0                    -> 0.6 * 0         = 0.000
#   x8 = SIS -> 0.5 no verificado     -> 0.9 * 0.5       = 0.450
#                                                suma = 4.090
#   z = -4.0 + 4.09 = 0.09
#   IUT = 1 / (1 + e^-0.09) = 1 / 1.9139312 = 0.52248
#
# Este es el caso que la redefinicion de x3 movio de verde a ambar, y el
# cambio es el correcto: una condicion neuromuscular cronica sin ninguna
# preparacion registrada y sin control conocido no es seguimiento estandar.
# ═══════════════════════════════════════════════════════════════════════════


def test_caso_3_datos_faltantes_se_imputan_y_se_marcan(
    calculadora: CalculadoraIUT,
) -> None:
    paciente = Paciente(
        id="CASO-3",
        fecha_nacimiento=date(2010, 8, 14),  # 16 anios exactos hoy
        procedencia="Lima",
        tipo_seguro=TipoSeguro.SIS,
        diagnosticos=[dx("G80.9", CategoriaCCC.NEUROMUSCULAR)],
        ultima_consulta=None,
        traq=None,
    )

    iut = calculadora.calcular(paciente, HOY)

    assert paciente.meses_hasta_corte(HOY) == 24
    assert iut.z == pytest.approx(0.09, abs=1e-9)
    assert iut.valor == pytest.approx(0.52248, abs=TOLERANCIA_IUT)
    assert iut.estado is EstadoSemaforo.AMBAR

    # Lo que se decide sobre un supuesto tiene que verse como supuesto.
    assert set(iut.factores_imputados) == {
        X5_BRECHA_PREPARACION,
        X6_RIESGO_PERDIDA,
        X8_CONTINUIDAD_SEGURO,  # SIS: no verificado, ver TODO del YAML
    }
    # Imputado 1.0 + 0.8 + 0.9 = 2.7 de 10 -> 27 % del modelo es supuesto.
    assert iut.confianza == pytest.approx(0.73, abs=1e-9)
    assert not iut.datos_insuficientes  # justo por encima del 0.70


# ═══════════════════════════════════════════════════════════════════════════
# CASO 4 — El techo: z = +6.0 exacto
#
# El dia del cumpleanos 18, con todos los factores saturados. Comprueba que
# los betas suman 10.0 y que todos los clamps funcionan por arriba.
#
#   x1 = 1 - 0/48 = 1                     -> 3.0 * 1 = 3.0
#   x2 = 6 categorias cronicas / 5 -> 1    -> 1.2 * 1 = 1.2
#   x3 = max severidad 3; 3/3 = 1         -> 1.5 * 1 = 1.5
#   x4 = (3 traqueo + 3 ventilacion)/6 = 1-> 1.0 * 1 = 1.0
#   x5 = (5 - 1.0)/4 = 1                  -> 1.0 * 1 = 1.0
#   x6 = 400/360 = 1.11 -> 1              -> 0.8 * 1 = 0.8
#   x7 = Loreto -> 1                      -> 0.6 * 1 = 0.6
#   x8 = NINGUNO -> 1.0                   -> 0.9 * 1 = 0.9
#                                              suma = 10.0
#   z = -4.0 + 10.0 = 6.0
#   IUT = 1 / (1 + e^-6) = 1 / 1.00247875 = 0.99753
# ═══════════════════════════════════════════════════════════════════════════


def test_caso_4_techo_del_indice(calculadora: CalculadoraIUT) -> None:
    paciente = Paciente(
        id="CASO-4",
        fecha_nacimiento=date(2008, 8, 14),  # cumple 18 justo hoy
        procedencia="Loreto",
        tipo_seguro=TipoSeguro.NINGUNO,
        diagnosticos=[
            dx("I27.0", CategoriaCCC.CARDIOVASCULAR),
            dx("J84.9", CategoriaCCC.RESPIRATORIA),
            dx("N18.5", CategoriaCCC.RENAL),
            dx("C91.0", CategoriaCCC.MALIGNIDAD),
            dx("Z94.0", CategoriaCCC.TRASPLANTE),
            dx("E74.0", CategoriaCCC.METABOLICA),
            dx("R62.8", CategoriaCCC.OTRA),  # no cuenta: ni cronico ni raro
        ],
        dispositivos=[
            Dispositivo(tipo="traqueostomia"),
            Dispositivo(tipo="ventilacion_mecanica"),
        ],
        ultima_consulta=HOY - timedelta(days=400),
        traq=ResultadoTRAQ(puntaje=1.0, fecha=HOY),
    )

    iut = calculadora.calcular(paciente, HOY)

    assert paciente.meses_hasta_corte(HOY) == 0
    assert iut.z == pytest.approx(6.0, abs=1e-9)
    assert iut.valor == pytest.approx(0.99753, abs=TOLERANCIA_IUT)
    assert iut.estado is EstadoSemaforo.ROJO
    # El techo declarado en config/reglas_transicion.yaml: los betas suman 10.
    assert sum(a.aporte for a in iut.aportes) == pytest.approx(10.0, abs=1e-9)


# ═══════════════════════════════════════════════════════════════════════════
# CASO 5 — Antes de la ventana: x1 se acota por abajo
#
# 12 anios: faltan 72 meses, mas que el horizonte de 48. Sin el clamp, x1
# valdria -0.5 y el paciente saldria con urgencia negativa.
# Lleva un audifono, que pesa 0: registrado pero sin puntuar.
#
#   x1 = 1 - 72/48 = -0.5 -> clamp -> 0 -> 3.0 * 0         = 0.000000
#   x2 = 0 categorias                   -> 1.2 * 0         = 0.000000
#   x3 = sin dx -> 0                    -> 1.5 * 0         = 0.000000
#   x4 = audifono 0 / 6 = 0             -> 1.0 * 0         = 0.000000
#   x5 = (5 - 5)/4 = 0                  -> 1.0 * 0         = 0.000000
#   x6 = 30/360 = 0.0833333             -> 0.8 * 0.0833333 = 0.066667
#   x7 = Callao -> 0 (Lima Metropolitana)-> 0.6 * 0        = 0.000000
#   x8 = PRIVADO -> 0.3                 -> 0.9 * 0.3       = 0.270000
#                                                suma = 0.3366667
#   z = -4.0 + 0.3366667 = -3.6633333
#   IUT = 1 / (1 + e^3.6633333) = 1 / 39.99126 = 0.02501
# ═══════════════════════════════════════════════════════════════════════════


def test_caso_5_antes_de_la_ventana_x1_se_acota(calculadora: CalculadoraIUT) -> None:
    paciente = Paciente(
        id="CASO-5",
        fecha_nacimiento=date(2014, 8, 14),  # 12 anios hoy
        procedencia="Callao",
        tipo_seguro=TipoSeguro.PRIVADO,
        dispositivos=[Dispositivo(tipo="audifono")],
        ultima_consulta=HOY - timedelta(days=30),
        traq=ResultadoTRAQ(puntaje=5.0, fecha=HOY),
    )

    iut = calculadora.calcular(paciente, HOY)

    assert paciente.meses_hasta_corte(HOY) == 72
    x1 = factor(iut, X1_URGENCIA_TEMPORAL)
    assert x1.x == 0.0  # acotado, no negativo
    assert iut.z == pytest.approx(-3.6633333333333336, abs=1e-9)
    assert iut.valor == pytest.approx(0.02501, abs=TOLERANCIA_IUT)
    assert iut.estado is EstadoSemaforo.VERDE


# ═══════════════════════════════════════════════════════════════════════════
# x2 y x3 miden cosas distintas — la correccion de fondo de la revision
# ═══════════════════════════════════════════════════════════════════════════


def test_tres_diagnosticos_del_mismo_sistema_son_un_sistema(
    calculadora: CalculadoraIUT,
) -> None:
    """Antes, agregar codigos del mismo aparato inflaba x2 Y x3 a la vez, y el
    desglose mostraba dos motivos donde habia uno. Ahora tres codigos
    cardiovasculares dan exactamente el mismo indice que uno solo: es un
    sistema comprometido, no tres."""
    uno = paciente_con("UNO", [dx("I27.0", CategoriaCCC.CARDIOVASCULAR)])
    tres = paciente_con(
        "TRES",
        [
            dx("I27.0", CategoriaCCC.CARDIOVASCULAR),
            dx("I50.0", CategoriaCCC.CARDIOVASCULAR),
            dx("I42.0", CategoriaCCC.CARDIOVASCULAR),
        ],
    )

    assert calculadora.calcular(uno, HOY).z == pytest.approx(
        calculadora.calcular(tres, HOY).z, abs=1e-9
    )


def test_x2_sube_al_comprometerse_otro_sistema(calculadora: CalculadoraIUT) -> None:
    """Lo que si tiene que subir la complejidad: un aparato distinto."""
    uno = paciente_con("UNO", [dx("I27.0", CategoriaCCC.CARDIOVASCULAR)])
    dos = paciente_con(
        "DOS",
        [
            dx("I27.0", CategoriaCCC.CARDIOVASCULAR),
            dx("N18.5", CategoriaCCC.RENAL),
        ],
    )

    x2_uno = factor(calculadora.calcular(uno, HOY), X2_COMPLEJIDAD)
    x2_dos = factor(calculadora.calcular(dos, HOY), X2_COMPLEJIDAD)
    assert x2_uno.x == pytest.approx(0.2, abs=1e-9)
    assert x2_dos.x == pytest.approx(0.4, abs=1e-9)


def test_una_condicion_severa_y_dos_leves_es_un_paciente_severo(
    calculadora: CalculadoraIUT,
) -> None:
    """x3 toma el maximo, no la suma: sumar lo convertiria en un segundo
    contador de diagnosticos."""
    paciente = Paciente(
        id="MAX",
        fecha_nacimiento=date(2009, 6, 14),
        diagnosticos=[
            dx("N18.5", CategoriaCCC.RENAL),  # severidad 3
            dx("K90.0", CategoriaCCC.GASTROINTESTINAL),  # 2
            dx("P07.3", CategoriaCCC.NEONATAL),  # 1
        ],
    )
    x3 = factor(calculadora.calcular(paciente, HOY), X3_SEVERIDAD)
    assert x3.x == pytest.approx(1.0, abs=1e-9)  # 3/3, no 6/3


def test_una_fractura_resuelta_no_sube_la_complejidad(
    calculadora: CalculadoraIUT,
) -> None:
    """PLAN_TECNICO §6.2 define K como diagnosticos cronicos ACTIVOS. Una
    fractura consolidada hace tres anios no complica a nadie hoy."""
    solo_cronico = paciente_con("A", [dx("N18.5", CategoriaCCC.RENAL)])
    con_historial = paciente_con(
        "B",
        [
            dx("N18.5", CategoriaCCC.RENAL),
            dx("S52.5", CategoriaCCC.OTRA),  # agudo
            dx("J18.9", CategoriaCCC.RESPIRATORIA, activo=False),  # curada
        ],
    )

    assert calculadora.calcular(solo_cronico, HOY).z == pytest.approx(
        calculadora.calcular(con_historial, HOY).z, abs=1e-9
    )


def test_una_enfermedad_rara_sin_categoria_ccc_igual_cuenta(
    calculadora: CalculadoraIUT,
) -> None:
    """Las raras son una fuente independiente de CCC v2: un codigo puede ser
    raro sin caer en ninguna categoria compleja, y sigue siendo cronico."""
    paciente = Paciente(
        id="RARA",
        fecha_nacimiento=date(2009, 6, 14),
        diagnosticos=[dx("E75.2", CategoriaCCC.OTRA, raro=True)],
    )
    x2 = factor(calculadora.calcular(paciente, HOY), X2_COMPLEJIDAD)
    assert x2.x == pytest.approx(0.2, abs=1e-9)


# ═══════════════════════════════════════════════════════════════════════════
# Confianza: cuanto del indice es dato y cuanto es supuesto
# ═══════════════════════════════════════════════════════════════════════════


def test_un_tercio_del_modelo_imputado_se_declara_insuficiente(
    calculadora: CalculadoraIUT,
) -> None:
    """SIS, sin TRAQ, sin ultima consulta y sin procedencia: se imputan x5, x6,
    x7 y x8, cuyos betas suman 3.3 de 10. El indice sale igual, pero el sistema
    deja de afirmar que lo sabe."""
    paciente = Paciente(
        id="OPACO",
        fecha_nacimiento=date(2009, 6, 14),
        procedencia="",
        tipo_seguro=TipoSeguro.SIS,
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
    )

    iut = calculadora.calcular(paciente, HOY)

    assert set(iut.factores_imputados) == {
        X5_BRECHA_PREPARACION,
        X6_RIESGO_PERDIDA,
        X7_BARRERA_ACCESO,
        X8_CONTINUIDAD_SEGURO,
    }
    assert iut.confianza == pytest.approx(0.67, abs=1e-9)  # 1 - 3.3/10
    assert iut.datos_insuficientes
    assert "datos insuficientes" in str(iut)


def test_historia_completa_da_confianza_total(calculadora: CalculadoraIUT) -> None:
    paciente = Paciente(
        id="COMPLETO",
        fecha_nacimiento=date(2009, 6, 14),
        procedencia="Lima",
        tipo_seguro=TipoSeguro.ESSALUD,  # verificado: Ley 26790
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
        ultima_consulta=HOY - timedelta(days=90),
        traq=ResultadoTRAQ(puntaje=4.0, fecha=HOY),
    )

    iut = calculadora.calcular(paciente, HOY)

    assert iut.confianza == 1.0
    assert not iut.datos_insuficientes
    assert not iut.hay_datos_faltantes


# ═══════════════════════════════════════════════════════════════════════════
# Invariantes del desglose
# ═══════════════════════════════════════════════════════════════════════════


def test_los_aportes_salen_ordenados_de_mayor_a_menor(
    calculadora: CalculadoraIUT,
) -> None:
    """El orden es la explicacion: quien lee el desglose lee primero lo que
    mas pesa. `IndiceUrgencia` rechaza cualquier otro orden."""
    paciente = Paciente(
        id="ORDEN",
        fecha_nacimiento=date(2009, 6, 14),
        procedencia="Puno",
        tipo_seguro=TipoSeguro.ESSALUD,
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
    )
    aportes = [a.aporte for a in calculadora.calcular(paciente, HOY).aportes]
    assert aportes == sorted(aportes, reverse=True)


def test_siempre_hay_ocho_factores(calculadora: CalculadoraIUT) -> None:
    """Ninguno se omite por falta de dato: se imputa y se marca. Un factor
    ausente del desglose seria un factor que nadie puede auditar."""
    paciente = Paciente(id="OCHO", fecha_nacimiento=date(2009, 6, 14))
    assert len(calculadora.calcular(paciente, HOY).aportes) == 8


def test_la_calculadora_no_se_construye_sin_politica_clinica() -> None:
    """Sin valor por defecto, a proposito: `CalculadoraIUT()` produciria
    numeros con aspecto legitimo calculados con pesos que ningun medico
    aprobo."""
    with pytest.raises(TypeError):
        CalculadoraIUT()  # type: ignore[call-arg]


# ═══════════════════════════════════════════════════════════════════════════
# Calibracion del umbral rojo contra la capacidad real del equipo
# ═══════════════════════════════════════════════════════════════════════════


def test_el_umbral_rojo_sale_de_la_capacidad_del_equipo() -> None:
    """Marcar en rojo a mas pacientes de los que el equipo puede atender no
    prioriza nada. Con capacidad 3 sobre 6 pacientes, el umbral es el IUT del
    tercero."""
    indices = [0.95, 0.91, 0.84, 0.70, 0.52, 0.11]
    assert calibrar_umbral_rojo(indices, capacidad_mensual=3) == 0.84


def test_sin_capacidad_ningun_paciente_llega_a_rojo(
    calculadora: CalculadoraIUT,
) -> None:
    """Si no hay capacidad, el sistema no debe decir que la hay — ni siquiera
    para el paciente mas extremo, cuyo IUT puede redondear a 1.0 exacto."""
    umbral = calibrar_umbral_rojo([0.99, 0.98], capacidad_mensual=0)
    assert umbral == INALCANZABLE
    assert umbral > 1.0

    extremo = Paciente(
        id="EXTREMO",
        fecha_nacimiento=date(2008, 8, 14),
        procedencia="Loreto",
        tipo_seguro=TipoSeguro.NINGUNO,
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
    )
    assert calculadora.calcular(extremo, HOY, umbral_rojo=umbral).estado is not (
        EstadoSemaforo.ROJO
    )


def test_capacidad_mayor_que_la_cohorte_admite_a_todos() -> None:
    indices = [0.95, 0.40]
    assert calibrar_umbral_rojo(indices, capacidad_mensual=10) == 0.40


def test_si_las_bandas_se_juntan_se_dice(calculadora: CalculadoraIUT) -> None:
    """Con capacidad de sobra el rojo calibrado puede caer por debajo del
    ambar. Las bandas se juntan; lo que no puede pasar es que se junten en
    silencio y el semaforo parezca roto."""
    paciente = Paciente(
        id="HOLGADO",
        fecha_nacimiento=date(2010, 8, 14),
        procedencia="Lima",
        tipo_seguro=TipoSeguro.ESSALUD,
        diagnosticos=[dx("N18.5", CategoriaCCC.RENAL)],
    )
    iut = calculadora.calcular(paciente, HOY, umbral_rojo=0.20)

    assert iut.bandas_colapsadas
    assert iut.umbral_ambar == 0.20
    assert iut.estado is EstadoSemaforo.ROJO
