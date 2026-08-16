"""BLOQUEANTE — la ruta de aprendizaje no puede frenar la ruta de referencia.

═══════════════════════════════════════════════════════════════════════════════
LA INVARIANTE
═══════════════════════════════════════════════════════════════════════════════

    La ruta de aprendizaje NUNCA bloquea, retrasa ni condiciona una transicion
    de la ruta de referencia. No existe un readiness score que autorice la
    transferencia.

El motivo es clinico y hay que poder decirlo en una frase: **el adolescente que
menos lecciones completa es exactamente el que mas riesgo tiene de quedarse sin
servicio a los 18.** Si el sistema pudiera retener su derivacion por eso,
habriamos convertido una herramienta de acompanamiento en una barrera de
acceso, y habriamos empeorado precisamente el caso que veniamos a proteger.

Es una tentacion real de diseno, no una hipotetica: un "puntaje de preparacion
para transferir" suena responsable y se implementa en veinte minutos. Este
archivo existe para que a nadie se le ocurra a las tres de la manana.
"""

from __future__ import annotations

import inspect
from datetime import date, timedelta

import pytest

from relevo.dominio.entidades import progreso_aprendizaje as modulo_progreso
from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.entidades.progreso_aprendizaje import ProgresoAprendizaje
from relevo.dominio.objetos_valor.estado_ciclo import TRANSICIONES_PERMITIDAS
from relevo.dominio.objetos_valor.habilidad import EstadoHabilidad, Habilidad

HOY = date(2026, 8, 16)


def progreso_en_cero() -> ProgresoAprendizaje:
    """El peor caso: las siete habilidades sin empezar."""
    progreso = ProgresoAprendizaje(paciente_id="PAC-1")
    for habilidad in Habilidad:
        progreso.estados[habilidad] = EstadoHabilidad.POR_INICIAR
    return progreso


# ═══════════════════════════════════════════════════════════════════════════
# La regla
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_con_las_siete_habilidades_sin_iniciar_todas_las_transiciones_siguen() -> None:
    """Recorre el grafo entero con el peor progreso posible.

    No se comprueba una transicion de ejemplo: se comprueban TODAS. Una sola
    que dependiera del aprendizaje seria suficiente para romper la promesa.
    """
    progreso = progreso_en_cero()
    assert progreso.total_logradas == 0

    for origen, destinos in TRANSICIONES_PERMITIDAS.items():
        for destino in destinos:
            ciclo = CicloTransicion(
                paciente_id="PAC-1",
                fecha_inicio=HOY - timedelta(days=10),
                fecha_nacimiento=date(2009, 4, 12),
            )
            # Se coloca el ciclo en el estado de origen sin recorrer el grafo:
            # lo que se mide es que el aprendizaje no estorbe, no el grafo.
            ciclo.historial[-1] = type(ciclo.historial[-1])(
                estado=origen, fecha=HOY - timedelta(days=5)
            )

            extras: dict[str, object] = {}
            if destino is EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA:
                extras["fuente_confirmacion"] = FuenteConfirmacion.CONFIRMACION_RECEPTOR
            if destino is EstadoCiclo.REINGRESO:
                from relevo.dominio.objetos_valor.reingreso import MotivoReingreso

                extras["motivo_reingreso"] = MotivoReingreso.REAPARECE_TRAS_PERDIDA

            ciclo.avanzar(destino, HOY, **extras)  # type: ignore[arg-type]
            assert ciclo.estado is destino, (
                f"La transicion {origen.name} -> {destino.name} no ocurrio con "
                "el progreso de aprendizaje en cero."
            )


@pytest.mark.bloqueante
def test_no_existe_ninguna_puerta_de_autorizacion_en_el_progreso() -> None:
    """Vigila la tentacion, no solo su consecuencia.

    El test de arriba comprueba que hoy nada bloquea. Este comprueba que no
    exista siquiera el metodo con el que alguien podria bloquear manana: un
    `esta_listo_para_transferir()` en `ProgresoAprendizaje` seria adoptado por
    la interfaz en cuanto existiera.
    """
    prohibidos = (
        "esta_listo",
        "listo_para_transferir",
        "readiness",
        "puntaje_preparacion",
        "autoriza",
        "habilita_transferencia",
        "puede_transferirse",
    )
    nombres = [n for n, _ in inspect.getmembers(ProgresoAprendizaje)]
    for prohibido in prohibidos:
        coincidencias = [n for n in nombres if prohibido in n.lower()]
        assert not coincidencias, (
            f"ProgresoAprendizaje expone {coincidencias}. No puede existir un "
            "puntaje que autorice la transferencia: el adolescente que menos "
            "lecciones completa es el que mas riesgo tiene de quedarse sin "
            "servicio a los 18."
        )


@pytest.mark.bloqueante
def test_el_ciclo_no_conoce_el_progreso_de_aprendizaje() -> None:
    """La independencia estructural, no solo la de comportamiento.

    Mientras `CicloTransicion` no importe nada de aprendizaje, la invariante se
    sostiene sola: no hay forma de escribir el acoplamiento sin que este test
    lo vea.
    """
    fuente = inspect.getsource(CicloTransicion)
    for palabra in ("ProgresoAprendizaje", "Habilidad", "Leccion", "aprendizaje"):
        assert palabra not in fuente, (
            f"CicloTransicion menciona '{palabra}'. La ruta de referencia no "
            "puede depender de la ruta de aprendizaje."
        )


def test_el_modulo_de_progreso_no_importa_el_ciclo() -> None:
    """Y en la otra direccion tampoco, que es como empiezan estas cosas."""
    fuente = inspect.getsource(modulo_progreso)
    assert "ciclo_transicion" not in fuente
    assert "EstadoCiclo" not in fuente


# ═══════════════════════════════════════════════════════════════════════════
# Lo que el progreso SI hace
# ═══════════════════════════════════════════════════════════════════════════


def test_el_progreso_materializa_las_siete_habilidades() -> None:
    """La interfaz siempre pinta siete. Que las que faltan cuenten como cero no
    puede depender de que alguien se acuerde."""
    progreso = ProgresoAprendizaje(paciente_id="PAC-2")
    assert len(progreso.estados) == 7
    assert len(progreso.sin_empezar) == 7
    assert progreso.resumen() == "0 de 7 habilidades logradas"


def test_registrar_un_avance_guarda_historial() -> None:
    """`NECESITA_REFUERZO` solo significa algo si se sabe que antes estuvo
    lograda. Sin historial, un refuerzo es indistinguible de no haber
    empezado."""
    progreso = ProgresoAprendizaje(paciente_id="PAC-3")
    progreso.registrar(Habilidad.MANEJO_MI_TRATAMIENTO, EstadoHabilidad.LOGRADA, HOY)
    progreso.registrar(
        Habilidad.MANEJO_MI_TRATAMIENTO,
        EstadoHabilidad.NECESITA_REFUERZO,
        HOY + timedelta(days=200),
    )

    assert progreso.total_logradas == 0
    assert len(progreso.historial) == 2
    assert progreso.historial[0].estado is EstadoHabilidad.LOGRADA


def test_ver_una_leccion_no_es_lograr_la_habilidad() -> None:
    """Confundirlas produciria una metrica que sube sola."""
    progreso = ProgresoAprendizaje(paciente_id="PAC-4")
    progreso.marcar_leccion_vista(6)

    assert 6 in progreso.lecciones_vistas
    assert progreso.total_logradas == 0
