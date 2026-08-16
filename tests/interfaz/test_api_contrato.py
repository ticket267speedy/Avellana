"""Contrato de la API: caso feliz y caso de error por endpoint.

Lo que se verifica no es solo que responda, sino que responda con el CODIGO
CORRECTO. Un 200 con un cuerpo de error es peor que un 500: el cliente lo trata
como exito.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.interfaz.conftest import HOY


# ═══════════════════════════════════════════════════════════════════════════
# Sistema
# ═══════════════════════════════════════════════════════════════════════════


def test_salud_responde_sin_tocar_la_base(cliente: TestClient) -> None:
    """Deliberadamente tonta: si consultara SQLite o Ollama, un fallo de
    cualquiera de los dos haria parecer caida la aplicacion entera."""
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["datos_sinteticos"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Radar y paciente
# ═══════════════════════════════════════════════════════════════════════════


def test_el_radar_devuelve_la_cohorte_ordenada_por_iut(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    respuesta = cliente.get("/api/pacientes", headers=insn)
    assert respuesta.status_code == 200

    filas = respuesta.json()
    assert filas
    valores = [f["indice"]["valor"] for f in filas]
    assert valores == sorted(valores, reverse=True)


def test_cada_fila_del_radar_trae_su_desglose_completo(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    """Un indice sin explicacion es un dato invalido en este dominio.

    El desglose es lo que convierte "priorizacion autonoma" —que el INSN
    excluyo de su alcance— en una lista ordenada que un medico puede discutir.
    """
    fila = cliente.get("/api/pacientes", headers=insn).json()[0]
    aportes = fila["indice"]["aportes"]

    assert len(aportes) == 8  # los ocho factores del IUT
    for aporte in aportes:
        assert {"nombre", "valor", "beta", "aporte", "dato_faltante"} <= set(aporte)


def test_un_paciente_que_no_existe_da_404(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    assert cliente.get("/api/pacientes/NO-EXISTE", headers=insn).status_code == 404


def test_la_dosis_no_verificada_sale_como_hueco_y_no_como_numero(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    """Regla 8, comprobada en la frontera HTTP y no solo en el dominio."""
    datos = cliente.get("/api/pacientes/DEMO-0001", headers=insn).json()
    idursulfasa = next(m for m in datos["medicamentos"] if "Idursulfasa" in m)
    assert "____" in idursulfasa


# ═══════════════════════════════════════════════════════════════════════════
# Ciclo
# ═══════════════════════════════════════════════════════════════════════════


def test_el_ciclo_dice_quien_tiene_el_turno(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    datos = cliente.get("/api/pacientes/DEMO-0001/ciclo", headers=insn).json()

    assert datos["estado"] == "en_evaluacion"
    assert datos["responsable"] == "hospital_receptor"
    assert datos["responsable_etiqueta"] == "Hospital receptor"


def test_el_ciclo_trae_las_siete_etapas_de_la_linea_de_tiempo(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    etapas = cliente.get("/api/pacientes/DEMO-0001/ciclo", headers=insn).json()["etapas"]

    assert len(etapas) == 7
    assert [e["orden"] for e in etapas] == list(range(7))
    # Cada etapa trae su version en lenguaje llano para la vista del paciente.
    assert all(e["etiqueta_llana"] for e in etapas)
    assert sum(1 for e in etapas if e["es_actual"]) == 1


def test_una_transicion_fuera_del_grafo_responde_409(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    """409 y no 422: la peticion esta bien formada, el ciclo no esta donde el
    cliente cree. Suele significar que otra persona ya lo movio."""
    respuesta = cliente.post(
        "/api/pacientes/DEMO-0001/ciclo/avanzar",
        headers=insn,
        json={"estado": "primera_atencion_confirmada"},
    )
    assert respuesta.status_code == 409


def test_un_estado_inexistente_responde_422(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    respuesta = cliente.post(
        "/api/pacientes/DEMO-0001/ciclo/avanzar",
        headers=insn,
        json={"estado": "estado_inventado"},
    )
    assert respuesta.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Receptor
# ═══════════════════════════════════════════════════════════════════════════


def test_la_bandeja_ordena_por_dias_para_el_corte(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """Para el receptor, la referencia urgente no es la mas antigua sino la del
    adolescente que se queda sin ningun servicio dentro de tres semanas."""
    filas = cliente.get("/api/receptor/bandeja", headers=receptor).json()
    assert filas

    dias = [f["dias_para_corte"] for f in filas if f["dias_para_corte"] is not None]
    assert dias == sorted(dias)


def test_la_bandeja_no_muestra_ciclos_en_preparacion(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """Un ciclo en preparacion todavia no salio del INSN."""
    filas = cliente.get("/api/receptor/bandeja", headers=receptor).json()
    assert all(f["estado"] != "preparacion" for f in filas)


def test_cada_fila_ofrece_solo_las_acciones_que_tocan(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """Una bandeja que muestra las seis acciones siempre obliga al profesional a
    razonar cual toca, que es el trabajo que el sistema deberia ahorrarle."""
    filas = cliente.get("/api/receptor/bandeja", headers=receptor).json()
    for fila in filas:
        assert len(fila["acciones"]) <= 2


def test_una_accion_inexistente_del_receptor_da_404(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    respuesta = cliente.post(
        "/api/receptor/DEMO-0001/bailar", headers=receptor, json={}
    )
    assert respuesta.status_code == 404


def test_solicitar_informacion_sin_decir_que_falta_es_422(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """Una peticion vacia es un rechazo silencioso con otro nombre, que es justo
    lo que esta accion viene a evitar."""
    respuesta = cliente.post(
        "/api/receptor/DEMO-0001/solicitar_informacion",
        headers=receptor,
        json={"faltantes": []},
    )
    assert respuesta.status_code == 422


def test_solicitar_informacion_devuelve_el_turno_sin_cambiar_de_estado(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """La accion mas importante de las seis: convierte un rechazo silencioso en
    una peticion trazable.

    NO retrocede el estado a proposito: eso borraria del historial que el
    expediente si llego a evaluarse.
    """
    antes = cliente.get("/api/pacientes/DEMO-0001/ciclo", headers=receptor).json()
    respuesta = cliente.post(
        "/api/receptor/DEMO-0001/solicitar_informacion",
        headers=receptor,
        json={"faltantes": ["falta_epicrisis"], "quien": "Dr. Vega"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["devolvio_el_turno"] is True
    assert cuerpo["estado"] == antes["estado"]

    despues = cliente.get("/api/pacientes/DEMO-0001/ciclo", headers=receptor).json()
    assert len(despues["historial"]) == len(antes["historial"]) + 1
    assert "epicrisis" in despues["historial"][-1]["nota"].lower()


def test_aceptar_sin_servicio_no_se_permite(
    cliente: TestClient, receptor: dict[str, str]
) -> None:
    """Una aceptacion sin servicio concreto es una carta amable que no le da
    cita a nadie."""
    respuesta = cliente.post(
        "/api/receptor/DEMO-0001/aceptar_con_servicio",
        headers=receptor,
        json={"servicio": "  "},
    )
    assert respuesta.status_code == 409


# ═══════════════════════════════════════════════════════════════════════════
# Metricas
# ═══════════════════════════════════════════════════════════════════════════


def test_la_metrica_de_corte_etario_separa_riesgo_de_dano(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    datos = cliente.get("/api/metricas/corte-etario", headers=insn).json()

    assert datos["horizonte_dias"] == 90
    assert datos["total_cohorte"] > 0
    assert len(datos["en_riesgo"]) == datos["en_riesgo_90_dias"]
    assert len(datos["consumados"]) == datos["ya_cumplieron_sin_destino"]
    assert "cumplen 18" in datos["titular"]


def test_la_cobertura_de_destinos_no_esconde_el_cien_por_ciento(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    """Con el directorio sin confirmar, la cifra es 100 % sin destino. ESA
    CIFRA ES EL ENTREGABLE DE B1: el sistema no inventa destinos, mide su
    ausencia. El propio INSN escribio que la falta de datos tambien es un
    hallazgo."""
    datos = cliente.get("/api/metricas/cobertura-destinos", headers=insn).json()

    assert datos["total_evaluados"] > 0
    assert datos["sin_destino"] == datos["total_evaluados"] - datos["con_destino"]
    assert datos["por_motivo"]
    assert datos["resumen_directorio"]


def test_la_metrica_declara_los_ciclos_que_no_pudo_evaluar(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    """Un denominador que excluye casos en silencio produce una metrica que
    mejora sola cuando empeoran los datos."""
    datos = cliente.get("/api/metricas/corte-etario", headers=insn).json()
    assert "sin_fecha_de_nacimiento" in datos


# ═══════════════════════════════════════════════════════════════════════════
# Aprendizaje
# ═══════════════════════════════════════════════════════════════════════════


def test_el_aprendizaje_muestra_las_siete_habilidades_siempre(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    datos = cliente.get("/api/pacientes/DEMO-0001/aprendizaje", headers=paciente).json()

    assert len(datos["habilidades"]) == 7
    assert len(datos["lecciones"]) == 7
    assert datos["franja"] == "ya"
    assert datos["version_pasaporte"] == "v3"


def test_seis_lecciones_van_selladas_como_pendientes_de_validacion(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    """Un esqueleto honesto es mas fuerte ante un jurado clinico que siete
    lecciones que nadie del equipo puede defender."""
    lecciones = cliente.get(
        "/api/pacientes/DEMO-0001/aprendizaje", headers=paciente
    ).json()["lecciones"]

    completas = [le for le in lecciones if le["completa"]]
    esqueletos = [le for le in lecciones if not le["completa"]]

    assert len(completas) == 1
    assert completas[0]["numero"] == 6
    assert len(esqueletos) == 6
    for le in esqueletos:
        assert le["sello"] == "Contenido pendiente de validacion clinica del INSN"


def test_la_leccion_completa_cita_sus_fuentes(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    """Una leccion que le dice a un adolescente que su madre ya no puede pedir
    sus resultados tiene que decir en que norma esta escrito."""
    leccion = cliente.get(
        "/api/pacientes/DEMO-0001/lecciones/6", headers=paciente
    ).json()

    assert leccion["completa"]
    assert leccion["sello"] is None
    assert len(leccion["fuentes"]) >= 4
    normas = " ".join(f["norma"] for f in leccion["fuentes"])
    assert "29733" in normas
    assert all(paso["contenido"].strip() for paso in leccion["pasos"])


def test_una_leccion_que_no_existe_da_404(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    respuesta = cliente.get("/api/pacientes/DEMO-0001/lecciones/99", headers=paciente)
    assert respuesta.status_code == 404


def test_avanzar_una_habilidad_inexistente_da_422(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    respuesta = cliente.post(
        "/api/pacientes/DEMO-0001/aprendizaje/avanzar",
        headers=paciente,
        json={"habilidad": "volar", "estado": "lograda"},
    )
    assert respuesta.status_code == 422


def test_el_traq_decide_la_recomendacion(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    """El TRAQ deja de ser un numero de reporte y pasa a ser el diagnostico que
    decide la intervencion. Ese es el cierre del bucle medir -> intervenir."""
    datos = cliente.get("/api/pacientes/DEMO-0001/aprendizaje", headers=paciente).json()
    assert datos["siguiente_leccion"] is not None
    assert "2.4" in datos["motivo"]  # el TRAQ del caso protagonista


# ═══════════════════════════════════════════════════════════════════════════
# Conciliacion
# ═══════════════════════════════════════════════════════════════════════════


def test_declarar_medicacion_abre_un_caso_para_el_insn(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    respuesta = cliente.post(
        "/api/pacientes/DEMO-0002/medicacion/declarar",
        headers=paciente,
        json={
            "medicamentos": [
                {"nombre": "Budesonida/Formoterol", "dosis": "320/9 mcg"},
                {"nombre": "Montelukast", "dosis": "10 mg"},
            ]
        },
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["requiere_revision"] is True
    assert datos["responsable"] == "Equipo de transicion del INSN"

    tipos = {d["tipo"] for d in datos["discrepancias"]}
    assert "dosis_distinta" in tipos
    assert "falta_en_pasaporte" in tipos


def test_lo_declarado_no_sobrescribe_el_pasaporte(
    cliente: TestClient, paciente: dict[str, str], insn: dict[str, str]
) -> None:
    """La regla, comprobada de punta a punta: el paciente declara otra dosis y
    el expediente sigue diciendo la suya."""
    antes = cliente.get("/api/pacientes/DEMO-0002", headers=insn).json()["medicamentos"]
    cliente.post(
        "/api/pacientes/DEMO-0002/medicacion/declarar",
        headers=paciente,
        json={"medicamentos": [{"nombre": "Budesonida/Formoterol", "dosis": "999 mcg"}]},
    )
    despues = cliente.get("/api/pacientes/DEMO-0002", headers=insn).json()["medicamentos"]

    assert antes == despues
    assert not any("999" in m for m in despues)


def test_resolver_una_conciliacion_sin_nota_es_422(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    respuesta = cliente.post(
        "/api/insn/DEMO-0002/conciliacion/resolver",
        headers=insn,
        json={"quien": "Dra. Rios", "nota": ""},
    )
    assert respuesta.status_code == 422


def test_cada_linea_de_medicacion_dice_de_donde_sale(
    cliente: TestClient, paciente: dict[str, str]
) -> None:
    lineas = cliente.get(
        "/api/pacientes/DEMO-0002/conciliacion", headers=paciente
    ).json()["lineas"]

    origenes = {le["origen"] for le in lineas}
    assert origenes <= {
        "verificado_insn",
        "informado_por_paciente",
        "pendiente_de_cotejo",
    }
    assert all(le["insignia"] for le in lineas)


# ═══════════════════════════════════════════════════════════════════════════
# Apoderado
# ═══════════════════════════════════════════════════════════════════════════


def test_el_apoderado_de_un_menor_ve_el_estado_del_ciclo(
    cliente: TestClient
) -> None:
    datos = cliente.get("/api/apoderado/DEMO-0001/permisos").json()

    assert datos["puede_ver_estado_del_ciclo"] is True
    assert datos["base_legal"] == "patria_potestad"
    assert "418" in datos["norma"]


def test_el_apoderado_nunca_ve_el_recorrido_de_aprendizaje(
    cliente: TestClient
) -> None:
    """Que un padre vea que su hijo no completo una leccion convierte una
    herramienta de autonomia en una de control."""
    datos = cliente.get("/api/apoderado/DEMO-0001/permisos").json()
    assert datos["puede_ver_aprendizaje"] is False


def test_se_avisa_de_la_caducidad_antes_de_que_ocurra(cliente: TestClient) -> None:
    """El corte no puede ser una sorpresa: la familia tiene que poder hablarlo
    antes, no descubrirlo el dia que deja de funcionar."""
    datos = cliente.get(
        "/api/apoderado/DEMO-0001/permisos", params={"hoy": "2027-02-01"}
    ).json()

    assert datos["aviso"] is not None
    assert 0 < datos["dias_para_el_corte"] <= 90


def test_pasado_el_cumpleanios_el_acceso_esta_cortado(cliente: TestClient) -> None:
    datos = cliente.get(
        "/api/apoderado/DEMO-0001/permisos", params={"hoy": "2027-05-01"}
    ).json()

    assert datos["puede_ver_estado_del_ciclo"] is False
    assert datos["base_legal"] == "sin_base"
    assert "Solo el paciente" in (datos["aviso"] or "")


# ═══════════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════════


def test_el_estado_de_la_demo_declara_que_los_datos_son_sinteticos(
    cliente: TestClient,
) -> None:
    datos = cliente.get("/api/demo/estado").json()
    assert datos["es_demo"] is True
    assert datos["cadena_intacta"] is True
    assert "sinteticos" in datos["aviso"]


def test_cambiar_a_un_rol_inexistente_es_422(cliente: TestClient) -> None:
    respuesta = cliente.post("/api/demo/cambiar-rol", json={"rol": "presidente"})
    assert respuesta.status_code == 422


def test_cambiar_de_rol_dice_a_donde_va_y_que_no_es_autenticacion(
    cliente: TestClient,
) -> None:
    datos = cliente.post(
        "/api/demo/cambiar-rol", json={"rol": "profesional_receptor"}
    ).json()

    assert datos["ruta_inicial"] == "#/receptor/bandeja"
    assert "no es autenticacion" in datos["aviso"]


def test_la_fecha_se_puede_mover_para_demostrar_el_paso_del_tiempo(
    cliente: TestClient, insn: dict[str, str]
) -> None:
    """Cambiar `?hoy=` y ver como se mueven los plazos y la metrica de corte
    etario es media demostracion."""
    hoy = cliente.get("/api/metricas/corte-etario", headers=insn).json()
    futuro = cliente.get(
        "/api/metricas/corte-etario", headers=insn, params={"hoy": "2027-08-16"}
    ).json()

    assert futuro["ya_cumplieron_sin_destino"] >= hoy["ya_cumplieron_sin_destino"]
    assert str(HOY) == "2026-08-16"
