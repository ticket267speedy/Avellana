"""Caso de uso: el acceso del apoderado, y su caducidad automatica.

La regla vive en el dominio (`entidades/acceso_apoderado.py`). Este caso de uso
la orquesta y produce lo que la interfaz necesita: si puede ver algo, con que
base legal, y que aviso mostrarle.

La vista del apoderado NO es una vista nueva: es la del paciente con permisos
recortados y el aviso de caducidad. Por eso este caso de uso devuelve permisos
en vez de contenido — el contenido lo sirven los mismos casos de uso del
paciente, filtrados por esto.

Importa solo `dominio`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from relevo.dominio.entidades.acceso_apoderado import (
    AccesoApoderado,
    AccesoDenegado,
    BaseLegalAcceso,
    ConsentimientoExplicito,
)


@dataclass(frozen=True, slots=True)
class PermisosApoderado:
    """Que puede ver este apoderado hoy, y por que.

    Cada permiso es un booleano explicito en vez de una lista de cadenas: una
    lista invita a comprobarla con `in`, y un error de escritura en esa cadena
    seria un permiso concedido por accidente.
    """

    puede_ver_estado_del_ciclo: bool
    puede_ver_pasaporte: bool
    puede_ver_aprendizaje: bool
    base_legal: BaseLegalAcceso
    aviso: str | None
    dias_para_el_corte: int

    @property
    def tiene_algun_acceso(self) -> bool:
        return self.puede_ver_estado_del_ciclo

    @property
    def norma(self) -> str:
        """La norma que sostiene —o niega— el acceso. Se muestra en pantalla.

        Sin la norma citada, "no puede usted ver esto" es una decision
        arbitraria del software.
        """
        return self.base_legal.norma


@dataclass(frozen=True, slots=True)
class GestionarAccesoApoderado:
    """Consulta, otorga y revoca. Nunca decide por el paciente."""

    def permisos(self, acceso: AccesoApoderado, hoy: date) -> PermisosApoderado:
        """Que puede ver hoy. Se recalcula siempre, nunca se guarda."""
        base = acceso.base_legal(hoy)
        hay_acceso = base.permite_acceso

        # El Pasaporte completo solo con patria potestad, o con consentimiento
        # que lo diga expresamente. El consentimiento es especifico, no una
        # llave maestra: por defecto autoriza el estado del tramite, que es lo
        # minimo util para que una madre sepa si su hijo ya tiene cita.
        alcance = acceso.consentimiento.alcance if acceso.consentimiento else ""
        pasaporte_autorizado = (
            base is BaseLegalAcceso.PATRIA_POTESTAD
            or "pasaporte" in alcance.lower()
        )

        return PermisosApoderado(
            puede_ver_estado_del_ciclo=hay_acceso,
            puede_ver_pasaporte=hay_acceso and pasaporte_autorizado,
            # El recorrido de aprendizaje es del adolescente y solo suyo. Ni
            # siquiera con patria potestad: que un padre vea que su hijo no
            # completo una leccion convierte una herramienta de autonomia en
            # una de control.
            puede_ver_aprendizaje=False,
            base_legal=base,
            aviso=acceso.aviso_de_caducidad(hoy),
            dias_para_el_corte=acceso.dias_restantes(hoy),
        )

    def exigir(self, acceso: AccesoApoderado, hoy: date) -> None:
        """Puerta para la capa de interfaz. Lanza `AccesoDenegado`."""
        acceso.exigir_acceso(hoy)

    def otorgar(
        self,
        acceso: AccesoApoderado,
        nombre_del_paciente: str,
        hoy: date,
        alcance: str = "estado del ciclo de transicion",
        medio: str = "",
    ) -> PermisosApoderado:
        """El paciente autoriza. Solo el puede, y queda fechado."""
        acceso.otorgar(
            ConsentimientoExplicito(
                otorgado_por_paciente=nombre_del_paciente,
                fecha=hoy,
                alcance=alcance,
                medio=medio,
            )
        )
        return self.permisos(acceso, hoy)

    def revocar(self, acceso: AccesoApoderado, hoy: date) -> PermisosApoderado:
        """El paciente retira el permiso. El registro anterior no se borra."""
        acceso.revocar(hoy)
        return self.permisos(acceso, hoy)


__all__ = [
    "AccesoDenegado",
    "GestionarAccesoApoderado",
    "PermisosApoderado",
]
