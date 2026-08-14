"""Caso de uso: priorizar la cohorte.

Orquesta el dominio y no hace nada mas. No lee archivos, no consulta el reloj,
no sabe si hay una pantalla del otro lado. Recibe los puertos ya construidos y
devuelve objetos de transporte que la interfaz pinta.

Solo importa `dominio`. `tests/test_arquitectura.py` lo verifica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.objetos_valor.indice_urgencia import EstadoSemaforo, IndiceUrgencia
from relevo.dominio.objetos_valor.ventana_transicion import Cohorte
from relevo.dominio.puertos.repositorios import RepositorioPacientes
from relevo.dominio.servicios.calculadora_iut import CalculadoraIUT, calibrar_umbral_rojo
from relevo.dominio.servicios.clasificador_cohorte import (
    ClasificadorCohorte,
    ResultadoClasificacion,
)


@dataclass(frozen=True, slots=True)
class FilaPrioridad:
    """Un paciente en la lista de trabajo, con todo lo que hay que mostrar."""

    paciente: Paciente
    indice: IndiceUrgencia
    clasificacion: ResultadoClasificacion
    meses_restantes: int
    edad: int

    @property
    def id(self) -> str:
        return self.paciente.id

    @property
    def estado(self) -> EstadoSemaforo:
        return self.indice.estado

    @property
    def requiere_atencion_ahora(self) -> bool:
        """Rojo, o cualquiera al que le queden menos de seis meses.

        Los seis meses no salen del indice: salen de que preparar un traspaso
        —conseguir cita, verificar contacto, emitir el Pasaporte— lleva tiempo,
        y el corte a los 18 no se mueve.
        TODO: confirmar con mentor — cuanto tarda de verdad preparar un traspaso.
        """
        return self.estado is EstadoSemaforo.ROJO or 0 <= self.meses_restantes < 6


@dataclass(frozen=True, slots=True)
class ResultadoPriorizacion:
    """La lista completa mas lo que hace falta para leerla con criterio."""

    fecha: date
    filas: tuple[FilaPrioridad, ...] = field(default_factory=tuple)
    umbral_rojo: float = 0.0
    umbral_calibrado: bool = False
    """True si el umbral salio de la capacidad real del equipo y no del YAML."""

    total_evaluados: int = 0
    no_elegibles: int = 0

    @property
    def rojos(self) -> tuple[FilaPrioridad, ...]:
        return tuple(f for f in self.filas if f.estado is EstadoSemaforo.ROJO)

    @property
    def ambares(self) -> tuple[FilaPrioridad, ...]:
        return tuple(f for f in self.filas if f.estado is EstadoSemaforo.AMBAR)

    @property
    def verdes(self) -> tuple[FilaPrioridad, ...]:
        return tuple(f for f in self.filas if f.estado is EstadoSemaforo.VERDE)

    @property
    def con_datos_insuficientes(self) -> tuple[FilaPrioridad, ...]:
        """Aquellos cuyo puntaje se apoya demasiado en supuestos.

        Se muestran aparte porque son una lista de trabajo distinta: no hay que
        atenderlos clinicamente, hay que ir a buscar el dato que falta.
        """
        return tuple(f for f in self.filas if f.indice.datos_insuficientes)

    @property
    def sin_contacto_vigente(self) -> tuple[FilaPrioridad, ...]:
        return tuple(f for f in self.filas if f.clasificacion.requiere_captura_contacto)

    def por_cohorte(self, cohorte: Cohorte) -> tuple[FilaPrioridad, ...]:
        return tuple(f for f in self.filas if f.clasificacion.cohorte is cohorte)


class PriorizarCohorte:
    """Recorre el padron, descarta a quien no corresponde y ordena al resto."""

    def __init__(
        self,
        repositorio: RepositorioPacientes,
        calculadora: CalculadoraIUT,
        clasificador: ClasificadorCohorte,
    ) -> None:
        self._repositorio = repositorio
        self._calculadora = calculadora
        self._clasificador = clasificador

    def ejecutar(
        self,
        hoy: date,
        capacidad_mensual: int | None = None,
        incluir_seguimiento: bool = True,
    ) -> ResultadoPriorizacion:
        """La lista de trabajo del dia.

        Si se pasa `capacidad_mensual`, el umbral rojo se recalibra contra ella
        en una segunda pasada: marcar en rojo a mas pacientes de los que el
        equipo puede atender no prioriza nada.
        """
        pacientes = self._repositorio.listar_todos()
        candidatos: list[tuple[Paciente, ResultadoClasificacion]] = []
        no_elegibles = 0

        for paciente in pacientes:
            clasificacion = self._clasificador.clasificar(paciente, hoy)
            if not clasificacion.entra_al_sistema:
                no_elegibles += 1
                continue
            if not incluir_seguimiento and clasificacion.cohorte is Cohorte.SEGUIMIENTO:
                continue
            candidatos.append((paciente, clasificacion))

        umbral = self._calculadora.parametros.umbral_rojo
        calibrado = False
        if capacidad_mensual is not None:
            # Primera pasada solo para conocer la distribucion de la cohorte.
            provisionales = [
                self._calculadora.calcular(p, hoy).valor for p, _ in candidatos
            ]
            umbral = calibrar_umbral_rojo(provisionales, capacidad_mensual)
            calibrado = True

        filas = [
            FilaPrioridad(
                paciente=paciente,
                indice=self._calculadora.calcular(paciente, hoy, umbral_rojo=umbral),
                clasificacion=clasificacion,
                meses_restantes=paciente.meses_hasta_corte(hoy),
                edad=paciente.edad(hoy),
            )
            for paciente, clasificacion in candidatos
        ]
        filas.sort(key=lambda f: f.indice.valor, reverse=True)

        return ResultadoPriorizacion(
            fecha=hoy,
            filas=tuple(filas),
            umbral_rojo=umbral,
            umbral_calibrado=calibrado,
            total_evaluados=len(pacientes),
            no_elegibles=no_elegibles,
        )
