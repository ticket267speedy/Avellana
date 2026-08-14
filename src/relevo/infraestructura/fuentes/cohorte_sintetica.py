"""Cohorte sintetica. Implementa `FuenteDatosClinicos`.

REGLA INVIOLABLE 1 DEL PROYECTO: nunca datos reales de pacientes. Todo lo que
sale de aqui es inventado por un generador con semilla fija, y `es_sintetica`
devuelve True para que todo documento que se produzca lleve la marca de agua
"DATOS SINTETICOS — DEMO".

Determinista a proposito: la misma semilla da la misma cohorte. Una demo que
cambia de numeros cada vez que se recarga no se puede ensayar, y en un pitch de
cinco minutos ensayar es todo.

Sin red, sin archivos, sin Faker: solo `random` de la libreria estandar. El
wifi del evento va a fallar.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from relevo.dominio.entidades.diagnostico import (
    CategoriaCCC,
    Cirugia,
    Contacto,
    Diagnostico,
    Dispositivo,
    HistoriaTextoLibre,
    Medicamento,
    ResultadoTRAQ,
    TipoContacto,
    TipoSeguro,
)
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.objetos_valor.codigo_cie10 import CodigoCIE10
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.dominio.puertos.fuente_datos import FuenteDatosClinicos, InformeCarga

# Catalogo minimo: codigo, descripcion, categoria CCC v2, si es raro.
# ~40 codigos representativos de las 10 categorias, como pide PLAN_TECNICO §6.1.
# La interfaz declara explicitamente que el listado completo es cargable: no
# fingimos una cobertura que no tenemos.
_CATALOGO: tuple[tuple[str, str, CategoriaCCC, bool], ...] = (
    ("G80.9", "Parálisis cerebral infantil", CategoriaCCC.NEUROMUSCULAR, False),
    ("G40.9", "Epilepsia no especificada", CategoriaCCC.NEUROMUSCULAR, False),
    ("G71.0", "Distrofia muscular de Duchenne", CategoriaCCC.NEUROMUSCULAR, True),
    ("G12.1", "Atrofia muscular espinal", CategoriaCCC.NEUROMUSCULAR, True),
    ("I27.0", "Hipertensión pulmonar primaria", CategoriaCCC.CARDIOVASCULAR, True),
    ("Q21.3", "Tetralogía de Fallot", CategoriaCCC.CARDIOVASCULAR, False),
    ("I42.0", "Miocardiopatía dilatada", CategoriaCCC.CARDIOVASCULAR, False),
    ("J45.9", "Asma persistente grave", CategoriaCCC.RESPIRATORIA, False),
    ("E84.0", "Fibrosis quística con manifestaciones pulmonares", CategoriaCCC.RESPIRATORIA, True),
    ("J84.9", "Enfermedad pulmonar intersticial", CategoriaCCC.RESPIRATORIA, True),
    ("N18.5", "Enfermedad renal crónica estadio 5", CategoriaCCC.RENAL, False),
    ("N04.9", "Síndrome nefrótico corticorresistente", CategoriaCCC.RENAL, False),
    ("Q61.3", "Riñón poliquístico", CategoriaCCC.RENAL, True),
    ("K90.0", "Enfermedad celíaca", CategoriaCCC.GASTROINTESTINAL, False),
    ("K50.0", "Enfermedad de Crohn", CategoriaCCC.GASTROINTESTINAL, False),
    ("K74.6", "Cirrosis hepática", CategoriaCCC.GASTROINTESTINAL, False),
    ("D57.0", "Anemia falciforme con crisis", CategoriaCCC.HEMATOLOGICA_INMUNOLOGICA, True),
    ("D66", "Hemofilia A", CategoriaCCC.HEMATOLOGICA_INMUNOLOGICA, True),
    ("D80.1", "Inmunodeficiencia común variable", CategoriaCCC.HEMATOLOGICA_INMUNOLOGICA, True),
    ("D61.0", "Anemia aplásica constitucional", CategoriaCCC.HEMATOLOGICA_INMUNOLOGICA, True),
    ("E10.9", "Diabetes mellitus tipo 1", CategoriaCCC.METABOLICA, False),
    ("E75.2", "Enfermedad de Gaucher", CategoriaCCC.METABOLICA, True),
    ("E74.0", "Enfermedad por almacenamiento de glucógeno", CategoriaCCC.METABOLICA, True),
    ("E70.0", "Fenilcetonuria clásica", CategoriaCCC.METABOLICA, True),
    ("Q90.9", "Síndrome de Down", CategoriaCCC.CONGENITA_GENETICA, False),
    ("Q87.4", "Síndrome de Marfan", CategoriaCCC.CONGENITA_GENETICA, True),
    ("Q05.9", "Espina bífida", CategoriaCCC.CONGENITA_GENETICA, False),
    ("Q79.6", "Síndrome de Ehlers-Danlos", CategoriaCCC.CONGENITA_GENETICA, True),
    ("C91.0", "Leucemia linfoblástica aguda en remisión", CategoriaCCC.MALIGNIDAD, False),
    ("C71.9", "Tumor cerebral", CategoriaCCC.MALIGNIDAD, False),
    ("C40.2", "Osteosarcoma de huesos largos", CategoriaCCC.MALIGNIDAD, True),
    ("P07.2", "Inmaturidad extrema", CategoriaCCC.NEONATAL, False),
    ("P27.1", "Displasia broncopulmonar", CategoriaCCC.NEONATAL, False),
    ("Z94.0", "Trasplante renal", CategoriaCCC.TRASPLANTE, False),
    ("Z94.4", "Trasplante hepático", CategoriaCCC.TRASPLANTE, False),
    ("Z93.0", "Traqueostomía permanente", CategoriaCCC.DEPENDENCIA_TECNOLOGICA, False),
    ("Z93.1", "Gastrostomía permanente", CategoriaCCC.DEPENDENCIA_TECNOLOGICA, False),
    ("Z99.2", "Dependencia de diálisis", CategoriaCCC.DEPENDENCIA_TECNOLOGICA, False),
)

# Procesos agudos que NO deben pesar en el indice. Estan aqui a proposito: son
# el ruido real de una historia clinica, y la prueba de que x2 no los cuenta.
_AGUDOS: tuple[tuple[str, str], ...] = (
    ("S52.5", "Fractura de radio distal consolidada"),
    ("J18.9", "Neumonía adquirida en la comunidad resuelta"),
    ("A09.9", "Gastroenteritis aguda resuelta"),
    ("L03.1", "Celulitis de miembro resuelta"),
)

_DISPOSITIVOS_POR_CATEGORIA: dict[CategoriaCCC, tuple[str, ...]] = {
    CategoriaCCC.RENAL: ("hemodialisis", "dialisis_peritoneal", "cateter_venoso_central"),
    CategoriaCCC.RESPIRATORIA: ("oxigeno_domiciliario", "ventilacion_no_invasiva", "traqueostomia"),
    CategoriaCCC.NEUROMUSCULAR: ("gastrostomia", "derivacion_ventriculoperitoneal", "sonda_vesical"),
    CategoriaCCC.CARDIOVASCULAR: ("marcapasos",),
    CategoriaCCC.METABOLICA: ("bomba_insulina",),
    CategoriaCCC.DEPENDENCIA_TECNOLOGICA: ("traqueostomia", "ventilacion_mecanica", "gastrostomia"),
}

_MEDICAMENTOS: tuple[tuple[str, str, str, str], ...] = (
    ("Prednisona", "5 mg", "VO", "cada 24 h"),
    ("Enalapril", "10 mg", "VO", "cada 12 h"),
    ("Levetiracetam", "500 mg", "VO", "cada 12 h"),
    ("Insulina glargina", "18 UI", "SC", "cada 24 h"),
    ("Ácido fólico", "5 mg", "VO", "cada 24 h"),
    ("Calcitriol", "0.25 mcg", "VO", "cada 24 h"),
    ("Tacrolimus", "2 mg", "VO", "cada 12 h"),
    ("Salbutamol", "2 puff", "INH", "cada 6 h"),
    ("Omeprazol", "20 mg", "VO", "cada 24 h"),
    ("Hidroxiurea", "500 mg", "VO", "cada 24 h"),
)

# Distribucion de procedencia. Fuera de Lima Metropolitana dispara x7, que es
# binario: el costo de viajar a Lima para una cita es una barrera de otro tipo,
# no de otro grado.
_PROCEDENCIAS_LIMA = ("Lima", "Lima Metropolitana", "Callao")
_PROCEDENCIAS_REGION = (
    "Huancavelica", "Loreto", "Puno", "Cusco", "Ayacucho", "Piura",
    "Junín", "Cajamarca", "Ucayali", "Áncash", "Amazonas", "Apurímac",
)

_NOMBRES = (
    "Ana", "Luis", "María", "José", "Carmen", "Miguel", "Rosa", "Carlos",
    "Elena", "Jorge", "Lucía", "Pedro", "Sofía", "Diego", "Valeria", "Andrés",
)
_APELLIDOS = (
    "Quispe", "Mamani", "Flores", "Huamán", "Rojas", "Vargas", "Chávez",
    "Ramos", "Torres", "Castillo", "Espinoza", "Sánchez",
)


class CohorteSintetica(FuenteDatosClinicos):
    """Genera una cohorte inventada con distribucion plausible.

    Plausible no es real. Los porcentajes de abajo son supuestos de diseno para
    que la demo muestre los cuatro cuadrantes del problema (urgente y completo,
    urgente y opaco, holgado, ya fuera de la ventana). NO son epidemiologia del
    INSN y no deben citarse como tal.
    TODO: confirmar con mentor — distribucion real de la cohorte 14-18.
    """

    def __init__(
        self,
        cantidad: int = 300,
        hoy: date | None = None,
        semilla: int = 20260814,
    ) -> None:
        self._cantidad = cantidad
        self._hoy = hoy or date(2026, 8, 14)
        self._semilla = semilla
        self._pacientes: list[Paciente] = []
        self._informe: InformeCarga | None = None

    # ── Puerto ───────────────────────────────────────────────────────────────

    @property
    def nombre(self) -> str:
        return f"Cohorte sintetica (semilla {self._semilla})"

    @property
    def es_sintetica(self) -> bool:
        return True

    def leer_pacientes(self) -> list[Paciente]:
        if not self._pacientes:
            self._pacientes = self._generar()
            self._informe = InformeCarga(
                leidos=self._cantidad,
                cargados=len(self._pacientes),
                descartados=(),
            )
        return list(self._pacientes)

    def leer_paciente(self, paciente_id: str) -> Paciente | None:
        for p in self.leer_pacientes():
            if p.id == paciente_id:
                return p
        return None

    def ultimo_informe(self) -> InformeCarga | None:
        return self._informe

    # ── Generacion ───────────────────────────────────────────────────────────

    def _generar(self) -> list[Paciente]:
        azar = random.Random(self._semilla)
        pacientes = [self._caso_ana(azar)]
        pacientes.append(self._caso_perimetro_cefalico(azar))
        for i in range(2, self._cantidad):
            pacientes.append(self._paciente(azar, i))
        return pacientes

    def _caso_ana(self, azar: random.Random) -> Paciente:
        """El caso del pitch, fijo y siempre primero.

        17 años, enfermedad renal crónica en hemodiálisis, EsSalud, procede de
        Huancavelica, sin TRAQ y con el teléfono de la madre sin verificar desde
        hace más de un año. Es el recorrido que se demuestra ante el jurado, de
        modo que no puede depender del azar.
        """
        return Paciente(
            id="SINT-0001",
            fecha_nacimiento=date(2009, 6, 14),
            sexo="F",
            procedencia="Huancavelica",
            tipo_seguro=TipoSeguro.ESSALUD,
            diagnosticos=[
                self._dx("N18.5", principal=True),
                self._dx("D61.0"),
                Diagnostico(
                    codigo=CodigoCIE10("E87.6"),
                    descripcion="Hipopotasemia",
                    categoria=CategoriaCCC.OTRA,
                ),
            ],
            medicamentos=[
                Medicamento("Calcitriol", "0.25 mcg", "VO", "cada 24 h", True),
                Medicamento("Ácido fólico", "5 mg", "VO", "cada 24 h", True),
                # Sin dosis verificada en la fuente: sale como hueco en el
                # Pasaporte. Un hueco visible obliga al médico a llenarlo.
                Medicamento("Eritropoyetina", None, "SC", None, False),
            ],
            dispositivos=[
                Dispositivo("hemodialisis", "Hemodiálisis trisemanal"),
                Dispositivo("cateter_venoso_central", "Catéter venoso central"),
            ],
            alergias=["Penicilina"],
            cirugias=[Cirugia("Colocación de catéter tunelizado", date(2023, 4, 12), "INSN SB")],
            contactos=[
                Contacto(
                    nombre="Rosa Quispe (Madre)",
                    tipo=TipoContacto.MADRE,
                    telefono=Telefono("987654321", verificado_en=date(2024, 3, 2)),
                )
            ],
            ultima_consulta=self._hoy - timedelta(days=180),
            traq=None,
            texto_libre=HistoriaTextoLibre(
                secciones={
                    "Anamnesis": (
                        "Paciente mujer de 17 años con ERC estadio 5 en hemodiálisis desde "
                        "los 13 años. Acude acompañada de su madre. Refiere "
                        "astenia y calambres ocasionales en miembros inferiores."
                    ),
                    "Examen físico": "Peso 42 kg, Talla 1.52 m, PA 128/84. Palidez +/+++.",
                    "Plan": "Continuar hemodiálisis trisemanal. Evaluar acceso vascular definitivo y coordinar referencia a nefrología de adultos.",
                }
            ),
        )

    def _caso_perimetro_cefalico(self, azar: random.Random) -> Paciente:
        """Caso de regresión de PLAN_TECNICO §8.3.

        Lleva 'PC' en el sentido de PERÍMETRO CEFÁLICO, en la sección de examen
        físico, junto a Peso y Talla — exactamente como aparece en el formulario
        del INSN. 'PC' es también la abreviatura habitual de parálisis cerebral,
        y confundirlas en un documento que un médico firma rápido es el tipo de
        error que este sistema no puede cometer.

        Ojo: este paciente NO tiene parálisis cerebral. Si algún día el
        extractor le pone G80 en los diagnósticos, el fallo está a la vista.
        """
        return Paciente(
            id="SINT-0002",
            fecha_nacimiento=date(2010, 2, 20),
            sexo="M",
            procedencia="Lima",
            tipo_seguro=TipoSeguro.SIS,
            diagnosticos=[self._dx("E10.9", principal=True)],
            medicamentos=[Medicamento("Insulina glargina", "18 UI", "SC", "cada 24 h", True)],
            dispositivos=[Dispositivo("bomba_insulina", "Bomba de infusión continua de insulina")],
            contactos=[
                Contacto(
                    nombre="Paciente",
                    tipo=TipoContacto.PACIENTE,
                    telefono=Telefono(
                        "912345678",
                        verificado_en=self._hoy - timedelta(days=45),
                        es_del_paciente=True,
                    ),
                )
            ],
            ultima_consulta=self._hoy - timedelta(days=95),
            traq=ResultadoTRAQ(puntaje=3.8, fecha=self._hoy - timedelta(days=95)),
            texto_libre=HistoriaTextoLibre(
                secciones={
                    "Anamnesis": "Varón de 16 años con diabetes mellitus tipo 1 desde los 9 años. Buen control metabólico.",
                    # PC aquí es perímetro cefálico, no parálisis cerebral.
                    "Examen físico": "Peso 58 kg, Talla 1.68 m, PC 55 cm. SOMA sin alteraciones.",
                    "Plan": "Continuar bomba de infusión de insulina. Reforzar educación en autocuidado.",
                }
            ),
        )

    def _paciente(self, azar: random.Random, indice: int) -> Paciente:
        edad = azar.choices(
            # La cohorte activa (14-17) es el grueso; hay algunos de 12-13 que
            # todavia no entran y algunos de 18-19 en seguimiento post-corte.
            population=[12, 13, 14, 15, 16, 17, 18, 19],
            weights=[4, 6, 16, 18, 20, 22, 10, 4],
        )[0]
        dias = azar.randint(0, 364)
        nacimiento = date(self._hoy.year - edad, 1, 1) + timedelta(days=dias)
        if nacimiento > self._hoy - timedelta(days=365 * edad):
            nacimiento -= timedelta(days=365)

        principal = azar.choice(_CATALOGO)
        diagnosticos = [self._dx(principal[0], principal=True)]

        # Comorbilidades: la mayoria tiene una o dos. Se sortean de categorias
        # distintas mas a menudo que de la misma, que es como se ve en la
        # practica.
        for _ in range(azar.choices([0, 1, 2, 3], weights=[35, 35, 22, 8])[0]):
            diagnosticos.append(self._dx(azar.choice(_CATALOGO)[0]))

        # Ruido agudo: un tercio arrastra algo resuelto en la historia. No debe
        # pesar en el indice, y hay un test que lo fija.
        if azar.random() < 0.33:
            codigo, descripcion = azar.choice(_AGUDOS)
            diagnosticos.append(
                Diagnostico(
                    codigo=CodigoCIE10(codigo),
                    descripcion=descripcion,
                    categoria=CategoriaCCC.OTRA,
                    activo=False,
                )
            )

        dispositivos: list[Dispositivo] = []
        candidatos = _DISPOSITIVOS_POR_CATEGORIA.get(principal[2], ())
        if candidatos and azar.random() < 0.45:
            dispositivos.append(Dispositivo(azar.choice(candidatos)))
            if azar.random() < 0.20:
                dispositivos.append(Dispositivo(azar.choice(candidatos)))

        medicamentos: list[Medicamento] = []
        for nombre, dosis, via, frecuencia in azar.sample(
            _MEDICAMENTOS, k=azar.choices([1, 2, 3, 4, 5, 6], weights=[18, 24, 22, 18, 12, 6])[0]
        ):
            # Una de cada cinco dosis no se pudo verificar contra la fuente.
            # Es el escenario realista, y el Pasaporte tiene que mostrarlo como
            # hueco en vez de rellenarlo.
            verificada = azar.random() > 0.20
            medicamentos.append(
                Medicamento(
                    nombre=nombre,
                    dosis=dosis if verificada else None,
                    via=via,
                    frecuencia=frecuencia if verificada else None,
                    verificada_en_fuente=verificada,
                )
            )

        # 55 % procede de fuera de Lima Metropolitana. TODO: confirmar con
        # mentor — el INSN es referencia nacional, pero no sabemos la mezcla.
        if azar.random() < 0.55:
            procedencia = azar.choice(_PROCEDENCIAS_REGION)
        else:
            procedencia = azar.choice(_PROCEDENCIAS_LIMA)
        # Uno de cada veinte no tiene procedencia registrada: x7 se imputa.
        if azar.random() < 0.05:
            procedencia = ""

        contactos: list[Contacto] = []
        if azar.random() < 0.85:
            # La plantilla oficial del INSN no tiene campo de telefono: el
            # numero que hay se anoto informalmente y puede llevar anios sin
            # verificar. La mitad de las verificaciones estan caducadas.
            antiguedad = azar.choice([30, 90, 200, 400, 700, 1100])
            propio = edad >= 16 and azar.random() < 0.35
            contactos.append(
                Contacto(
                    nombre=(
                        "Paciente"
                        if propio
                        else f"{azar.choice(_NOMBRES)} {azar.choice(_APELLIDOS)}"
                    ),
                    tipo=TipoContacto.PACIENTE if propio else azar.choice(
                        (TipoContacto.MADRE, TipoContacto.PADRE, TipoContacto.CUIDADOR)
                    ),
                    telefono=Telefono(
                        f"9{azar.randint(10_000_000, 99_999_999)}",
                        verificado_en=self._hoy - timedelta(days=antiguedad),
                        es_del_paciente=propio,
                    ),
                )
            )

        ultima = (
            None
            if azar.random() < 0.12  # sin registro de consulta previa: x6 se imputa
            else self._hoy - timedelta(days=azar.choices(
                [20, 60, 120, 200, 300, 420, 600],
                weights=[18, 22, 20, 15, 12, 8, 5],
            )[0])
        )

        traq = (
            None
            if azar.random() < 0.60  # el TRAQ casi nunca se ha aplicado: x5 se imputa
            else ResultadoTRAQ(
                puntaje=round(azar.uniform(1.5, 4.8), 1),
                fecha=self._hoy - timedelta(days=azar.randint(10, 300)),
            )
        )

        return Paciente(
            id=f"SINT-{indice + 1:04d}",
            fecha_nacimiento=nacimiento,
            sexo=azar.choice(("F", "M")),
            procedencia=procedencia,
            tipo_seguro=azar.choices(
                [TipoSeguro.SIS, TipoSeguro.ESSALUD, TipoSeguro.PRIVADO, TipoSeguro.NINGUNO],
                weights=[62, 26, 5, 7],
            )[0],
            diagnosticos=diagnosticos,
            medicamentos=medicamentos,
            dispositivos=dispositivos,
            alergias=["Penicilina"] if azar.random() < 0.12 else [],
            cirugias=[],
            contactos=contactos,
            ultima_consulta=ultima,
            traq=traq,
            texto_libre=HistoriaTextoLibre(
                secciones={
                    "Anamnesis": f"Paciente de {edad} años con diagnóstico de {principal[1].lower()}.",
                    "Examen físico": "Peso y talla en percentiles esperados. Examen físico general sin alteraciones agudas.",
                }
            ),
        )

    @staticmethod
    def _dx(codigo: str, principal: bool = False) -> Diagnostico:
        for cod, descripcion, categoria, raro in _CATALOGO:
            if cod == codigo:
                return Diagnostico(
                    codigo=CodigoCIE10(cod),
                    descripcion=descripcion,
                    categoria=categoria,
                    es_principal=principal,
                    es_raro=raro,
                )
        raise KeyError(f"'{codigo}' no esta en el catalogo sintetico")
