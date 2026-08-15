"""Un lector falso que se equivoca como se equivoca un lector de verdad.

PARA QUE SIRVE
Permite ejercitar y MEDIR el pipeline completo sin GPU, sin Ollama, sin red y
sin esperar minutos por documento. Toma la verdad del corpus y le inyecta los
errores tipicos de lectura optica, de forma determinista segun la semilla.

Con esto se puede:

  · Calibrar los umbrales de confianza campo por campo antes de tener el modelo.
  · Comprobar que la capa de validacion detecta lo que dice detectar.
  · Correr la demo si el dia del evento no arranca Ollama.
  · Tener un numero de `tasa de error no detectado` desde hoy.

NO SIRVE para estimar que tan bien lee un modelo real: eso solo se sabe con el
modelo. Sirve para verificar que, CUANDO el modelo se equivoque, el sistema se
de cuenta.

La tasa de error por defecto es deliberadamente alta (18%). Un pipeline que solo
se prueba con lecturas buenas no prueba nada: lo interesante es que la capa de
verificacion aguante cuando el lector es malo.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass, field

# Sustituciones que de verdad comete un lector optico, en ambos sentidos.
# Misma tabla que pondera la distancia de edicion en el verificador: si el
# simulador rompe por donde el verificador sabe reparar, la prueba seria
# tramposa — por eso tambien se inyectan errores que NO estan en la tabla.
CONFUSIONES = {
    "0": "OQD", "O": "0Q", "1": "Il7", "I": "1l", "l": "1I",
    "5": "S", "S": "5", "8": "B", "B": "8", "2": "Z", "Z": "2",
    "6": "G", "G": "6", "9": "gq", "U": "V", "V": "U",
    "rn": "m", "m": "rn", "cl": "d", "a": "o", "o": "a",
    "e": "c", "c": "e", "n": "h", "u": "v", "t": "f",
}


@dataclass(frozen=True, slots=True)
class LectorSimulado:
    """Devuelve la verdad con ruido. No mira la imagen."""

    verdad: Mapping[str, str]
    semilla: int = 0

    prob_error_caracter: float = 0.018
    """Probabilidad de alterar cada caracter. 1.8% da ~18% de campos con al
    menos un error en campos de 10 caracteres."""

    prob_campo_ilegible: float = 0.06
    """Probabilidad de que el lector directamente no pueda con el campo."""

    prob_campo_omitido: float = 0.03
    """El modelo no encuentra el campo en el documento."""

    nombre: str = "simulado"
    _cache: dict = field(default_factory=dict, compare=False)

    def _corromper(self, texto: str, rnd: random.Random) -> str:
        salida = []
        for c in texto:
            if rnd.random() < self.prob_error_caracter and c in CONFUSIONES:
                salida.append(rnd.choice(CONFUSIONES[c]))
            elif rnd.random() < self.prob_error_caracter / 3:
                salida.append("")  # caracter perdido
            else:
                salida.append(c)
        return "".join(salida)

    def leer(self, imagen: bytes, instruccion: str) -> str:  # noqa: ARG002
        import json

        rnd = random.Random(self.semilla)
        salida: dict[str, str | None] = {}
        for campo, valor in self.verdad.items():
            u = rnd.random()
            if u < self.prob_campo_omitido:
                continue  # ni siquiera aparece en el JSON
            if u < self.prob_campo_omitido + self.prob_campo_ilegible:
                salida[campo] = None
                continue
            salida[campo] = self._corromper(valor, rnd)
        return json.dumps(salida, ensure_ascii=False)


def par_de_lectores_simulados(
    verdad: Mapping[str, str], semilla: int
) -> tuple[LectorSimulado, LectorSimulado]:
    """Dos lectores con semillas distintas: se equivocan en sitios distintos.

    Es lo que hace util la doble lectura — dos modelos independientes rara vez
    cometen el MISMO error en el MISMO campo, asi que el desacuerdo senala
    justamente donde hay problema.
    """
    return (
        LectorSimulado(verdad=verdad, semilla=semilla, nombre="simulado-A"),
        LectorSimulado(
            verdad=verdad,
            semilla=semilla + 100_000,
            prob_error_caracter=0.022,
            nombre="simulado-B",
        ),
    )
