"""Ida y vuelta de serializacion. NO ES OPCIONAL.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTE ARCHIVO ES BLOQUEANTE
═══════════════════════════════════════════════════════════════════════════════

    Si un campo no entra en el mapeador, se pierde al reiniciar — y se pierde
    en silencio, que es lo peor.

Una serializacion incompleta no lanza ninguna excepcion. Simplemente devuelve
un paciente con un diagnostico menos, o una alergia menos, y nadie se entera
hasta que un medico firma un Pasaporte al que le falta la penicilina.

Cincuenta semillas y comparacion estructural completa: es lo unico que
garantiza que cerrar la aplicacion no borre informacion.
"""

from __future__ import annotations


from datetime import date, timedelta

import pytest

from relevo.dominio.entidades.acceso_apoderado import (
    AccesoApoderado,
    ConsentimientoExplicito,
)
from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.entidades.conciliacion import MedicacionDeclarada
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.progreso_aprendizaje import ProgresoAprendizaje
from relevo.dominio.objetos_valor.habilidad import EstadoHabilidad, Habilidad
from relevo.dominio.objetos_valor.reingreso import MotivoReingreso
from relevo.dominio.servicios.conciliador import conciliar
from relevo.infraestructura.fuentes.cohorte_sintetica import CohorteSintetica
from relevo.infraestructura.persistencia.mapeadores import (
    acceso_a_documento,
    acceso_desde_documento,
    ciclo_a_documento,
    ciclo_desde_documento,
    conciliacion_a_documento,
    conciliacion_desde_documento,
    paciente_a_documento,
    paciente_desde_documento,
    progreso_a_documento,
    progreso_desde_documento,
)

HOY = date(2026, 8, 16)


def _cohorte(semilla: int) -> list[Paciente]:
    return CohorteSintetica(cantidad=3, hoy=HOY, semilla=semilla).leer_pacientes()


# ═══════════════════════════════════════════════════════════════════════════
# Paciente — las 50 semillas
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.bloqueante
def test_ida_y_vuelta_del_paciente_no_pierde_nada() -> None:
    for semilla in range(50):
        for original in _cohorte(semilla):
            reconstruido = paciente_desde_documento(paciente_a_documento(original))
            assert reconstruido == original, (
                f"semilla {semilla}, paciente {original.id}: la serializacion "
                "pierde datos"
            )


def test_las_50_semillas_cubren_los_campos_dificiles() -> None:
    """Un test de ida y vuelta que solo ve pacientes simples no prueba nada.

    Se comprueba que la muestra contenga de verdad los casos que suelen
    romperse: fechas opcionales en None, listas vacias, dosis sin verificar y
    TRAQ ausente.
    """
    todos = [p for s in range(50) for p in _cohorte(s)]

    assert any(p.traq is None for p in todos), "ninguna semilla trae TRAQ ausente"
    assert any(p.traq is not None for p in todos)
    assert any(not p.alergias for p in todos), "ninguna semilla trae lista vacia"
    assert any(p.ultima_consulta is None for p in todos)
    assert any(
        m.requiere_completar_manualmente for p in todos for m in p.medicamentos
    ), "ninguna semilla trae una dosis sin verificar"


def test_una_fecha_ausente_no_se_convierte_en_epoch() -> None:
    """None y el 1 de enero de 1970 son cosas distintas, y confundirlas produce
    un paciente de 56 anios en la cohorte."""
    original = _cohorte(7)[0]
    original.ultima_consulta = None
    reconstruido = paciente_desde_documento(paciente_a_documento(original))
    assert reconstruido.ultima_consulta is None


def test_un_documento_sin_fecha_de_nacimiento_se_detiene() -> None:
    """Reconstruir un agregado a partir de un documento incompleto produce
    datos plausibles y falsos."""
    doc = paciente_a_documento(_cohorte(1)[0])
    doc["fecha_nacimiento"] = None
    with pytest.raises(ValueError):
        paciente_desde_documento(doc)


# ═══════════════════════════════════════════════════════════════════════════
# Ciclo
# ═══════════════════════════════════════════════════════════════════════════


def _ciclo_completo() -> CicloTransicion:
    """Un ciclo que ha pasado por todo: tramite, reingreso y reclasificacion."""
    ciclo = CicloTransicion(
        paciente_id="PAC-1",
        fecha_inicio=HOY - timedelta(days=300),
        fecha_nacimiento=date(2008, 5, 3),
        destino_propuesto="Neumologia",
        establecimiento_receptor="HOSPITAL NACIONAL  DOS DE MAYO",
        servicio_asignado="Neumologia — consultorio 4",
    )
    ciclo.avanzar(EstadoCiclo.REFERENCIA_ENVIADA, HOY - timedelta(days=280))
    ciclo.avanzar(EstadoCiclo.RECEPCION_CONFIRMADA, HOY - timedelta(days=270))
    ciclo.avanzar(EstadoCiclo.EN_EVALUACION, HOY - timedelta(days=250))
    ciclo.avanzar(EstadoCiclo.ACEPTADO_CON_SERVICIO, HOY - timedelta(days=200))
    ciclo.avanzar(EstadoCiclo.CITA_PROGRAMADA, HOY - timedelta(days=100))
    ciclo.avanzar(
        EstadoCiclo.PRIMERA_ATENCION_CONFIRMADA,
        HOY - timedelta(days=90),
        fuente_confirmacion=FuenteConfirmacion.CONFIRMACION_RECEPTOR,
    )
    ciclo.avanzar(
        EstadoCiclo.REINGRESO,
        HOY - timedelta(days=30),
        motivo_reingreso=MotivoReingreso.ATENDIDO_SIN_CONTINUIDAD,
    )
    ciclo.reclasificar(EstadoCiclo.ACEPTADO_CON_SERVICIO, HOY - timedelta(days=25))
    return ciclo


@pytest.mark.bloqueante
def test_ida_y_vuelta_del_ciclo_conserva_historial_y_reingresos() -> None:
    original = _ciclo_completo()
    reconstruido = ciclo_desde_documento(ciclo_a_documento(original))

    assert reconstruido.estado is original.estado
    assert reconstruido.fecha_nacimiento == original.fecha_nacimiento
    assert reconstruido.establecimiento_receptor == original.establecimiento_receptor
    assert reconstruido.servicio_asignado == original.servicio_asignado
    assert len(reconstruido.historial) == len(original.historial)
    assert reconstruido.historial == original.historial
    assert reconstruido.reingresos == original.reingresos
    assert reconstruido.fuente_de_confirmacion is original.fuente_de_confirmacion


def test_un_ciclo_del_modelo_viejo_se_lee_traducido() -> None:
    """Nada se borra para simplificar la migracion: se traduce.

    El historial se asigna directamente y no se revalida contra el grafo nuevo,
    porque un ciclo del modelo de seis contiene transiciones que el de nueve no
    permite y revalidarlas haria imposible abrir la base antigua.
    """
    documento = {
        "paciente_id": "PAC-VIEJO",
        "fecha_inicio": "2025-01-10",
        "historial": [
            {"estado": "PASAPORTE_EMITIDO", "fecha": "2025-01-10"},
            {"estado": "REFERENCIA_REGISTRADA", "fecha": "2025-01-20"},
            {"estado": "REFERENCIA_ACEPTADA", "fecha": "2025-03-05"},
        ],
    }
    ciclo = ciclo_desde_documento(documento)

    assert ciclo.historial[0].estado is EstadoCiclo.PREPARACION
    assert ciclo.historial[1].estado is EstadoCiclo.REFERENCIA_ENVIADA
    assert ciclo.estado is EstadoCiclo.ACEPTADO_CON_SERVICIO
    assert ciclo.tiene_destino_asegurado


# ═══════════════════════════════════════════════════════════════════════════
# Los tres agregados que llegaron con la fusion
# ═══════════════════════════════════════════════════════════════════════════


def test_ida_y_vuelta_del_progreso_de_aprendizaje() -> None:
    progreso = ProgresoAprendizaje(paciente_id="PAC-1")
    progreso.registrar(Habilidad.CONOZCO_MIS_DERECHOS, EstadoHabilidad.LOGRADA, HOY)
    progreso.registrar(
        Habilidad.MANEJO_MI_TRATAMIENTO,
        EstadoHabilidad.NECESITA_REFUERZO,
        HOY,
        nota="lo dejo de tomar tres semanas",
    )
    progreso.marcar_leccion_vista(6)

    reconstruido = progreso_desde_documento(progreso_a_documento(progreso))

    assert reconstruido.estados == progreso.estados
    assert reconstruido.historial == progreso.historial
    assert reconstruido.lecciones_vistas == progreso.lecciones_vistas


def test_ida_y_vuelta_de_la_conciliacion() -> None:
    paciente = _cohorte(3)[0]
    caso = conciliar(
        paciente.id,
        paciente.medicamentos,
        [MedicacionDeclarada(nombre="Omeprazol", dosis="20 mg")],
        HOY,
    )
    caso.tomar(HOY)
    caso.resolver("Dra. Rios", HOY, "Confirmado con la madre por telefono.")

    reconstruido = conciliacion_desde_documento(conciliacion_a_documento(caso))

    assert reconstruido.discrepancias == caso.discrepancias
    assert reconstruido.estado is caso.estado
    assert reconstruido.resuelto_por == caso.resuelto_por
    assert reconstruido.historial_estados == caso.historial_estados


@pytest.mark.bloqueante
def test_el_acceso_del_apoderado_no_persiste_ningun_booleano_de_acceso() -> None:
    """El fallo clasico: un `tiene_acceso` guardado seguiria valiendo True el
    dia despues del cumpleanos 18."""
    acceso = AccesoApoderado(
        paciente_id="PAC-1",
        fecha_nacimiento_paciente=date(2008, 8, 16),
        nombre_apoderado="Rosa Quispe",
        parentesco="madre",
    )
    acceso.otorgar(
        ConsentimientoExplicito(
            otorgado_por_paciente="Mateo Silva Quispe", fecha=date(2026, 8, 1)
        )
    )
    documento = acceso_a_documento(acceso)

    for clave in documento:
        assert "acceso" not in clave.lower() or clave == "paciente_id", (
            f"El documento persiste '{clave}'. El acceso se calcula en cada "
            "consulta, nunca se guarda."
        )

    reconstruido = acceso_desde_documento(documento)
    assert reconstruido.consentimiento == acceso.consentimiento
    assert reconstruido.historial == acceso.historial
    assert reconstruido.tiene_acceso(date(2026, 8, 16))


def test_la_muestra_de_semillas_no_esta_vacia() -> None:
    """Un test de ida y vuelta que no encontro pacientes pasa sin verificar."""
    assert len(_cohorte(0)) >= 3
