"""Calculadora del Indice de Urgencia de Transicion.

PLAN_TECNICO §6.2:

    IUT = sigmoide(beta_0 + suma_i beta_i * x_i)

BLINDAJE DISCURSIVO Y PRINCIPIO ETICO (§4.9 / MAPEO_RUBRICA_INSN #7):
El IUT no prioriza pacientes; ordena la cola de trabajo del equipo de
transicion. No decide quien se atiende primero en un hospital: decide a quien
llama primero la trabajadora social o coordinadora de referencia. Es
transparente — dz/dx_i = beta_i, cada factor con su peso visible y e^beta_i
interpretable como razon de momios (odds ratio) —, es auditable, y cualquier
persona puede reordenar la cola a mano, quedando ese reordenamiento registrado
en la auditoria.

CRITERIO DE ACEPTACION DEL BLOQUE 3: cinco casos calculados a mano en papel
deben coincidir con el codigo. Ver `tests/dominio/test_calculadora_iut.py`.

Los parametros NO se leen aqui de ningun archivo: el dominio no toca el disco.
`ParametrosIUT` los recibe ya cargados; quien los lee de
`config/reglas_transicion.yaml` es un adaptador de infraestructura.

Y NO HAY VALOR POR DEFECTO, a proposito. `CalculadoraIUT()` no existe: hay que
decir con que politica clinica se construye. Un defecto silencioso produciria
numeros con aspecto legitimo calculados con pesos que ningun medico aprobo, y
en un hackathon eso termina en una demo mostrando prioridades clinicas
inventadas. Si nadie carga el YAML, esto falla ruidosamente — que es lo que
pide la regla del propio archivo: nadie inventa un peso.

Los valores provisionales del YAML viven ahora en `tests/dominio/conftest.py`,
que es lo que en realidad son: material de prueba.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from relevo.dominio.entidades.diagnostico import TipoSeguro
from relevo.dominio.entidades.paciente import Paciente
from relevo.dominio.excepciones import ConfiguracionIncompleta
from relevo.dominio.objetos_valor.indice_urgencia import (
    AporteFactor,
    EstadoSemaforo,
    IndiceUrgencia,
    sigmoide,
)

# Nombres de los ocho factores. Son las claves de `betas` y las etiquetas que
# ve el usuario en el desglose, asi que se declaran una sola vez.
X1_URGENCIA_TEMPORAL = "x1_urgencia_temporal"
X2_COMPLEJIDAD = "x2_complejidad"
X3_SEVERIDAD = "x3_severidad"
X4_DEPENDENCIA_TECNOLOGICA = "x4_dependencia_tecnologica"
X5_BRECHA_PREPARACION = "x5_brecha_preparacion"
X6_RIESGO_PERDIDA = "x6_riesgo_perdida"
X7_BARRERA_ACCESO = "x7_barrera_acceso"
X8_CONTINUIDAD_SEGURO = "x8_continuidad_seguro"

_EXPLICACIONES: Mapping[str, str] = {
    X1_URGENCIA_TEMPORAL: "Queda poco tiempo antes de cumplir 18 años",
    X2_COMPLEJIDAD: "Múltiples sistemas u órganos comprometidos",
    X3_SEVERIDAD: "Condición clínica de alta severidad",
    X4_DEPENDENCIA_TECNOLOGICA: "Dependencia de tecnología o dispositivos médicos",
    X5_BRECHA_PREPARACION: "Autonomía de autocuidado por reforzar (TRAQ)",
    X6_RIESGO_PERDIDA: "Tiempo prolongado sin consulta de control",
    X7_BARRERA_ACCESO: "Residencia fuera de Lima Metropolitana",
    X8_CONTINUIDAD_SEGURO: "Riesgo de pérdida de cobertura de seguro a los 18 años",
}


# El primer float por encima de 1.0. Ningun IUT puede alcanzarlo, ni siquiera
# cuando la sigmoide satura a 1.0 exacto por redondeo.
INALCANZABLE = math.nextafter(1.0, 2.0)


def _acotar(valor: float, minimo: float = 0.0, maximo: float = 1.0) -> float:
    """clamp. Todos los x_i van normalizados en [0, 1] sin excepcion."""
    return max(minimo, min(maximo, valor))


@dataclass(frozen=True, slots=True)
class ParametrosIUT:
    """Politica clinica del indice. Se carga; no se inventa.

    Cada valor de `provisionales()` esta copiado de `config/reglas_transicion.yaml`
    y marcado alli con su fuente o con su TODO. El YAML manda: si los dos se
    separan, el que esta mal es este archivo.
    """

    beta_0: float
    betas: Mapping[str, float]

    horizonte_meses: int
    """x1: 48 meses = 4 anios = la cohorte activa completa (arranca a los 14)."""

    categorias_techo: int
    """x2: cuantas categorias CCC v2 distintas se consideran el maximo.

    5 = las casillas de diagnostico secundario de la HC del INSN (formato
    RD N° 000109-2021-DG-INSN-SB): mas de cinco sistemas comprometidos no
    caben ni en el propio formulario de la institucion.
    TODO: confirmar con mentor — si el techo de sistemas debe ser menor que el
    de casillas de registro.
    """

    severidad_maxima_posible: float
    """x3: 3 = el peso maximo de la escala de severidad de
    `config/reglas_transicion.yaml` (1 cronica, 2 compleja, 3 amenaza vital).
    No es un numero elegido: es el tope de la propia escala."""

    peso_maximo_dispositivos: float
    traq_minimo: float
    traq_maximo: float
    traq_imputacion: float
    """x5: 0.5 cuando no hay TRAQ, Y se marca dato_faltante."""

    intervalo_control_dias: int
    """x6: 180 dias. El factor satura a los 360: un anio sin consulta es
    perdida de seguimiento, no un retraso."""

    lima_metropolitana: frozenset[str]
    severidad_por_categoria: Mapping[str, int]
    peso_dispositivos: Mapping[str, int]
    riesgo_seguro: Mapping[str, float]
    riesgo_seguro_verificado: Mapping[str, bool]
    umbral_rojo: float
    umbral_ambar: float

    imputacion_sin_consulta: float = 0.5
    """x6 sin fecha de ultima consulta. Se imputa igual que x5 y se marca
    dato_faltante: la ausencia de registro no es un paciente al dia."""

    imputacion_sin_procedencia: float = 0.5
    """x7 sin procedencia registrada. Ni dentro ni fuera de Lima: no se sabe."""

    confianza_minima: float = 0.70
    """Debajo de esta fraccion de dato real, el indice se declara poco fiable.

    PROVISIONAL. TODO: confirmar con mentor — a partir de que punto un puntaje
    deja de ser accionable.
    """

    def __post_init__(self) -> None:
        faltantes = [
            nombre
            for nombre in (
                X1_URGENCIA_TEMPORAL,
                X2_COMPLEJIDAD,
                X3_SEVERIDAD,
                X4_DEPENDENCIA_TECNOLOGICA,
                X5_BRECHA_PREPARACION,
                X6_RIESGO_PERDIDA,
                X7_BARRERA_ACCESO,
                X8_CONTINUIDAD_SEGURO,
            )
            if nombre not in self.betas
        ]
        if faltantes:
            raise ConfiguracionIncompleta(
                f"Faltan pesos beta para: {', '.join(faltantes)}. "
                "Nadie debe inventar un peso: se carga del YAML o se detiene."
            )
        if not 0.0 < self.umbral_ambar < self.umbral_rojo < 1.0:
            raise ConfiguracionIncompleta(
                f"Umbrales incoherentes: ambar={self.umbral_ambar}, rojo={self.umbral_rojo}."
            )


@dataclass(frozen=True, slots=True)
class CalculadoraIUT:
    """Aritmetica pura: paciente y fecha entran, indice explicado sale.

    Sin estado, sin efectos, sin reloj. `hoy` siempre se pasa por parametro:
    un dominio que consulta la hora no se puede probar contra casos hechos a
    mano.

    `parametros` no tiene valor por defecto y no lo va a tener: quien construye
    la calculadora tiene que decir con que politica clinica lo hace.
    """

    parametros: ParametrosIUT

    # ── Los ocho factores ────────────────────────────────────────────────────

    def _x1_urgencia_temporal(self, paciente: Paciente, hoy: date) -> AporteFactor:
        """clamp(1 - t_r/48, 0, 1) con t_r = meses hasta el cumpleanos 18.

        Satura en 1 el dia del corte y no baja de 0 antes de los 14: fuera de
        esos cuatro anios la urgencia temporal no significa nada.
        """
        meses = paciente.meses_hasta_corte(hoy)
        x = _acotar(1.0 - meses / self.parametros.horizonte_meses)
        return self._aporte(X1_URGENCIA_TEMPORAL, x)

    def _x2_complejidad(self, paciente: Paciente) -> AporteFactor:
        """Numero de CATEGORIAS CCC v2 distintas / techo. Extension, no cuenta.

        Cuenta sistemas comprometidos, no diagnosticos: tres codigos
        cardiovasculares son un sistema, no tres.

        Antes esto era min(K/5, 1) sobre el total de diagnosticos, y crecia con
        el numero de codigos igual que x3. El desglose los presentaba como dos
        razones independientes cuando eran la misma senal contada dos veces, y
        el desglose ES el producto: si un medico lee 'complejidad' y
        'severidad' como dos motivos distintos y solo hay uno, la promesa de
        explicabilidad esta rota.
        """
        categorias = {dx.categoria for dx in paciente.diagnosticos_contables}
        x = _acotar(len(categorias) / self.parametros.categorias_techo)
        return self._aporte(X2_COMPLEJIDAD, x)

    def _x3_severidad(self, paciente: Paciente) -> AporteFactor:
        """Severidad MAXIMA entre los diagnosticos contables / tope de escala.

        Gravedad, no cantidad. Un paciente con una condicion severa y dos leves
        es un paciente severo; sumar convertiria la severidad en un segundo
        contador de diagnosticos, que es exactamente lo que x2 ya hace.
        """
        severidades = [
            self.parametros.severidad_por_categoria.get(dx.categoria.value, 0)
            for dx in paciente.diagnosticos_contables
        ]
        maxima = max(severidades, default=0)
        x = _acotar(maxima / self.parametros.severidad_maxima_posible)
        return self._aporte(X3_SEVERIDAD, x)

    def _x4_dependencia_tecnologica(self, paciente: Paciente) -> AporteFactor:
        """Suma de pesos de dispositivos / techo.

        Un dispositivo desconocido pesa 0 y NO marca dato faltante: el catalogo
        de `config` es la referencia, y lo que no esta en el catalogo se
        registra pero no se puntua hasta que alguien decida cuanto vale.
        """
        suma = sum(
            self.parametros.peso_dispositivos.get(d.tipo, 0)
            for d in paciente.dispositivos
        )
        x = _acotar(suma / self.parametros.peso_maximo_dispositivos)
        return self._aporte(X4_DEPENDENCIA_TECNOLOGICA, x)

    def _x5_brecha_preparacion(self, paciente: Paciente) -> AporteFactor:
        """(5 - TRAQ)/4. Sin TRAQ ni checklist INSN se imputa 0.5 Y se marca dato_faltante.

        Soporta tanto el instrumento estandar TRAQ como el Checklist de 6 items
        del INSN San Borja (Rubrica INSN #3).
        """
        p = self.parametros
        if paciente.traq is not None:
            rango = p.traq_maximo - p.traq_minimo
            x = _acotar((p.traq_maximo - paciente.traq.puntaje) / rango)
            return self._aporte(X5_BRECHA_PREPARACION, x)

        if paciente.checklist_insn is not None:
            rango = p.traq_maximo - p.traq_minimo
            puntaje = paciente.checklist_insn.puntaje_traq_equivalente
            x = _acotar((p.traq_maximo - puntaje) / rango)
            return self._aporte(X5_BRECHA_PREPARACION, x)

        return self._aporte(X5_BRECHA_PREPARACION, p.traq_imputacion, faltante=True)

    def _x6_riesgo_perdida(self, paciente: Paciente, hoy: date) -> AporteFactor:
        """clamp(delta / (2*theta), 0, 1) con theta = intervalo de control.

        Sin fecha de ultima consulta se imputa y se marca faltante: no saber
        cuando vino por ultima vez no es lo mismo que haber venido ayer.
        """
        p = self.parametros
        dias = paciente.dias_desde_ultima_consulta(hoy)
        if dias is None:
            return self._aporte(X6_RIESGO_PERDIDA, p.imputacion_sin_consulta, faltante=True)
        x = _acotar(dias / (2 * p.intervalo_control_dias))
        return self._aporte(X6_RIESGO_PERDIDA, x)

    def _x7_barrera_acceso(self, paciente: Paciente) -> AporteFactor:
        """1 si procede de fuera de Lima Metropolitana o Callao.

        Binario a proposito: el costo de viajar a Lima para una cita de
        transicion es una barrera de otro tipo, no de otro grado.
        """
        p = self.parametros
        procedencia = paciente.procedencia.strip().lower()
        if not procedencia:
            return self._aporte(X7_BARRERA_ACCESO, p.imputacion_sin_procedencia, faltante=True)
        x = 0.0 if procedencia in p.lima_metropolitana else 1.0
        return self._aporte(X7_BARRERA_ACCESO, x)

    def _x8_continuidad_seguro(self, paciente: Paciente) -> AporteFactor:
        """Riesgo de perder la cobertura al cumplir 18.

        El SIS sale marcado como dato faltante a proposito: no sabemos que pasa
        y el YAML lo dice. Un supuesto que empuja a alguien a rojo tiene que
        verse en pantalla como supuesto.
        """
        p = self.parametros
        clave = paciente.tipo_seguro.value
        if clave not in p.riesgo_seguro:
            raise ConfiguracionIncompleta(
                f"No hay riesgo de seguro configurado para '{clave}'."
            )
        verificado = p.riesgo_seguro_verificado.get(clave, False)
        return self._aporte(
            X8_CONTINUIDAD_SEGURO, p.riesgo_seguro[clave], faltante=not verificado
        )

    def _aporte(self, nombre: str, x: float, faltante: bool = False) -> AporteFactor:
        return AporteFactor(
            nombre=nombre,
            x=x,
            beta=self.parametros.betas[nombre],
            dato_faltante=faltante,
            explicacion=_EXPLICACIONES[nombre],
        )

    # ── El indice ────────────────────────────────────────────────────────────

    def calcular(
        self,
        paciente: Paciente,
        hoy: date,
        umbral_rojo: float | None = None,
    ) -> IndiceUrgencia:
        """El IUT del paciente a una fecha, con su desglose ordenado.

        `umbral_rojo` permite pasar el valor calibrado contra la capacidad real
        del equipo (`calibrar_umbral_rojo`). Sin el, se usa el del YAML.
        """
        aportes = (
            self._x1_urgencia_temporal(paciente, hoy),
            self._x2_complejidad(paciente),
            self._x3_severidad(paciente),
            self._x4_dependencia_tecnologica(paciente),
            self._x5_brecha_preparacion(paciente),
            self._x6_riesgo_perdida(paciente, hoy),
            self._x7_barrera_acceso(paciente),
            self._x8_continuidad_seguro(paciente),
        )
        # El orden es la explicacion: quien lee el desglose lee primero lo que
        # mas pesa. `IndiceUrgencia` rechaza cualquier otro orden.
        ordenados = tuple(sorted(aportes, key=lambda a: a.aporte, reverse=True))

        z = self.parametros.beta_0 + sum(a.aporte for a in ordenados)
        valor = sigmoide(z)
        rojo = self.parametros.umbral_rojo if umbral_rojo is None else umbral_rojo
        # Si la calibracion devuelve un rojo por debajo del ambar (cohorte
        # chica, capacidad grande), las bandas se juntan. No se corrige en
        # silencio: `IndiceUrgencia.bandas_colapsadas` lo deja visible para que
        # la interfaz pueda decir que el equipo va holgado, en vez de mostrar
        # un semaforo sin banda intermedia y que parezca un error.
        ambar = min(self.parametros.umbral_ambar, rojo)

        return IndiceUrgencia(
            valor=valor,
            z=z,
            beta_0=self.parametros.beta_0,
            aportes=ordenados,
            estado=self._semaforo(valor, rojo, ambar),
            umbral_rojo=rojo,
            umbral_ambar=ambar,
            confianza_minima=self.parametros.confianza_minima,
        )

    @staticmethod
    def _semaforo(valor: float, rojo: float, ambar: float) -> EstadoSemaforo:
        if valor >= rojo:
            return EstadoSemaforo.ROJO
        if valor >= ambar:
            return EstadoSemaforo.AMBAR
        return EstadoSemaforo.VERDE


def calibrar_umbral_rojo(
    indices: Sequence[float],
    capacidad_mensual: int,
) -> float:
    """Deriva el umbral rojo de la capacidad real del equipo.

    PLAN_TECNICO §6.2: no es un adorno, es un argumento del pitch. Marcar en
    rojo a mas pacientes de los que el equipo puede atender no prioriza nada —
    solo reparte culpa. El umbral es el IUT del paciente que ocupa el ultimo
    lugar atendible.

    Sin capacidad devuelve un umbral genuinamente inalcanzable. No 1.0: la
    comparacion del semaforo es `valor >= rojo`, y `sigmoide` devuelve
    exactamente 1.0 en cuanto z pasa de unos 37 por redondeo de coma flotante,
    de modo que un umbral de 1.0 dejaria pasar a rojo justo a los pacientes mas
    extremos. `nextafter(1.0, 2.0)` es el primer float por encima de 1.0, que
    ningun IUT puede alcanzar.

    Con capacidad mayor que la cohorte devuelve el indice mas bajo: todos
    entran.

    TODO: confirmar con mentor — capacidad mensual del equipo de transicion.
    """
    if capacidad_mensual <= 0:
        return INALCANZABLE
    if not indices:
        return INALCANZABLE
    ordenados = sorted(indices, reverse=True)
    posicion = min(capacidad_mensual, len(ordenados)) - 1
    return ordenados[posicion]
