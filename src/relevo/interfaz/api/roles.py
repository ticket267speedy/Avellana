"""Los cinco roles: cuatro de negocio y uno tecnico.

Vive en `interfaz/` y no en `dominio/` a proposito: un rol es una forma de
acceder al sistema, no una regla clinica de la transicion. El dominio no sabe
que existen usuarios.

Sin dependencias externas mas alla de la libreria estandar.
"""

from __future__ import annotations

from enum import Enum


class Rol(Enum):
    """Quien esta usando el sistema."""

    PACIENTE = "paciente"

    APODERADO = "apoderado"
    """PACIENTE con permisos recortados y la caducidad de los 18 anios.

    No es una vista aparte ni una logica aparte: es la vista del paciente
    filtrada por `GestionarAccesoApoderado`. Duplicarla habria producido dos
    sitios donde arreglar cada cosa, y uno de los dos se habria quedado atras.
    """

    PROFESIONAL_INSN = "profesional_insn"
    """Ve SU cohorte pediatrica completa."""

    PROFESIONAL_RECEPTOR = "profesional_receptor"
    """Ve UNICAMENTE las referencias dirigidas a su establecimiento.

    ═══════════════════════════════════════════════════════════════════════════
    POR QUE NO ES EL MISMO ROL QUE PROFESIONAL_INSN
    ═══════════════════════════════════════════════════════════════════════════

    Estan en instituciones distintas. Unificarlos le daria al receptor
    visibilidad sobre toda la cohorte pediatrica del INSN, que es exactamente
    el problema de proteccion de datos que decimos evitar: un medico del
    Hospital Dos de Mayo no tiene ninguna base legal para ver el expediente de
    un paciente que nunca le fue referido.

    Y el filtro es por ESTABLECIMIENTO, no por rol a secas: dos receptores de
    hospitales distintos tampoco se ven entre si.
    """

    ADMINISTRADOR = "administrador"
    """Rol tecnico. NO tiene lectura clinica en la interfaz.

    Puede sembrar, reiniciar, ver registros, ver metricas agregadas y verificar
    la cadena de auditoria. No puede abrir un Pasaporte ni una historia.

    ═══════════════════════════════════════════════════════════════════════════
    ¿QUIEN VIGILA AL VIGILANTE?
    ═══════════════════════════════════════════════════════════════════════════

    En la practica, quien administre el servidor tendra acceso al archivo
    SQLite. Eso es inevitable y fingir lo contrario seria deshonesto: ninguna
    comprobacion de rol dentro de la aplicacion impide leer un archivo del
    disco.

    Por eso existe la cadena de hash de auditoria. No impide que el
    administrador mire; hace que no pueda TOCAR sin que se note. Si edita una
    fila por SQL, `verificar_cadena()` devuelve el id de la primera fila rota.

    La respuesta honesta a la pregunta no es "nadie puede"; es "quien lo haga
    deja rastro".
    """

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]

    @property
    def es_personal_de_salud(self) -> bool:
        """True para los dos roles profesionales.

        Es la condicion que activa la regla de cero captura clinica: al
        personal de salud NO se le pide teclear ningun dato clinico, porque el
        INSN ya tiene SisGalenPlus y nadie va a escribir lo mismo dos veces.
        """
        return self in (Rol.PROFESIONAL_INSN, Rol.PROFESIONAL_RECEPTOR)

    @property
    def puede_leer_datos_clinicos(self) -> bool:
        """El ADMINISTRADOR queda fuera a proposito. Ver su docstring."""
        return self is not Rol.ADMINISTRADOR

    @property
    def ruta_inicial(self) -> str:
        """A donde va este rol al entrar."""
        return {
            Rol.PACIENTE: "#/paciente",
            Rol.APODERADO: "#/paciente",
            Rol.PROFESIONAL_INSN: "#/insn/radar",
            Rol.PROFESIONAL_RECEPTOR: "#/receptor/bandeja",
            Rol.ADMINISTRADOR: "#/insn/radar",
        }[self]


_ETIQUETAS: dict[Rol, str] = {
    Rol.PACIENTE: "Paciente",
    Rol.APODERADO: "Apoderado",
    Rol.PROFESIONAL_INSN: "Profesional del INSN",
    Rol.PROFESIONAL_RECEPTOR: "Profesional del hospital receptor",
    Rol.ADMINISTRADOR: "Administrador del sistema",
}
