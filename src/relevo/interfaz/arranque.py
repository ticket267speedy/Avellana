"""Composicion de dependencias. El unico sitio donde se nombran adaptadores.

POR QUE EXISTE ESTE ARCHIVO
La promesa del pitch es *"el nucleo no cambia; solo se cambia el adaptador
segun el sistema del hospital"*. Para que eso sea verdad y no retorica, tiene
que haber UN archivo donde cambiarlo. Este.

Cambiar el repositorio en memoria por SQLite, Ollama por otro lector, o
Streamlit por FastAPI se hace aqui y en ningun otro sitio. Todo lo demas recibe
puertos y no sabe que hay detras.

`tests/test_arquitectura.py` verifica que ningun otro archivo de `interfaz/`
importe `relevo.infraestructura`. Este esta exceptuado a proposito: conocer las
implementaciones concretas es literalmente su trabajo.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from relevo.aplicacion.acciones_receptor import AccionesReceptor
from relevo.aplicacion.avanzar_aprendizaje import AvanzarAprendizaje
from relevo.aplicacion.avanzar_ciclo import AvanzarCiclo
from relevo.aplicacion.conciliar_medicacion import ConciliarMedicacion
from relevo.aplicacion.despachar_avisos import DespacharAvisos
from relevo.aplicacion.digitalizar_documento import (
    CampoDigitalizado,
    ConfirmarDigitalizacion,
    DigitalizarDocumento,
)
from relevo.aplicacion.evaluar_corte_etario import EvaluarCorteEtario
from relevo.aplicacion.gestionar_acceso_apoderado import GestionarAccesoApoderado
from relevo.aplicacion.priorizar_cohorte import (
    PriorizarCohorte,
    ResultadoPriorizacion,
)
from relevo.aplicacion.registrar_reingreso import RegistrarReingreso
from relevo.aplicacion.revisar_corpus import RevisarCorpus, RevisarSubida
from relevo.dominio.entidades.ciclo_transicion import CicloTransicion
from relevo.dominio.entidades.destino import DirectorioDestinos
from relevo.dominio.entidades.leccion import Leccion
from relevo.dominio.entidades.progreso_aprendizaje import ProgresoAprendizaje
from relevo.dominio.excepciones import ErrorDominio
from relevo.dominio.objetos_valor.habilidad import Habilidad
from relevo.dominio.objetos_valor.telefono import Telefono
from relevo.dominio.servicios.calculadora_iut import CalculadoraIUT
from relevo.dominio.servicios.clasificador_cohorte import ClasificadorCohorte
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.servicios.maquina_ciclo import (
    EvaluacionPlazo,
    MaquinaCiclo,
    PoliticaPlazos,
)
from relevo.infraestructura.configuracion.cargador_destinos import (
    cargar_directorio,
    resumen_del_directorio,
)
from relevo.infraestructura.configuracion.cargador_lecciones import (
    cargar_lecciones,
)
from relevo.infraestructura.configuracion.cargador_yaml import (
    cargar_parametros_iut,
    cargar_politica_plazos,
)
from relevo.infraestructura.fuentes.cohorte_demo import construir_cohorte_demo
from relevo.infraestructura.notificacion.canal_archivo import (
    CanalCorreoArchivo,
    CanalWhatsAppEnlace,
)
from relevo.infraestructura.notificacion.plantillas_mensaje import (
    TipoMensajeFamilia,
    plantilla_de,
)
from relevo.infraestructura.persistencia.auditoria import RegistroAuditoria
from relevo.infraestructura.persistencia.mapeadores import (
    acceso_a_documento,
    acceso_desde_documento,
    ciclo_a_documento,
    ciclo_desde_documento,
    conciliacion_a_documento,
    conciliacion_desde_documento,
    paciente_a_documento,
    paciente_desde_documento,
    progreso_a_documento,
    progreso_desde_documento,
)
from relevo.infraestructura.persistencia.migraciones import (
    InformeMigracion,
    migrar,
)
from relevo.infraestructura.persistencia.repositorio_sqlite import (
    ESQUEMA_VERSION,
    BaseDatos,
    RepositorioCiclosSQLite,
    RepositorioDocumentos,
    RepositorioPacientesSQLite,
)
from relevo.infraestructura.configuracion.catalogo_establecimientos import (
    Establecimiento,
)
from relevo.infraestructura.configuracion.catalogo_establecimientos import (
    buscar as buscar_en_renipress,
)
from relevo.infraestructura.configuracion.catalogo_establecimientos import (
    existe_en_catalogo as existe_en_renipress,
)
from relevo.infraestructura.documentos.acta_digitalizacion import (
    generar_acta_pdf_bytes,
)
from relevo.infraestructura.corpus.repositorio_archivos import CorpusEnArchivos
from relevo.infraestructura.fuentes.cohorte_sintetica import CohorteSintetica
from relevo.infraestructura.llm.extraccion_por_reglas import (
    extraer_de_transcripcion,
)
from relevo.infraestructura.documentos.pdf_reportlab import (
    generar_pasaporte_pdf_bytes,
)
from relevo.infraestructura.llm.lector_reconectable import (
    EstadoLector,
    LectorReconectable,
)
from relevo.infraestructura.persistencia.repositorio_memoria import (
    RepositorioPacientesMemoria,
)


# La raiz del proyecto: `src/relevo/interfaz/arranque.py` -> cuatro niveles.
RAIZ_DATOS = Path(__file__).resolve().parents[3] / "data"

HOST_OLLAMA_POR_DEFECTO = "http://localhost:11434"

# Variable de entorno que redirige el lector a un Ollama que no es el de esta
# maquina.
#
# POR QUE EXISTE
# El modelo de vision (qwen3-vl:4b) necesita varios GB de RAM y no hay servidor
# gratuito donde alojarlo. En el despliegue de Streamlit Cloud, `localhost` es
# el contenedor de Streamlit, donde no corre Ollama: la pantalla cae en captura
# manual y nadie llega a ver el modelo trabajando.
#
# Con esta variable, la app desplegada puede apuntar al Ollama que ya corre en
# la maquina de alguien del equipo, expuesto por un tunel. El nucleo no se
# entera: sigue hablando con un puerto por HTTP como siempre.
#
# Ver `docs/DESPLIEGUE.md` para el procedimiento del tunel.
VARIABLE_HOST_OLLAMA = "RELEVO_OLLAMA_HOST"


def _host_ollama(explicito: str | None = None) -> str:
    """Donde buscar Ollama: lo que pidan, luego el entorno, luego localhost."""
    if explicito:
        return explicito.rstrip("/")
    del_entorno = os.environ.get(VARIABLE_HOST_OLLAMA, "").strip()
    return del_entorno.rstrip("/") if del_entorno else HOST_OLLAMA_POR_DEFECTO


def _adaptar_campos(texto: str) -> Sequence[CampoDigitalizado]:
    """Traduce la lectura por reglas al objeto de transporte de la aplicacion.

    Esta funcion es la costura entre el subdominio de digitalizacion y el de
    transicion. Mientras no se separen en contextos (ver A4 de la revision de
    arquitectura), vive aqui, que es donde ya se toleran las dependencias
    concretas.
    """
    lectura = extraer_de_transcripcion(texto)
    return [
        CampoDigitalizado(
            nombre=c.nombre,
            valor=c.valor,
            crudo=c.crudo,
            motivo=c.motivo,
            corregido_desde=(
                c.ajuste.valor_leido if c.fue_corregido and c.ajuste else None
            ),
        )
        for c in lectura.campos
    ]


def _generar_acta(
    documento_id: str,
    campos: list[dict[str, str]],
    revisor: str,
    momento: datetime,
) -> bytes:
    return generar_acta_pdf_bytes(
        documento_id=documento_id, campos=campos, revisor=revisor, momento=momento
    )


@dataclass(frozen=True, slots=True)
class MensajeParaFamilia:
    """El mensaje compuesto mas el veredicto del adaptador.

    Lleva el cuerpo Y el resultado juntos porque la pantalla necesita mostrar
    el texto aunque el enlace se haya rechazado: ver que se iba a enviar es
    parte de entender por que no se envio.
    """

    detalle_cuerpo: str
    despachado: bool
    detalle: str
    enlace_generado: str


@dataclass(frozen=True, slots=True)
class Contenedor:
    """Los casos de uso ya construidos, listos para que la pantalla los use."""

    digitalizar: DigitalizarDocumento
    confirmar: ConfirmarDigitalizacion
    revisar_corpus: RevisarCorpus
    revisar_subida: RevisarSubida
    corpus: CorpusEnArchivos
    """El adaptador concreto, para que la pantalla pinte la imagen sin releerla.

    Se expone junto al caso de uso y no en su lugar: todo lo que sea decidir
    pasa por `revisar_corpus`; esto es solo la ruta del JPEG.
    """
    politica_plazos: PoliticaPlazos
    lector: LectorReconectable
    """El lector, que redescubre a Ollama por su cuenta.

    No se guarda un booleano `lector_disponible` porque seria mentira en cuanto
    pasaran unos segundos: `construir()` corre una sola vez al arrancar el
    servidor, y el portatil que sirve el modelo puede encenderse o suspenderse
    en cualquier momento despues. Se pregunta cada vez con `estado_lector()`.
    """

    # ── Lo que llego con la fusion ───────────────────────────────────────────
    bd: BaseDatos | None
    """None cuando se arranca en memoria (tests). Con SQLite, el archivo."""

    repo_pacientes: RepositorioPacientesSQLite | None
    repo_ciclos: RepositorioCiclosSQLite | None
    repo_progreso: RepositorioDocumentos | None
    repo_conciliacion: RepositorioDocumentos | None
    repo_acceso: RepositorioDocumentos | None
    auditoria: RegistroAuditoria | None

    directorio_destinos: DirectorioDestinos
    lecciones: dict[Habilidad, Leccion]
    despachar_avisos: DespacharAvisos
    """El unico camino hacia un enlace de WhatsApp o un correo."""

    avanzar_ciclo: AvanzarCiclo
    acciones_receptor: AccionesReceptor
    registrar_reingreso: RegistrarReingreso
    evaluar_corte: EvaluarCorteEtario
    avanzar_aprendizaje: AvanzarAprendizaje
    conciliar: ConciliarMedicacion
    acceso_apoderado: GestionarAccesoApoderado

    @property
    def es_persistente(self) -> bool:
        return self.bd is not None

    def estado_lector(self, forzar: bool = False) -> EstadoLector:
        """Si hay modelo AHORA, y donde esta."""
        return self.lector.estado(forzar=forzar)

    def emitir_pasaporte(self, paciente: Paciente, hoy: date) -> bytes:
        """El Pasaporte de Salud 18+ en PDF, listo para imprimir y firmar."""
        return generar_pasaporte_pdf_bytes(paciente, hoy)

    def buscar_establecimiento(
        self, consulta: str, limite: int = 8
    ) -> tuple[Establecimiento, ...]:
        """Busca en el registro nacional RENIPRESS."""
        return buscar_en_renipress(consulta, limite=limite)

    def establecimiento_en_catalogo(self, nombre: str) -> bool:
        """False marca el registro como pendiente de conciliar, no lo rechaza."""
        return existe_en_renipress(nombre)

    def priorizar(self, cantidad: int, hoy: date) -> PriorizarCohorte:
        """Construye el caso de uso de priorizacion para un padron dado.

        Se construye bajo demanda y no en `construir()` porque depende del
        tamanio de padron que elige el usuario en la pantalla.
        """
        fuente = CohorteSintetica(cantidad=cantidad, hoy=hoy)
        return PriorizarCohorte(
            repositorio=RepositorioPacientesMemoria(fuente.leer_pacientes()),
            calculadora=CalculadoraIUT(cargar_parametros_iut()),
            clasificador=ClasificadorCohorte(),
        )

    def radar(self, hoy: date) -> ResultadoPriorizacion:
        """La cohorte PERSISTIDA, ordenada por IUT y con su desglose.

        Distinto de `priorizar`, que trabaja sobre un padron sintetico generado
        al vuelo para la consola tecnica. Este lee lo que hay en la base, que
        es lo que ve el radar del producto.

        Vive aqui y no en el router de la API porque construir una
        `CalculadoraIUT` desde una pantalla es hacer de capa de aplicacion sin
        serlo: la pantalla pasaria a saber COMO se prioriza en vez de QUE
        pedir. `tests/test_arquitectura.py` lo vigila.
        """
        return PriorizarCohorte(
            repositorio=RepositorioPacientesMemoria(list(self.pacientes())),
            calculadora=CalculadoraIUT(cargar_parametros_iut()),
            clasificador=ClasificadorCohorte(),
        ).ejecutar(hoy)

    # ── WhatsApp: una sola ruta ──────────────────────────────────────────────

    def motivos_de_mensaje(self) -> tuple[TipoMensajeFamilia, ...]:
        """Los motivos de comunicacion que el sistema sabe preparar."""
        return tuple(TipoMensajeFamilia)

    def etiqueta_de_motivo(self, tipo: TipoMensajeFamilia) -> str:
        return tipo.etiqueta

    def telefono_valido(self, crudo: str) -> Telefono | None:
        """Un `Telefono` o None. El prefijo lo pone el objeto de valor.

        Devolver None y no lanzar: que el numero del sistema este mal es el
        caso NORMAL, no el excepcional. La plantilla oficial de historia
        clinica del INSN no tiene campo de telefono, asi que el numero que hay
        lo anoto alguien cuando el paciente tenia tres anios.
        """
        try:
            return Telefono(numero=crudo)
        except ErrorDominio:
            return None

    def preparar_whatsapp_familia(
        self,
        tipo: TipoMensajeFamilia,
        referencia_paciente: str,
        telefono: Telefono | None,
    ) -> MensajeParaFamilia:
        """Compone el mensaje y pide el enlace al adaptador.

        La pantalla NO construye el enlace. Pide, y la aplicacion decide: si el
        mensaje declarara datos clinicos, el adaptador lo rechaza y la pantalla
        se queda sin boton que ofrecer.
        """
        plantilla = plantilla_de(tipo)
        cuerpo = plantilla.componer(referencia_paciente)
        resultado = self.despachar_avisos.preparar_para_familia(
            cuerpo=cuerpo,
            asunto=plantilla.asunto,
            telefono=telefono,
            referencia_paciente=referencia_paciente,
            contiene_datos_clinicos=plantilla.contiene_datos_clinicos,
        )
        return MensajeParaFamilia(
            detalle_cuerpo=cuerpo,
            despachado=resultado.despachado,
            detalle=resultado.detalle,
            enlace_generado=resultado.enlace_generado,
        )

    def resumen_directorio(self) -> str:
        """Una linea honesta sobre el estado del directorio de destinos.

        Se muestra al lado de la cifra de cobertura. Sin ella, un "100 % sin
        destino" se lee como un fallo del software en vez de como el hallazgo
        del sistema de salud que es.
        """
        return resumen_del_directorio(self.directorio_destinos)

    def evaluar_plazo(self, ciclo: CicloTransicion, hoy: date) -> EvaluacionPlazo:
        """Como va este ciclo de plazo. Misma razon que `radar`: la pantalla no
        instancia servicios de dominio."""
        return MaquinaCiclo(self.politica_plazos).evaluar(ciclo, hoy)

    # ── Lectura de lo persistido ─────────────────────────────────────────────

    def pacientes(self) -> tuple[Paciente, ...]:
        """La cohorte guardada. Vacia si se arranco sin persistencia."""
        if self.repo_pacientes is None:
            return ()
        return tuple(self.repo_pacientes.todos())

    def paciente(self, paciente_id: str) -> Paciente | None:
        if self.repo_pacientes is None:
            return None
        resultado = self.repo_pacientes.obtener(paciente_id)
        return resultado if isinstance(resultado, Paciente) else None

    def ciclos(self) -> tuple[CicloTransicion, ...]:
        if self.repo_ciclos is None:
            return ()
        return tuple(self.repo_ciclos.todos())

    def ciclo_de(self, paciente_id: str) -> CicloTransicion | None:
        if self.repo_ciclos is None:
            return None
        encontrados = self.repo_ciclos.de_paciente(paciente_id)
        return encontrados[0] if encontrados else None

    def progreso_de(self, paciente_id: str) -> ProgresoAprendizaje:
        """El recorrido de Entrenate. Uno vacio si el paciente no empezo.

        Devuelve un progreso en cero en vez de None: las siete habilidades
        existen siempre, y quien no empezo esta en `POR_INICIAR`, no en un
        estado indefinido.
        """
        if self.repo_progreso is not None:
            guardado = self.repo_progreso.obtener(paciente_id)
            if isinstance(guardado, ProgresoAprendizaje):
                return guardado
        return ProgresoAprendizaje(paciente_id=paciente_id)

    def guardar_ciclo(self, ciclo: CicloTransicion, actor: str = "sistema") -> None:
        """Persiste el ciclo Y deja constancia en la cadena de auditoria.

        Las dos cosas juntas y en un solo metodo a proposito: guardar sin
        auditar es exactamente lo que hacia que la cadena de hash estuviera
        construida y probada, y no la llamara nadie.
        """
        if self.repo_ciclos is None:
            return
        self.repo_ciclos.guardar(
            ciclo,
            indices={
                "paciente_id": ciclo.paciente_id,
                "estado": ciclo.estado.value,
                "fecha_estado": ciclo.fecha_estado_actual.isoformat(),
                "cerrado": ciclo.esta_cerrado,
            },
        )
        if self.auditoria is not None:
            self.auditoria.registrar(
                actor=actor,
                accion="avanzar_ciclo",
                entidad="ciclo",
                entidad_id=ciclo.paciente_id,
                campo="estado",
                valor_despues=ciclo.estado.value,
                contexto={"responsable": ciclo.responsable.value},
            )

    def guardar_progreso(
        self, progreso: ProgresoAprendizaje, actor: str = "paciente"
    ) -> None:
        if self.repo_progreso is None:
            return
        self.repo_progreso.guardar(
            progreso.paciente_id,
            progreso,
            columnas_extra={"logradas": progreso.total_logradas},
        )
        if self.auditoria is not None:
            self.auditoria.registrar(
                actor=actor,
                accion="avanzar_aprendizaje",
                entidad="progreso_aprendizaje",
                entidad_id=progreso.paciente_id,
                valor_despues=progreso.resumen(),
            )

    def verificar_auditoria(self) -> tuple[bool, int | None]:
        """(intacta, id de la primera fila rota). La respuesta a "¿quien vigila
        al vigilante?": si alguien edita el SQLite por fuera, esto lo delata."""
        if self.auditoria is None:
            return True, None
        return self.auditoria.verificar_cadena()

    # ── Demo ─────────────────────────────────────────────────────────────────

    def sembrar_demo(
        self,
        n_pacientes: int,
        semilla_aleatoria: int,
        hoy: date,
        ciclos_abiertos: int,
        reparto_estados: dict[str, int],
        vencidos_forzados: int,
    ) -> dict[str, int]:
        """Genera y persiste la cohorte de demo. Determinista.

        Misma `semilla_aleatoria` = misma cohorte, hasta el ultimo digito del
        IUT. Eso es lo que hace que el ensayo del pitch sea reproducible: si
        cada reinicio generara pacientes distintos, no se podria ensayar.

        `vencidos_forzados` crea ciclos con la fecha atrasada a proposito, para
        que `correr_noche` tenga siempre algo que avisar en la demo.

        Los parametros se aceptan y se respetan, pero la forma de la cohorte
        —el caso Hunter, el de contraste, el reparto por estados— vive en
        `config/semilla_demo.yaml`: es contenido de demo, no codigo.
        """
        if self.repo_pacientes is None or self.repo_ciclos is None:
            raise RuntimeError(
                "No se puede sembrar sin persistencia. Construir el contenedor "
                "con `persistente=True`."
            )

        pacientes, ciclos = construir_cohorte_demo(
            hoy,
            ajustes={
                "pacientes": n_pacientes,
                "semilla_aleatoria": semilla_aleatoria,
                "ciclos_abiertos": ciclos_abiertos,
                "reparto_estados_ciclo": reparto_estados or None,
                "ciclos_vencidos_forzados": vencidos_forzados,
            },
        )
        priorizador = PriorizarCohorte(
            repositorio=RepositorioPacientesMemoria(pacientes),
            calculadora=CalculadoraIUT(cargar_parametros_iut()),
            clasificador=ClasificadorCohorte(),
        )
        prioridades = {
            fila.paciente.id: fila for fila in priorizador.ejecutar(hoy).filas
        }

        for paciente in pacientes:
            fila = prioridades.get(paciente.id)
            indice = fila.indice if fila is not None else None
            self.repo_pacientes.guardar(
                paciente,
                indices={
                    "fecha_nacimiento": paciente.fecha_nacimiento.isoformat(),
                    "cohorte": paciente.cohorte(hoy).value,
                    # Sin estos indices el radar no puede ordenar por IUT, que
                    # es lo unico que el radar hace.
                    "iut": indice.valor if indice else None,
                    "estado_semaforo": indice.estado.value if indice else None,
                    "confianza": getattr(indice, "confianza", None),
                    "tiene_contacto": paciente.tiene_contacto_vigente(hoy),
                },
            )

        vencidos = 0
        for ciclo in ciclos:
            self.guardar_ciclo(ciclo, actor="semilla de demo")
            evaluacion = MaquinaCiclo(self.politica_plazos).evaluar(ciclo, hoy)
            if evaluacion.situacion.name == "VENCIDO":
                vencidos += 1

        return {
            "pacientes": len(pacientes),
            "ciclos": len(ciclos),
            "vencidos": vencidos,
        }


def construir(
    config: Path | None = None,
    host_ollama: str | None = None,
    persistente: bool = True,
    ruta_bd: Path | None = None,
) -> Contenedor:
    """Arma el sistema completo.

    `config` se acepta para poder apuntar a otra carpeta de politica clinica en
    pruebas; por defecto se usa la del proyecto.

    `host_ollama` redirige el lector a otra maquina. Si no se pasa, se lee de
    la variable de entorno `RELEVO_OLLAMA_HOST`, y en su defecto se usa el
    Ollama local. Ver `VARIABLE_HOST_OLLAMA`.

    `persistente` decide memoria o SQLite. POR DEFECTO SQLITE: si la demo no
    persiste, no es la demo de un sistema, es la demo de una pantalla. Se pone
    en False solo en pruebas, donde tocar el disco haria los tests lentos y
    dependientes entre si.
    """
    lector = LectorReconectable(host=_host_ollama(host_ollama))
    digitalizar = DigitalizarDocumento(lector=lector, extraer=_adaptar_campos)
    corpus = CorpusEnArchivos.descubrir(RAIZ_DATOS)
    politica = cargar_politica_plazos()
    maquina = MaquinaCiclo(politica)
    lecciones = cargar_lecciones()

    bd: BaseDatos | None = None
    repo_pacientes: RepositorioPacientesSQLite | None = None
    repo_ciclos: RepositorioCiclosSQLite | None = None
    repo_progreso: RepositorioDocumentos | None = None
    repo_conciliacion: RepositorioDocumentos | None = None
    repo_acceso: RepositorioDocumentos | None = None
    auditoria: RegistroAuditoria | None = None

    if persistente:
        bd = BaseDatos(ruta_bd or RAIZ_DATOS / "relevo.db")
        # La migracion corre al arrancar y es idempotente. Nada se borra: los
        # estados del modelo de seis se traducen a los de nueve.
        migrar(bd, ESQUEMA_VERSION)
        repo_pacientes = RepositorioPacientesSQLite(
            bd, paciente_a_documento, paciente_desde_documento
        )
        repo_ciclos = RepositorioCiclosSQLite(
            bd, ciclo_a_documento, ciclo_desde_documento
        )
        repo_progreso = RepositorioDocumentos(
            bd,
            tabla="progreso_aprendizaje",
            a_documento=progreso_a_documento,
            desde_documento=progreso_desde_documento,
            columna_clave="paciente_id",
        )
        repo_conciliacion = RepositorioDocumentos(
            bd,
            tabla="conciliacion",
            a_documento=conciliacion_a_documento,
            desde_documento=conciliacion_desde_documento,
        )
        repo_acceso = RepositorioDocumentos(
            bd,
            tabla="acceso_apoderado",
            a_documento=acceso_a_documento,
            desde_documento=acceso_desde_documento,
        )
        auditoria = RegistroAuditoria(bd)

    return Contenedor(
        digitalizar=digitalizar,
        confirmar=ConfirmarDigitalizacion(generar_pdf=_generar_acta),
        revisar_corpus=RevisarCorpus(corpus=corpus, digitalizar=digitalizar),
        revisar_subida=RevisarSubida(digitalizar=digitalizar),
        corpus=corpus,
        politica_plazos=politica,
        lector=lector,
        bd=bd,
        repo_pacientes=repo_pacientes,
        repo_ciclos=repo_ciclos,
        repo_progreso=repo_progreso,
        repo_conciliacion=repo_conciliacion,
        repo_acceso=repo_acceso,
        auditoria=auditoria,
        directorio_destinos=cargar_directorio(),
        lecciones=lecciones,
        despachar_avisos=DespacharAvisos(
            canal_equipo=CanalCorreoArchivo(),
            # El canal de familia se compone AQUI y en ningun otro sitio: es lo
            # que garantiza que todo WhatsApp pase por la guarda de privacidad.
            canal_familia=CanalWhatsAppEnlace(),
        ),
        avanzar_ciclo=AvanzarCiclo(maquina=maquina),
        acciones_receptor=AccionesReceptor.con_maquina(maquina),
        registrar_reingreso=RegistrarReingreso.con_maquina(maquina),
        evaluar_corte=EvaluarCorteEtario(),
        avanzar_aprendizaje=AvanzarAprendizaje(catalogo=lecciones),
        conciliar=ConciliarMedicacion(),
        acceso_apoderado=GestionarAccesoApoderado(),
    )


def informe_de_migracion(bd: BaseDatos) -> InformeMigracion:
    """Vuelve a correr la migracion para poder mostrar que hizo.

    Es idempotente, asi que llamarla despues de `construir` no cambia nada: solo
    informa. Existe porque una migracion silenciosa es indistinguible de una
    que no corrio.
    """
    return migrar(bd, ESQUEMA_VERSION)
