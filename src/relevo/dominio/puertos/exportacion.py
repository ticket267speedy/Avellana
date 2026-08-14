"""Puerto de interoperabilidad.

PLAN_TECNICO §11. Bundle FHIR de tipo `document` conforme a los perfiles CorePE
del MINSA (FHIR R4, basado en International Patient Summary).

`validar_fhir.py` valida contra el validador publico de HAPI FHIR.
SI NO VALIDA, NO ES ENTREGABLE. Es uno de los diferenciadores del proyecto y
tiene que funcionar de verdad, no de mentira.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.entidades.pasaporte import Pasaporte


@dataclass(frozen=True, slots=True)
class ResultadoValidacion:
    """Lo que dijo el validador.

    Los avisos no impiden entregar; los errores si. La distincion la hace el
    validador, no nosotros.
    """

    valido: bool
    errores: tuple[str, ...] = field(default_factory=tuple)
    avisos: tuple[str, ...] = field(default_factory=tuple)
    validador: str = ""
    """Quien valido: 'HAPI FHIR publico', 'validacion local de estructura'.

    Importa distinguirlos: pasar una comprobacion local nuestra no es lo mismo
    que pasar HAPI, y decir lo contrario en el pitch seria mentir.
    """

    def __str__(self) -> str:
        if self.valido:
            return f"valido ({self.validador}), {len(self.avisos)} avisos"
        return f"INVALIDO ({self.validador}), {len(self.errores)} errores"


class ExportadorInteroperable(ABC):
    """Convierte el estado del dominio en un artefacto de intercambio.

    El pasaporte debe estar firmado antes de exportarse: un Bundle FHIR que
    sale del sistema es una salida clinica como cualquier otra.
    """

    @abstractmethod
    def exportar_paciente(self, paciente: Paciente, pasaporte: Pasaporte) -> str:
        """Devuelve el Bundle serializado en JSON."""

    @abstractmethod
    def validar(self, documento: str) -> ResultadoValidacion:
        """Comprueba el documento.

        La implementacion contra HAPI requiere red. Debe existir un modo local
        de respaldo que valide estructura, y su `ResultadoValidacion.validador`
        tiene que decir claramente que fue local.
        """

    @property
    @abstractmethod
    def perfil(self) -> str:
        """'CorePE R4 / IPS'. Se muestra junto al documento exportado."""
