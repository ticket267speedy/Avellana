"""El proceso nocturno. Corre solo, no le pide nada a nadie.

    python -m relevo.interfaz.cli.correr_noche
    python -m relevo.interfaz.cli.correr_noche --hoy 2026-12-01 --destinatario coordinacion@insnsb.gob.pe

QUE HACE Y POR QUE IMPORTA
Recorre los ciclos abiertos, evalua plazos y deja la bandeja de avisos escrita.
Nadie tiene que abrir una pantalla ni acordarse de mirar: al dia siguiente esta
el correo.

Ese es el principio rector del proyecto —*el sistema busca a la persona; la
persona no busca al sistema*— convertido en algo que se puede ejecutar. Hasta
ahora existia como frase en el dossier y como maquina de plazos sin nadie que
la corriera.

SI NO HAY NADA QUE AVISAR, NO ESCRIBE NADA. Un aviso que llega siempre deja de
leerse, y el silencio tambien es informacion: significa que nada esta parado.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from relevo.aplicacion.despachar_avisos import DespacharAvisos
from relevo.aplicacion.evaluar_vencimientos import EvaluarVencimientos
from relevo.dominio.entidades.ciclo_transicion import CicloTransicion, EstadoCiclo
from relevo.dominio.servicios.maquina_ciclo import MaquinaCiclo
from relevo.infraestructura.configuracion.cargador_yaml import cargar_politica_plazos
from relevo.infraestructura.notificacion.canal_archivo import CanalCorreoArchivo
from relevo.infraestructura.persistencia.repositorio_memoria import (
    RepositorioCiclosMemoria,
)


def _ciclos_de_ejemplo(hoy: date) -> list[CicloTransicion]:
    """Ciclos sinteticos en distintos puntos del recorrido.

    Mientras no haya persistencia real, esto es lo que permite demostrar el
    proceso completo. Las fechas se calculan hacia atras desde `hoy` para que
    siempre haya casos vencidos, por vencer y en plazo — si no, la demo del
    proceso nocturno dependeria de que fecha sea el dia de la presentacion.
    """
    ciclos: list[CicloTransicion] = []

    # Vencido de sobra: registro de referencia parado 40 dias (plazo: 7).
    c1 = CicloTransicion(paciente_id="PAC-0042", fecha_inicio=hoy - timedelta(days=40))
    ciclos.append(c1)

    # Aceptada hace 130 dias sin cita programada (plazo: 120).
    c2 = CicloTransicion(paciente_id="PAC-0117", fecha_inicio=hoy - timedelta(days=200))
    c2.avanzar(EstadoCiclo.REFERENCIA_REGISTRADA, hoy - timedelta(days=195))
    c2.avanzar(EstadoCiclo.REFERENCIA_ACEPTADA, hoy - timedelta(days=130))
    ciclos.append(c2)

    # Recien emitido: en plazo, no debe generar aviso.
    ciclos.append(
        CicloTransicion(paciente_id="PAC-0203", fecha_inicio=hoy - timedelta(days=2))
    )
    return ciclos


def main() -> int:
    p = argparse.ArgumentParser(description="Proceso nocturno de Relevo")
    p.add_argument(
        "--hoy",
        type=date.fromisoformat,
        default=date.today(),
        help="fecha de evaluacion (ISO). Por defecto, hoy.",
    )
    p.add_argument(
        "--destinatario",
        default="coordinacion.transicion@insnsb.gob.pe",
        help="a quien va el correo del equipo",
    )
    p.add_argument(
        "--salida", type=Path, default=Path("salidas/avisos"),
        help="carpeta donde se escribe la bandeja",
    )
    args = p.parse_args()

    politica = cargar_politica_plazos()
    repositorio = RepositorioCiclosMemoria()
    for ciclo in _ciclos_de_ejemplo(args.hoy):
        repositorio.guardar(ciclo)

    evaluar = EvaluarVencimientos(
        repositorio=repositorio, maquina=MaquinaCiclo(politica)
    )
    despachar = DespacharAvisos(canal_equipo=CanalCorreoArchivo(carpeta=args.salida))

    resultado = evaluar.ejecutar(args.hoy, destinatario=args.destinatario)

    print(f"Proceso nocturno · {args.hoy.isoformat()}")
    print(f"  ciclos revisados : {resultado.ciclos_revisados}")
    print(f"  vencidos         : {len(resultado.vencidos)}")
    print(f"  por vencer       : {len(resultado.por_vencer)}")

    for evento in resultado.eventos:
        print(f"    · {evento.descripcion}")

    resumen = despachar.ejecutar(resultado.eventos, args.destinatario)
    for detalle in resumen.detalles:
        print(f"  {detalle}")

    if not resultado.hay_algo_que_avisar:
        print("  (sin novedades: no se envia correo, y eso es correcto)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
