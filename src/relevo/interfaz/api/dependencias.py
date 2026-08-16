"""Lo que comparten todos los routers: el contenedor, la fecha y el rol.

El contenedor se construye UNA vez y se reutiliza. Se pide siempre por
inyeccion de dependencias de FastAPI y nunca como variable global importada,
para que un test pueda sustituirlo por otro con `app.dependency_overrides`.

Ningun archivo de esta carpeta importa `relevo.infraestructura`: todo lo
concreto llega ya montado desde `interfaz/arranque.py`, que es el unico sitio
del proyecto autorizado a conocer adaptadores. `tests/test_arquitectura.py` lo
vigila.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status

from relevo.dominio.entidades.ciclo_transicion import CicloTransicion
from relevo.dominio.entidades.paciente import Paciente
from relevo.interfaz.api.roles import Rol
from relevo.interfaz.arranque import Contenedor, construir

# Fecha de la demo. El dominio nunca lee el reloj del sistema —un dominio que
# consulta la hora no se puede probar— y aqui pasa lo mismo por un motivo
# distinto: el pitch se ensaya contra una cohorte fija, y si "hoy" cambiara
# cada dia, los plazos vencidos del ensayo dejarian de coincidir.
FECHA_DEMO = date(2026, 8, 16)

# Cabecera con la que la demo declara su rol mientras no hay sesion de
# servidor. Se sustituye por la cookie de sesion en C6; hasta entonces la
# interfaz manda el rol elegido en la pantalla de entrada.
CABECERA_ROL = "X-Relevo-Rol"
CABECERA_ESTABLECIMIENTO = "X-Relevo-Establecimiento"


@lru_cache(maxsize=1)
def _contenedor_compartido() -> Contenedor:
    return construir()


def obtener_contenedor() -> Contenedor:
    """El sistema completo, ya cableado."""
    return _contenedor_compartido()


def reiniciar_contenedor() -> None:
    """Olvida el contenedor cacheado. Lo usa la barra de control de demo."""
    _contenedor_compartido.cache_clear()


def obtener_hoy(
    hoy: Annotated[date | None, Query(description="fecha de evaluacion")] = None,
) -> date:
    """La fecha contra la que se evalua todo.

    Se admite por parametro para poder demostrar el paso del tiempo delante del
    jurado sin tocar el reloj de la maquina: cambiar `?hoy=` y ver como se
    mueven los plazos y la metrica de corte etario es media demostracion.
    """
    return hoy or FECHA_DEMO


def obtener_rol(request: Request) -> Rol:
    """El rol de quien pide. Sin sesion todavia: ver C6.

    Por defecto PACIENTE y no ADMINISTRADOR: si la cabecera falta por un error,
    el fallo tiene que dejar ver MENOS, nunca mas.
    """
    crudo = (request.headers.get(CABECERA_ROL) or "").strip()
    try:
        return Rol(crudo)
    except ValueError:
        return Rol.PACIENTE


def obtener_establecimiento(request: Request) -> str:
    """El establecimiento del profesional receptor, para el aislamiento."""
    return (request.headers.get(CABECERA_ESTABLECIMIENTO) or "").strip()


ContenedorDep = Annotated[Contenedor, Depends(obtener_contenedor)]
HoyDep = Annotated[date, Depends(obtener_hoy)]
RolDep = Annotated[Rol, Depends(obtener_rol)]
EstablecimientoDep = Annotated[str, Depends(obtener_establecimiento)]


# ═══════════════════════════════════════════════════════════════════════════
# Aislamiento por rol
# ═══════════════════════════════════════════════════════════════════════════


# Un unico mensaje para TODOS los 404 de paciente y de ciclo.
#
# No es pereza: es la mitad de la regla del 404. Si "no existe", "no tiene
# ciclo" y "no es tuyo" respondieran cuerpos distintos, los tres seguirian
# siendo distinguibles aunque los tres devolvieran 404 — y con eso se puede
# enumerar la cohorte pediatrica del INSN igual de bien que con un 403.
#
# El coste es que el equipo del INSN pierde el matiz "existe pero sin ciclo".
# Lo compensa la lista del radar, que ya dice quien tiene ciclo y quien no.
NO_ENCONTRADO = "Paciente no encontrado"


def exigir_paciente(contenedor: Contenedor, paciente_id: str) -> Paciente:
    paciente = contenedor.paciente(paciente_id)
    if paciente is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    return paciente


def exigir_ciclo(contenedor: Contenedor, paciente_id: str) -> CicloTransicion:
    ciclo = contenedor.ciclo_de(paciente_id)
    if ciclo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    return ciclo


def exigir_visibilidad(
    ciclo: CicloTransicion, rol: Rol, establecimiento: str
) -> None:
    """El receptor solo ve lo que le fue referido. Lo demas es 404, no 403.

    ═══════════════════════════════════════════════════════════════════════════
    POR QUE 404 Y NO 403
    ═══════════════════════════════════════════════════════════════════════════

    Un 403 confirma que el paciente EXISTE. Con eso, cualquiera con una cuenta
    de receptor podria averiguar, probando identificadores, quienes estan en la
    cohorte pediatrica del INSN — sin llegar a ver un solo dato clinico y sin
    romper ninguna comprobacion de permisos.

    Un 404 no distingue entre "no existe" y "no es tuyo", que es justo lo que
    hace falta. La fuga por codigo de estado es de las mas faciles de
    introducir sin darse cuenta.
    """
    if rol is not Rol.PROFESIONAL_RECEPTOR:
        return
    if not establecimiento:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    if _normalizar(ciclo.establecimiento_receptor) != _normalizar(establecimiento):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)


def exigir_lectura_clinica(rol: Rol) -> None:
    """El ADMINISTRADOR no abre un Pasaporte ni una historia.

    Puede sembrar, reiniciar, ver metricas agregadas y verificar la cadena de
    auditoria. Su acceso al archivo SQLite es inevitable; lo que la interfaz
    puede hacer es no ofrecerselo, y la cadena de hash se encarga del resto.
    """
    if not rol.puede_leer_datos_clinicos:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El rol de administrador no tiene lectura clinica. Puede "
            "administrar el sistema y verificar la cadena de auditoria.",
        )


def _normalizar(nombre: str) -> str:
    """Compara nombres de establecimiento sin pelearse por los espacios.

    El catalogo RENIPRESS trae nombres con espacios dobles
    ('HOSPITAL NACIONAL  DOS DE MAYO'), y un filtro de seguridad que falla por
    un espacio de mas es un filtro que alguien va a desactivar.
    """
    return " ".join(nombre.upper().split())
