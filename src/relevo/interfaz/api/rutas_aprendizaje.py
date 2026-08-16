"""Entrenate: el recorrido educativo del adolescente.

Lo alimenta el PACIENTE, no el personal de salud. Es la tercera de las tres
puertas legitimas por las que entra informacion al sistema, y no es doble
digitacion porque nadie mas tenia este dato.

Ningun endpoint de aqui bloquea nada de la ruta de referencia. No existe —ni
puede existir— un puntaje que autorice la transferencia: el adolescente que
menos lecciones completa es exactamente el que mas riesgo tiene de quedarse sin
servicio a los 18.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from relevo.aplicacion.avanzar_aprendizaje import VistaAprendizaje
from relevo.dominio.entidades.leccion import Leccion
from relevo.dominio.objetos_valor.habilidad import EstadoHabilidad, Habilidad
from relevo.interfaz.api.dependencias import (
    ContenedorDep,
    HoyDep,
    RolDep,
    exigir_lectura_clinica,
    exigir_paciente,
)
from relevo.interfaz.api.esquemas import (
    AprendizajeSalida,
    AvanzarAprendizajeEntrada,
    FuenteSalida,
    HabilidadSalida,
    LeccionSalida,
    PasoSalida,
)

router = APIRouter(prefix="/api/pacientes", tags=["aprendizaje"])


def _leccion_a_salida(leccion: Leccion) -> LeccionSalida:
    return LeccionSalida(
        numero=leccion.numero,
        titulo=leccion.titulo,
        objetivo=leccion.objetivo,
        habilidad=leccion.habilidad.value,
        completa=leccion.esta_completa,
        # El sello va al frontend para que la interfaz lo pinte. Una leccion en
        # esqueleto se muestra —el adolescente ve que existe y de que va— pero
        # nunca se presenta como material validado.
        sello=leccion.sello,
        pasos=[
            PasoSalida(titulo=p.titulo, contenido=p.contenido) for p in leccion.pasos
        ],
        fuentes=[
            FuenteSalida(afirmacion=f.afirmacion, norma=f.norma, detalle=f.detalle)
            for f in leccion.fuentes
        ],
    )


def _vista_a_salida(vista: VistaAprendizaje) -> AprendizajeSalida:
    franja = vista.franja
    return AprendizajeSalida(
        paciente_id=vista.paciente_id,
        franja=franja.value if franja else None,
        franja_etiqueta=franja.etiqueta if franja else None,
        version_pasaporte=(
            franja.version_pasaporte.value
            if franja and franja.version_pasaporte
            else None
        ),
        resumen=vista.resumen,
        total_logradas=vista.total_logradas,
        habilidades=[
            HabilidadSalida(
                numero=h.numero,
                codigo=h.value,
                titulo=h.titulo,
                estado=vista.estados[h].value,
                estado_etiqueta=vista.estados[h].etiqueta,
            )
            for h in Habilidad
        ],
        siguiente_leccion=vista.siguiente.numero if vista.siguiente else None,
        motivo=vista.motivo,
        lecciones=[_leccion_a_salida(le) for le in vista.lecciones],
    )


@router.get("/{paciente_id}/aprendizaje", response_model=AprendizajeSalida)
def ver_aprendizaje(
    paciente_id: str, contenedor: ContenedorDep, hoy: HoyDep, rol: RolDep
) -> AprendizajeSalida:
    """El mapa de siete habilidades, la franja etaria y que toca ahora.

    El apoderado NO lo ve, ni siquiera con patria potestad: que un padre vea
    que su hijo no completo una leccion convierte una herramienta de autonomia
    en una de control. Lo decide `GestionarAccesoApoderado`, que devuelve
    `puede_ver_aprendizaje=False` en todos los casos.
    """
    exigir_lectura_clinica(rol)
    paciente = exigir_paciente(contenedor, paciente_id)
    progreso = contenedor.progreso_de(paciente_id)
    vista = contenedor.avanzar_aprendizaje.ver(
        progreso, paciente.edad(hoy), paciente.traq
    )
    return _vista_a_salida(vista)


@router.post("/{paciente_id}/aprendizaje/avanzar", response_model=AprendizajeSalida)
def avanzar_aprendizaje(
    paciente_id: str,
    entrada: AvanzarAprendizajeEntrada,
    contenedor: ContenedorDep,
    hoy: HoyDep,
    rol: RolDep,
) -> AprendizajeSalida:
    """Lo marca el adolescente sobre si mismo."""
    exigir_lectura_clinica(rol)
    paciente = exigir_paciente(contenedor, paciente_id)

    try:
        habilidad = Habilidad(entrada.habilidad)
        estado = EstadoHabilidad(entrada.estado)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)
        ) from error

    progreso = contenedor.progreso_de(paciente_id)
    contenedor.avanzar_aprendizaje.registrar_avance(
        progreso, habilidad, estado, hoy, nota=entrada.nota
    )
    contenedor.guardar_progreso(progreso, actor=paciente_id)

    return _vista_a_salida(
        contenedor.avanzar_aprendizaje.ver(progreso, paciente.edad(hoy), paciente.traq)
    )


@router.get("/{paciente_id}/lecciones/{numero}", response_model=LeccionSalida)
def ver_leccion(
    paciente_id: str, numero: int, contenedor: ContenedorDep, rol: RolDep
) -> LeccionSalida:
    """Abre una leccion y anota que la vio.

    Ver una leccion y lograr la habilidad son cosas distintas: si se
    confundieran, tendriamos una metrica que sube sola con solo abrir
    pantallas.
    """
    exigir_lectura_clinica(rol)
    exigir_paciente(contenedor, paciente_id)

    progreso = contenedor.progreso_de(paciente_id)
    leccion = contenedor.avanzar_aprendizaje.abrir_leccion(progreso, numero)
    if leccion is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No existe la leccion {numero}. Son siete, una por habilidad.",
        )
    contenedor.guardar_progreso(progreso, actor=paciente_id)
    return _leccion_a_salida(leccion)
