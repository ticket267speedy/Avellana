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

from relevo.aplicacion.digitalizar_documento import (
    CampoDigitalizado,
    ConfirmarDigitalizacion,
    DigitalizarDocumento,
)
from relevo.aplicacion.priorizar_cohorte import PriorizarCohorte
from relevo.aplicacion.revisar_corpus import RevisarCorpus, RevisarSubida
from relevo.dominio.servicios.calculadora_iut import CalculadoraIUT
from relevo.dominio.servicios.clasificador_cohorte import ClasificadorCohorte
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.servicios.maquina_ciclo import PoliticaPlazos
from relevo.infraestructura.configuracion.cargador_yaml import (
    cargar_parametros_iut,
    cargar_politica_plazos,
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


def construir(
    config: Path | None = None, host_ollama: str | None = None
) -> Contenedor:
    """Arma el sistema completo.

    `config` se acepta para poder apuntar a otra carpeta de politica clinica en
    pruebas; por defecto se usa la del proyecto.

    `host_ollama` redirige el lector a otra maquina. Si no se pasa, se lee de
    la variable de entorno `RELEVO_OLLAMA_HOST`, y en su defecto se usa el
    Ollama local. Ver `VARIABLE_HOST_OLLAMA`.
    """
    lector = LectorReconectable(host=_host_ollama(host_ollama))
    digitalizar = DigitalizarDocumento(lector=lector, extraer=_adaptar_campos)
    corpus = CorpusEnArchivos.descubrir(RAIZ_DATOS)

    return Contenedor(
        digitalizar=digitalizar,
        confirmar=ConfirmarDigitalizacion(generar_pdf=_generar_acta),
        revisar_corpus=RevisarCorpus(corpus=corpus, digitalizar=digitalizar),
        revisar_subida=RevisarSubida(digitalizar=digitalizar),
        corpus=corpus,
        politica_plazos=cargar_politica_plazos(),
        lector=lector,
    )
