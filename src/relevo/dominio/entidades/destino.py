"""A donde se deriva al paciente. El dolor B1, por fin nombrado.

POR QUE ESTE ARCHIVO ES CORTO Y AUN ASI IMPORTA
B1 del dossier — "no hay destino" — llevaba toda la vida del proyecto sin
existir en el codigo. Y lo que no tiene nombre no existe para el software: no se
puede contar, no se puede mostrar, no se puede echar de menos.

Este modulo no resuelve B1. Nadie puede: si en el Peru no hay un servicio de
adultos que atienda una enfermedad rara concreta, ningun software lo va a
inventar. Lo que si hace es volver el vacio VISIBLE Y CONTABLE.

    "De 31 pacientes transferidos el ano pasado, 12 salieron sin destino
     identificado."

Ese numero hoy no lo tiene nadie porque nadie lo cuenta. Producirlo por primera
vez es la contribucion honesta que el software puede hacer a B1, y es lo que
convierte una queja en un dato que se le puede llevar a quien decide.

Sin dependencias externas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MotivoSinDestino(Enum):
    """Por que un paciente sale sin destino. Cada motivo pide una accion distinta."""

    NO_EXISTE_SERVICIO_ADULTO = (
        "no existe servicio de adultos para esta patologia en el pais"
    )
    """El caso grave. No es un fallo administrativo: es una brecha de oferta."""

    EXISTE_PERO_NO_CONFIRMADO = "hay un servicio candidato pero nadie confirmo que reciba"
    NO_ACCESIBLE_GEOGRAFICAMENTE = "el servicio existe pero esta fuera del alcance del paciente"
    DIRECTORIO_INCOMPLETO = "el directorio no tiene entrada para este diagnostico"
    """El caso barato: falta llenar el directorio. Se resuelve con trabajo."""

    PENDIENTE_DECISION_CLINICA = "el medico aun no define el destino"

    @property
    def es_brecha_de_oferta(self) -> bool:
        """True si el problema es del sistema de salud, no del directorio.

        La distincion importa: `DIRECTORIO_INCOMPLETO` se arregla llenando una
        tabla. `NO_EXISTE_SERVICIO_ADULTO` se arregla con politica publica, y
        contarlo es exactamente para lo que sirve este modulo.
        """
        return self in {
            MotivoSinDestino.NO_EXISTE_SERVICIO_ADULTO,
            MotivoSinDestino.NO_ACCESIBLE_GEOGRAFICAMENTE,
        }


@dataclass(frozen=True, slots=True)
class Destino:
    """Un servicio de adultos que puede recibir a un paciente."""

    codigo_renaes: str
    """Codigo del establecimiento en el registro nacional. Es la clave real:
    los nombres se escriben de diez formas distintas, el codigo no."""

    nombre: str
    especialidad: str
    cie10_que_atiende: tuple[str, ...] = ()
    """Prefijos CIE-10. 'E84' cubre E84.0, E84.1, etc."""

    departamento: str = ""
    contacto: str = ""

    confirmado_por: str | None = None
    """Quien verifico que este servicio efectivamente recibe a estos pacientes.

    Sin confirmacion es una hipotesis, no un destino. Un directorio lleno de
    entradas sin confirmar es peor que uno vacio: da falsa seguridad.
    """

    @property
    def esta_confirmado(self) -> bool:
        return bool(self.confirmado_por)

    def atiende(self, cie10: str) -> bool:
        return any(cie10.upper().startswith(p.upper()) for p in self.cie10_que_atiende)


@dataclass(frozen=True, slots=True)
class SinDestinoIdentificado:
    """No hay a donde derivar. Es un RESULTADO valido del sistema, no un error.

    Se modela como un tipo propio y no como `Destino | None` a proposito: un
    `None` no puede llevar motivo, y el motivo es justamente lo que convierte
    "falta un dato" en "hay una brecha de oferta que alguien tiene que resolver".
    """

    motivo: MotivoSinDestino
    cie10: str
    detalle: str = ""

    @property
    def requiere_escalamiento(self) -> bool:
        """True si esto no se arregla llenando el directorio."""
        return self.motivo.es_brecha_de_oferta

    def __str__(self) -> str:
        return f"Sin destino ({self.cie10}): {self.motivo.value}"


ResultadoDestino = Destino | SinDestinoIdentificado


@dataclass(frozen=True, slots=True)
class DirectorioDestinos:
    """Mapa CIE-10 → servicio de adultos.

    Hoy va a estar casi vacio, y eso esta bien: el directorio SE CONSTRUYE con
    el mentor, entrada por entrada. Lo importante es que exista la estructura
    para poder decir cuantas veces se consulto y no habia nada.

    TODO: poblar desde `config/destinos.csv` con el mentor del INSN.
    """

    destinos: tuple[Destino, ...] = ()

    def buscar(self, cie10: str, departamento: str = "") -> ResultadoDestino:
        """El destino para un diagnostico. NUNCA adivina.

        Si no hay entrada, devuelve `SinDestinoIdentificado` con el motivo — no
        el destino "mas parecido". Mandar a un paciente al servicio equivocado
        es peor que no mandarlo: pierde la cita, pierde el viaje, y pierde la
        confianza en que el sistema funciona.
        """
        candidatos = [d for d in self.destinos if d.atiende(cie10)]

        if not candidatos:
            return SinDestinoIdentificado(
                motivo=MotivoSinDestino.DIRECTORIO_INCOMPLETO,
                cie10=cie10,
                detalle="el directorio no tiene entrada para este codigo",
            )

        confirmados = [d for d in candidatos if d.esta_confirmado]
        if not confirmados:
            return SinDestinoIdentificado(
                motivo=MotivoSinDestino.EXISTE_PERO_NO_CONFIRMADO,
                cie10=cie10,
                detalle=f"{len(candidatos)} candidato(s), ninguno confirmado",
            )

        if departamento:
            mismos = [d for d in confirmados if d.departamento == departamento]
            if mismos:
                return mismos[0]

        return confirmados[0]


@dataclass(frozen=True, slots=True)
class CoberturaDirectorio:
    """El indicador de B1. Es lo que hoy no sabe nadie.

    No mide que tan bueno es nuestro software: mide un hueco del sistema de
    salud peruano que nadie habia cuantificado. Por eso vale como entregable
    aunque el directorio este vacio — de hecho, cuanto mas vacio, mas grande el
    hallazgo.
    """

    total_evaluados: int
    con_destino: int
    sin_destino_por_motivo: dict[MotivoSinDestino, int]

    @property
    def sin_destino(self) -> int:
        return self.total_evaluados - self.con_destino

    @property
    def tasa_sin_destino(self) -> float:
        return self.sin_destino / self.total_evaluados if self.total_evaluados else 0.0

    @property
    def brechas_de_oferta(self) -> int:
        """Los que no se arreglan llenando el directorio. El numero del pitch."""
        return sum(
            n for m, n in self.sin_destino_por_motivo.items() if m.es_brecha_de_oferta
        )

    def __str__(self) -> str:
        return (
            f"{self.sin_destino} de {self.total_evaluados} sin destino identificado "
            f"({self.tasa_sin_destino:.0%}) · {self.brechas_de_oferta} son brecha de oferta"
        )


def medir_cobertura(
    directorio: DirectorioDestinos, diagnosticos: tuple[str, ...]
) -> CoberturaDirectorio:
    con = 0
    por_motivo: dict[MotivoSinDestino, int] = {}
    for cie10 in diagnosticos:
        r = directorio.buscar(cie10)
        if isinstance(r, Destino):
            con += 1
        else:
            por_motivo[r.motivo] = por_motivo.get(r.motivo, 0) + 1
    return CoberturaDirectorio(len(diagnosticos), con, por_motivo)
