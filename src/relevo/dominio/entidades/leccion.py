"""Una leccion de Entrenate: la unidad del recorrido educativo.

NO SE LLAMAN "MODULOS". En software esa palabra significa otra cosa y ya causo
confusion en el equipo. Se llaman lecciones, en el codigo y en la pantalla.

Cada leccion tiene la misma estructura de cinco pasos:

    aprender -> practicar -> desafio -> tarea de la vida real -> retroalimentacion

La cuarta es la que hace que esto no sea un folleto. "Tarea de la vida real"
significa que el adolescente tiene que hacer algo fuera de la pantalla —pedir
una cita por telefono, leer su propia caja de medicamentos, guardar un
documento— y volver a contar como le fue. Sin ese paso, medir aprendizaje seria
medir lectura.

Sin dependencias externas: solo libreria estandar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from relevo.dominio.objetos_valor.habilidad import EstadoContenido, Habilidad


@dataclass(frozen=True, slots=True)
class Fuente:
    """De donde sale una afirmacion de la leccion, visible para el usuario.

    Se muestra AL LADO del texto, no en un pie de pagina que nadie abre. Una
    leccion que le dice a un adolescente que su madre ya no puede pedir sus
    resultados tiene que poder decirle tambien en que norma esta escrito, o es
    indistinguible de un rumor.
    """

    afirmacion: str
    norma: str
    detalle: str = ""

    def __str__(self) -> str:
        return f"{self.afirmacion} — {self.norma}"


@dataclass(frozen=True, slots=True)
class PasoLeccion:
    """Uno de los cinco pasos. `contenido` vacio = esqueleto sin escribir."""

    titulo: str
    contenido: str = ""

    @property
    def esta_escrito(self) -> bool:
        return bool(self.contenido.strip())


@dataclass(frozen=True, slots=True)
class Leccion:
    """Una leccion del recorrido, completa o en esqueleto.

    `estado_contenido` no es metadato administrativo: decide si la interfaz
    pinta el sello "Contenido pendiente de validacion clinica del INSN". Una
    leccion en esqueleto se muestra igual —el adolescente ve que existe y de
    que va— pero nunca se presenta como material validado.
    """

    numero: int
    habilidad: Habilidad
    titulo: str
    objetivo: str
    """Que sabra hacer el adolescente al terminarla. En primera persona y
    verificable: "se pedir una cita por telefono", no "conoce el sistema"."""

    estado_contenido: EstadoContenido = EstadoContenido.ESQUELETO_PENDIENTE_VALIDACION
    aprender: PasoLeccion = field(default_factory=lambda: PasoLeccion("Aprender"))
    practicar: PasoLeccion = field(default_factory=lambda: PasoLeccion("Practicar"))
    desafio: PasoLeccion = field(default_factory=lambda: PasoLeccion("Desafio"))
    tarea_real: PasoLeccion = field(
        default_factory=lambda: PasoLeccion("Tarea de la vida real")
    )
    retroalimentacion: PasoLeccion = field(
        default_factory=lambda: PasoLeccion("Retroalimentacion")
    )
    fuentes: tuple[Fuente, ...] = ()

    def __post_init__(self) -> None:
        if self.numero != self.habilidad.numero:
            raise ValueError(
                f"La leccion {self.numero} dice cubrir la habilidad "
                f"{self.habilidad.name}, que es la numero {self.habilidad.numero}. "
                "Una leccion por habilidad, sin excepciones."
            )
        if self.estado_contenido is EstadoContenido.COMPLETO and not self.fuentes:
            raise ValueError(
                f"La leccion {self.numero} se declara COMPLETA sin una sola "
                "fuente citada. Cada afirmacion va con su fuente, visible para "
                "el usuario: sin eso no se puede defender delante de nadie."
            )

    @property
    def pasos(self) -> tuple[PasoLeccion, ...]:
        return (
            self.aprender,
            self.practicar,
            self.desafio,
            self.tarea_real,
            self.retroalimentacion,
        )

    @property
    def sello(self) -> str | None:
        """El aviso que la interfaz pinta encima. None si esta validada."""
        return self.estado_contenido.sello

    @property
    def esta_completa(self) -> bool:
        return self.estado_contenido is EstadoContenido.COMPLETO

    @property
    def pasos_escritos(self) -> int:
        return sum(1 for p in self.pasos if p.esta_escrito)

    def __str__(self) -> str:
        marca = "" if self.esta_completa else " [esqueleto]"
        return f"Leccion {self.numero} · {self.titulo}{marca}"
