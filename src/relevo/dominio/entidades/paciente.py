"""El paciente: la entidad raiz del dominio.

PLAN_TECNICO §5. Sin imports externos: solo libreria estandar.

Nota de identidad: `id` es un identificador interno del sistema, NUNCA el DNI
ni el numero de historia clinica. El sistema corre al lado del hospital y no
necesita el identificador nacional para nada; guardarlo solo agrega riesgo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from relevo.dominio.entidades.diagnostico import (
    ChecklistPreparacionINSN,
    Cirugia,
    Contacto,
    Diagnostico,
    Dispositivo,
    HistoriaTextoLibre,
    Medicamento,
    PerfilPsicosocial,
    ResultadoTRAQ,
    TipoContacto,
    TipoSeguro,
)
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.dominio.objetos_valor.ventana_transicion import (
    Cohorte,
    VentanaTransicion,
)


@dataclass
class Paciente:
    """Un paciente de la cohorte de transicion.

    Mutable a proposito, a diferencia de los objetos de valor: un paciente
    acumula diagnosticos, contactos y consultas a lo largo de los cuatro anios
    que dura la ventana. Lo que no cambia nunca es su `id` ni su fecha de
    nacimiento.
    """

    id: str
    fecha_nacimiento: date
    sexo: str = ""
    procedencia: str = ""
    tipo_seguro: TipoSeguro = TipoSeguro.NINGUNO

    diagnosticos: list[Diagnostico] = field(default_factory=list)
    medicamentos: list[Medicamento] = field(default_factory=list)
    dispositivos: list[Dispositivo] = field(default_factory=list)
    alergias: list[str] = field(default_factory=list)
    cirugias: list[Cirugia] = field(default_factory=list)
    contactos: list[Contacto] = field(default_factory=list)

    ultima_consulta: date | None = None
    traq: ResultadoTRAQ | None = None
    checklist_insn: ChecklistPreparacionINSN | None = None
    psicosocial: PerfilPsicosocial | None = None
    texto_libre: HistoriaTextoLibre = field(default_factory=HistoriaTextoLibre)

    # ── Ventana y cohorte ────────────────────────────────────────────────────

    def ventana(self, hoy: date) -> VentanaTransicion:
        """La ventana de transicion evaluada a una fecha dada.

        `hoy` se pasa siempre como parametro y nunca se lee del reloj del
        sistema: un dominio que consulta la hora no se puede probar.
        """
        return VentanaTransicion(fecha_nacimiento=self.fecha_nacimiento, hoy=hoy)

    def edad(self, hoy: date) -> int:
        return self.ventana(hoy).edad

    def meses_hasta_corte(self, hoy: date) -> int:
        """Meses hasta el cumpleanos 18. Negativo si ya paso."""
        return self.ventana(hoy).meses_restantes

    def cohorte(self, hoy: date) -> Cohorte:
        """ACTIVA si 14 <= edad < 18. SEGUIMIENTO si >= 18. PREVIA si < 14.

        El INSN no atiende mayores de 18: el corte es duro y en fecha exacta.
        """
        return self.ventana(hoy).cohorte

    # ── Lecturas que el motor de reglas necesita ─────────────────────────────

    @property
    def diagnostico_principal(self) -> Diagnostico | None:
        """El marcado como principal; si ninguno lo esta, el primero.

        El respaldo existe porque las historias reales no siempre marcan cual
        es el principal, y el Pasaporte necesita encabezarse con algo.
        """
        for dx in self.diagnosticos:
            if dx.es_principal:
                return dx
        return self.diagnosticos[0] if self.diagnosticos else None

    @property
    def diagnosticos_contables(self) -> tuple[Diagnostico, ...]:
        """Los cronicos y activos: los unicos que pesan en el indice.

        PLAN_TECNICO §6.2 define K como diagnosticos cronicos activos. Vive
        aqui y no en la calculadora para que el Pasaporte y la exportacion
        FHIR usen el mismo criterio y no cada uno el suyo.
        """
        return tuple(dx for dx in self.diagnosticos if dx.cuenta_para_el_indice)

    @property
    def tiene_enfermedad_rara(self) -> bool:
        """True si algun diagnostico figura en el listado RM 478-2026-MINSA.

        Lo marca el adaptador que carga el CSV, no el dominio.
        """
        return any(dx.es_raro for dx in self.diagnosticos)

    @property
    def medicamentos_por_completar(self) -> tuple[Medicamento, ...]:
        """Los que no tienen dosis verificada en la fuente.

        Se imprimen como hueco en el Pasaporte para que el medico los llene.
        Nunca se rellenan con una estimacion.
        """
        return tuple(m for m in self.medicamentos if m.requiere_completar_manualmente)

    def dias_desde_ultima_consulta(self, hoy: date) -> int | None:
        """None si no hay registro de consulta previa.

        None no es cero: es ausencia de dato, y el factor x6 la trata como tal
        (imputa y marca `dato_faltante`), no como un paciente al dia.
        """
        if self.ultima_consulta is None:
            return None
        return (hoy - self.ultima_consulta).days

    # ── Contacto ─────────────────────────────────────────────────────────────

    def contacto_preferente(self, hoy: date) -> Contacto | None:
        """A quien se le escribe. Prioridad: paciente vigente, luego cualquiera
        vigente, luego el primero que exista.

        El paciente propio va primero a partir de los 16 (Pasaporte v2) porque
        a los 18 el vinculo con el cuidador puede haberse roto y el paciente es
        quien tiene que poder ser contactado.
        """
        vigentes = [c for c in self.contactos if c.esta_vigente(hoy)]
        for c in vigentes:
            if c.es_del_paciente:
                return c
        if vigentes:
            return vigentes[0]
        return self.contactos[0] if self.contactos else None

    @property
    def telefono_propio(self) -> Telefono | None:
        """El movil del propio paciente, si se capturo alguno."""
        for c in self.contactos:
            if c.tipo is TipoContacto.PACIENTE and c.telefono is not None:
                return c.telefono
        return None

    def tiene_contacto_vigente(self, hoy: date) -> bool:
        return any(c.esta_vigente(hoy) for c in self.contactos)

    def __str__(self) -> str:
        dx = self.diagnostico_principal
        return f"{self.id} — {dx.descripcion if dx else 'sin diagnostico registrado'}"
