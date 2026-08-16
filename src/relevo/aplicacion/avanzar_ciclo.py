"""Caso de uso: mover el ciclo de un paciente al siguiente estado.

Es el clic. Todo el sistema de nueve estados, responsables y plazos existe para
que este caso de uso sea lo unico que un profesional tiene que hacer.

PRINCIPIO DE CERO DOBLE DIGITACION
Este caso de uso no recibe ni un solo dato clinico. Recibe: que ciclo, a que
estado, quien lo registra y cuando. El dato clinico entra por el extractor con
verificacion y firma, nunca por aqui.

    Relevo no pide datos. Pide decisiones.

Importa solo `dominio`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from relevo.dominio.entidades.ciclo_transicion import (
    CicloTransicion,
    EstadoCiclo,
    EventoCiclo,
    FuenteConfirmacion,
)
from relevo.dominio.excepciones import TransicionInvalida
from relevo.dominio.objetos_valor.reingreso import MotivoReingreso
from relevo.dominio.objetos_valor.responsable import Responsable, responsable_de
from relevo.dominio.servicios.maquina_ciclo import (
    EvaluacionPlazo,
    MaquinaCiclo,
)


@dataclass(frozen=True, slots=True)
class ResultadoAvance:
    """Que paso y quien tiene el turno ahora.

    Devuelve el responsable NUEVO y no solo el evento porque es la unica
    pregunta que el profesional se hace despues de hacer clic: "¿ya no es cosa
    mia?". Obligarle a consultarlo aparte convierte una respuesta en un paso
    mas.
    """

    ciclo: CicloTransicion
    evento: EventoCiclo
    responsable_anterior: Responsable
    responsable_nuevo: Responsable
    evaluacion: EvaluacionPlazo

    @property
    def cambio_de_turno(self) -> bool:
        return self.responsable_anterior is not self.responsable_nuevo

    @property
    def gano_destino_asegurado(self) -> bool:
        """True si este avance saco al paciente del riesgo de corte etario.

        Es el momento que el sistema entero persigue, y merece que la interfaz
        lo celebre en vez de pintarlo como una transicion mas.
        """
        return self.ciclo.tiene_destino_asegurado

    def titular(self) -> str:
        return (
            f"{self.ciclo.paciente_id}: {self.evento.estado.etiqueta} · "
            f"turno de {self.responsable_nuevo.etiqueta}"
        )


@dataclass(frozen=True, slots=True)
class AvanzarCiclo:
    """Aplica una transicion, la valida y dice quien sigue.

    `maquina` se inyecta porque los plazos son politica clinica que se carga de
    `config/`: este caso de uso no sabe cuantos dias dura nada.
    """

    maquina: MaquinaCiclo

    def ejecutar(
        self,
        ciclo: CicloTransicion,
        estado: EstadoCiclo,
        hoy: date,
        registrado_por: str = "",
        fuente_confirmacion: FuenteConfirmacion | None = None,
        motivo_reingreso: MotivoReingreso | None = None,
        nota_administrativa: str = "",
    ) -> ResultadoAvance:
        """Mueve el ciclo. Lanza `TransicionInvalida` si el grafo no lo permite.

        `nota_administrativa` se llama asi y no `nota` a proposito: el nombre
        del parametro es parte de la regla. Un campo llamado `nota` acabaria
        recibiendo diagnosticos.
        """
        anterior = ciclo.responsable
        evento = ciclo.avanzar(
            estado=estado,
            fecha=hoy,
            registrado_por=registrado_por,
            fuente_confirmacion=fuente_confirmacion,
            motivo_reingreso=motivo_reingreso,
            nota=nota_administrativa,
        )
        return ResultadoAvance(
            ciclo=ciclo,
            evento=evento,
            responsable_anterior=anterior,
            responsable_nuevo=ciclo.responsable,
            evaluacion=self.maquina.evaluar(ciclo, hoy),
        )

    def reclasificar(
        self,
        ciclo: CicloTransicion,
        estado: EstadoCiclo,
        hoy: date,
        registrado_por: str = "",
    ) -> ResultadoAvance:
        """Saca un ciclo de REINGRESO. Ver `CicloTransicion.reclasificar`."""
        anterior = ciclo.responsable
        evento = ciclo.reclasificar(estado, hoy, registrado_por=registrado_por)
        return ResultadoAvance(
            ciclo=ciclo,
            evento=evento,
            responsable_anterior=anterior,
            responsable_nuevo=ciclo.responsable,
            evaluacion=self.maquina.evaluar(ciclo, hoy),
        )

    def siguiente_paso_natural(self, ciclo: CicloTransicion) -> EstadoCiclo | None:
        """El avance de un solo boton. None si no hay uno obvio."""
        return ciclo.siguiente_estado

    def exigir_turno(self, ciclo: CicloTransicion, quien: Responsable) -> None:
        """Comprueba que a quien pide el avance le toca.

        No es autorizacion —eso vive en la capa de interfaz— sino coherencia de
        proceso: que el INSN registre por su cuenta que el receptor acepto una
        referencia produce un dato que el piloto no puede usar, porque nadie
        sabe si el receptor lo confirmo de verdad.
        """
        real = responsable_de(ciclo.estado)
        if real is not quien:
            raise TransicionInvalida(
                f"El turno de {ciclo.paciente_id} es de {real.etiqueta}, no de "
                f"{quien.etiqueta}."
            )
