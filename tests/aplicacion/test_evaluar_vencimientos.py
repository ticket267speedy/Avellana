"""Vencimientos y avisos: el motor de B4, probado sobre el paso del tiempo.

Es el criterio de aceptacion de A3 en la revision de arquitectura: simular que
pasan los dias sobre una cohorte y verificar que se emite `PlazoVencido` con el
destinatario correcto.
"""

from __future__ import annotations

from datetime import date, timedelta

from relevo.aplicacion.despachar_avisos import DespacharAvisos
from relevo.aplicacion.evaluar_vencimientos import EvaluarVencimientos
from relevo.dominio.entidades.ciclo_transicion import CicloTransicion, EstadoCiclo
from relevo.dominio.eventos import PlazoPorVencer, PlazoVencido
from relevo.dominio.puertos.notificacion import (
    CanalNotificacion,
    Mensaje,
    ResultadoDespacho,
    TipoDestinatario,
)
from relevo.dominio.servicios.maquina_ciclo import MaquinaCiclo, PoliticaPlazos
from relevo.infraestructura.persistencia.repositorio_memoria import (
    RepositorioCiclosMemoria,
)

HOY = date(2026, 8, 15)
DESTINATARIO = "coordinacion@insnsb.gob.pe"

# Plazos de prueba, no los del YAML: un test que lee configuracion mide dos
# cosas a la vez y falla cuando cambia cualquiera.
POLITICA = PoliticaPlazos(
    dias_por_estado={
        EstadoCiclo.PASAPORTE_EMITIDO: 7,
        EstadoCiclo.REFERENCIA_REGISTRADA: 15,
        EstadoCiclo.REFERENCIA_ACEPTADA: 120,
        EstadoCiclo.CITA_PROGRAMADA: 30,
        EstadoCiclo.CITA_CUMPLIDA: 30,
    }
)


def _repositorio(*ciclos: CicloTransicion) -> RepositorioCiclosMemoria:
    repo = RepositorioCiclosMemoria()
    for c in ciclos:
        repo.guardar(c)
    return repo


def _caso(*ciclos: CicloTransicion) -> EvaluarVencimientos:
    return EvaluarVencimientos(
        repositorio=_repositorio(*ciclos), maquina=MaquinaCiclo(POLITICA)
    )


class CanalEspia(CanalNotificacion):
    """Doble del puerto de notificacion. Guarda lo que se le manda."""

    def __init__(self, admite_clinicos: bool = True) -> None:
        self.mensajes: list[Mensaje] = []
        self._admite = admite_clinicos

    def despachar(self, mensaje: Mensaje) -> ResultadoDespacho:
        if mensaje.contiene_datos_clinicos and not self._admite:
            return ResultadoDespacho(despachado=False, detalle="canal abierto")
        self.mensajes.append(mensaje)
        return ResultadoDespacho(despachado=True, detalle="ok")

    @property
    def nombre(self) -> str:
        return "espia"

    @property
    def admite_datos_clinicos(self) -> bool:
        return self._admite

    @property
    def requiere_red(self) -> bool:
        return False


# ── Vencimientos ────────────────────────────────────────────────────────────


def test_un_ciclo_recien_abierto_no_genera_nada() -> None:
    """El silencio es informacion: no hay nada parado."""
    ciclo = CicloTransicion(paciente_id="PAC-1", fecha_inicio=HOY - timedelta(days=1))
    r = _caso(ciclo).ejecutar(HOY, destinatario=DESTINATARIO)

    assert r.eventos == ()
    assert not r.hay_algo_que_avisar
    assert r.ciclos_revisados == 1


def test_al_superar_el_plazo_se_emite_plazo_vencido() -> None:
    ciclo = CicloTransicion(paciente_id="PAC-2", fecha_inicio=HOY - timedelta(days=40))
    r = _caso(ciclo).ejecutar(HOY, destinatario=DESTINATARIO)

    assert len(r.vencidos) == 1
    evento = r.vencidos[0]
    assert isinstance(evento, PlazoVencido)
    assert evento.paciente_id == "PAC-2"
    assert evento.estado is EstadoCiclo.PASAPORTE_EMITIDO
    assert evento.dias_de_retraso == 33          # 40 transcurridos - 7 de plazo
    assert evento.destinatario == DESTINATARIO
    assert evento.ocurrido_en == HOY


def test_dentro_del_preaviso_se_emite_por_vencer_y_no_vencido() -> None:
    """Avisar solo cuando ya es tarde convierte el sistema en un registro de
    fracasos. El preaviso es donde todavia se puede intervenir."""
    # Plazo 7, preaviso 25 % -> minimo 3 dias. A los 5 dias quedan 2.
    ciclo = CicloTransicion(paciente_id="PAC-3", fecha_inicio=HOY - timedelta(days=5))
    r = _caso(ciclo).ejecutar(HOY, destinatario=DESTINATARIO)

    assert len(r.por_vencer) == 1
    assert len(r.vencidos) == 0
    assert isinstance(r.por_vencer[0], PlazoPorVencer)
    assert r.por_vencer[0].dias_restantes == 2


def test_el_plazo_largo_de_la_cita_no_dispara_antes_de_tiempo() -> None:
    """Los 120 dias entre aceptacion y cita salen de la mediana peruana de
    80-85. Un umbral de 90 dispararia en la mitad de los casos que van bien."""
    ciclo = CicloTransicion(paciente_id="PAC-4", fecha_inicio=HOY - timedelta(days=200))
    ciclo.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, HOY - timedelta(days=195))
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ACEPTADA, HOY - timedelta(days=85))

    r = _caso(ciclo).ejecutar(HOY, destinatario=DESTINATARIO)
    assert r.vencidos == ()


def test_a_los_130_dias_la_cita_si_esta_vencida() -> None:
    ciclo = CicloTransicion(paciente_id="PAC-5", fecha_inicio=HOY - timedelta(days=300))
    ciclo.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, HOY - timedelta(days=295))
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ACEPTADA, HOY - timedelta(days=130))

    r = _caso(ciclo).ejecutar(HOY, destinatario=DESTINATARIO)
    assert len(r.vencidos) == 1
    assert r.vencidos[0].estado is EstadoCiclo.REFERENCIA_ACEPTADA
    assert r.vencidos[0].dias_de_retraso == 10


def test_un_ciclo_cerrado_no_tiene_plazo_que_vigilar() -> None:
    ciclo = CicloTransicion(paciente_id="PAC-6", fecha_inicio=HOY - timedelta(days=400))
    for estado, atras in (
        (EstadoCiclo.REFERENCIA_REGISTRADA, 395),
        (EstadoCiclo.REFERENCIA_ACEPTADA, 380),
        (EstadoCiclo.CITA_PROGRAMADA, 300),
    ):
        ciclo.avanzar(estado, HOY - timedelta(days=atras))
    ciclo.avanzar(
        EstadoCiclo.CITA_CUMPLIDA,
        HOY - timedelta(days=290),
        fuente_confirmacion=__import__(
            "relevo.dominio.entidades.ciclo_transicion", fromlist=["FuenteConfirmacion"]
        ).FuenteConfirmacion.CONFIRMACION_FAMILIA,
    )
    ciclo.avanzar(EstadoCiclo.CONTRARREFERENCIA, HOY - timedelta(days=280))

    r = _caso(ciclo).ejecutar(HOY, destinatario=DESTINATARIO)
    assert r.eventos == ()


# ── Avisos ──────────────────────────────────────────────────────────────────


def test_sin_eventos_no_se_manda_correo() -> None:
    """PLAN_TECNICO §10: un aviso que llega siempre deja de leerse."""
    canal = CanalEspia()
    resumen = DespacharAvisos(canal).ejecutar([], DESTINATARIO)

    assert canal.mensajes == []
    assert resumen.despachados == 0


def test_los_eventos_se_agrupan_en_un_solo_correo() -> None:
    """Quince correos es la forma mas rapida de que dejen de leerse."""
    ciclos = [
        CicloTransicion(paciente_id=f"PAC-{i}", fecha_inicio=HOY - timedelta(days=40))
        for i in range(5)
    ]
    r = _caso(*ciclos).ejecutar(HOY, destinatario=DESTINATARIO)

    canal = CanalEspia()
    DespacharAvisos(canal).ejecutar(r.eventos, DESTINATARIO)

    assert len(canal.mensajes) == 1
    cuerpo = canal.mensajes[0].cuerpo
    assert "VENCIDOS (5)" in cuerpo
    for i in range(5):
        assert f"PAC-{i}" in cuerpo


def test_el_aviso_no_declara_datos_clinicos() -> None:
    """El cuerpo lleva identificadores y etapas, nunca diagnosticos ni dosis:
    puede acabar en una pantalla de bloqueo."""
    ciclo = CicloTransicion(paciente_id="PAC-9", fecha_inicio=HOY - timedelta(days=40))
    r = _caso(ciclo).ejecutar(HOY, destinatario=DESTINATARIO)

    canal = CanalEspia()
    DespacharAvisos(canal).ejecutar(r.eventos, DESTINATARIO)

    mensaje = canal.mensajes[0]
    assert mensaje.contiene_datos_clinicos is False
    assert mensaje.es_seguro_por_canal_abierto
    assert mensaje.tipo_destinatario is TipoDestinatario.EQUIPO
