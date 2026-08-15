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
from relevo.infraestructura.fuentes.cohorte_sintetica import CohorteSintetica
from relevo.infraestructura.llm.extraccion_por_reglas import (
    extraer_de_transcripcion,
)
from relevo.infraestructura.documentos.pdf_reportlab import (
    generar_pasaporte_pdf_bytes,
)
from relevo.infraestructura.llm.lector_ollama import elegir_lectores
from relevo.infraestructura.persistencia.repositorio_memoria import (
    RepositorioPacientesMemoria,
)


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
    politica_plazos: PoliticaPlazos
    lector_disponible: bool
    """False cuando no hay ningun modelo instalado.

    La interfaz lo usa para decirlo en pantalla en vez de fallar a mitad de una
    demo: sin lector, el flujo entra en captura manual y todo lo demas sigue
    funcionando igual.
    """

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


def construir(config: Path | None = None) -> Contenedor:
    """Arma el sistema completo.

    `config` se acepta para poder apuntar a otra carpeta de politica clinica en
    pruebas; por defecto se usa la del proyecto.
    """
    principal, _contraste = elegir_lectores()
    hay_lector = getattr(principal, "nombre", "") != "sin-modelo"

    return Contenedor(
        digitalizar=DigitalizarDocumento(
            lector=principal,  # type: ignore[arg-type]
            extraer=_adaptar_campos,
        ),
        confirmar=ConfirmarDigitalizacion(generar_pdf=_generar_acta),
        politica_plazos=cargar_politica_plazos(),
        lector_disponible=hay_lector,
    )
