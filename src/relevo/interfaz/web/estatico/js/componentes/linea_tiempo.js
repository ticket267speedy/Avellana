// La linea de tiempo de las siete etapas de la ruta de referencia.
//
// Se pintan SIEMPRE las siete, incluso las que faltan. Que el paciente vea
// cuanto queda por delante es la mitad del valor: hoy, al cumplir 18, el
// paciente simplemente deja de aparecer y nadie —el incluido— sabe en que
// punto se quedo.
//
// Los dos estados que no son tramite —perdida de seguimiento y reingreso— no
// van en la linea: estan en otra dimension del proceso, y meterlos como una
// octava casilla haria parecer que perderse es un paso del camino.

import { esc } from "../enrutador.js";

export function lineaTiempo(ciclo, opciones = {}) {
  const llano = opciones.llano === true;

  const pasos = ciclo.etapas
    .map((etapa) => {
      const clases = ["etapa"];
      if (etapa.alcanzada) clases.push("etapa-alcanzada");
      if (etapa.es_actual) clases.push("etapa-actual");

      const texto = llano ? etapa.etiqueta_llana : etapa.etiqueta;
      const marca = etapa.alcanzada ? "●" : "○";

      return `
        <li class="${clases.join(" ")}">
          <span class="etapa-marca" aria-hidden="true">${marca}</span>
          <span class="etapa-texto">${esc(texto)}</span>
        </li>`;
    })
    .join("");

  return `<ol class="linea-tiempo">${pasos}</ol>${fueraDeLinea(ciclo, llano)}`;
}

// Si el ciclo esta perdido o reabierto, se dice aparte y con todas las letras.
function fueraDeLinea(ciclo, llano) {
  if (ciclo.estado === "perdida_de_seguimiento") {
    return `
      <p class="fuera-de-linea alerta">
        ${llano
          ? "Perdimos el contacto contigo. Estamos intentando encontrarte."
          : "Perdida de seguimiento. El caso esta en busqueda activa."}
      </p>`;
  }
  if (ciclo.estado === "reingreso") {
    return `
      <p class="fuera-de-linea aviso">
        ${llano
          ? "Retomamos tu caso y lo estamos reubicando en el recorrido."
          : "Ciclo reabierto. REINGRESO es transitorio: exige reclasificacion " +
            "a un estado de tramite. Reabrir el ciclo NO reabre la atencion " +
            "pediatrica del INSN."}
      </p>`;
  }
  return "";
}

// El estado del plazo, dicho sin alarmismo pero sin esconderlo.
export function estadoPlazo(ciclo) {
  const mapa = {
    en_plazo: { clase: "plazo-bien", texto: "En plazo" },
    por_vencer: { clase: "plazo-aviso", texto: "Por vencer" },
    vencido: { clase: "plazo-mal", texto: "Vencido" },
    cerrado: { clase: "plazo-bien", texto: "Sin plazo pendiente" },
  };
  const estilo = mapa[ciclo.situacion_plazo] || mapa.en_plazo;
  const dias = ciclo.plazo_dias
    ? ` · ${ciclo.dias_en_estado} de ${ciclo.plazo_dias} dias`
    : "";

  return `<span class="plazo ${estilo.clase}">${esc(estilo.texto)}${esc(dias)}</span>`;
}

// El historial completo. Es la evidencia del piloto, no un adorno: la
// proporcion entre las vias por las que se confirma una atencion es en si
// misma un hallazgo.
export function historial(ciclo) {
  const filas = ciclo.historial
    .map(
      (e) => `
      <li>
        <span class="historial-fecha">${esc(e.fecha)}</span>
        <span class="historial-estado">${esc(e.etiqueta)}</span>
        ${e.nota ? `<span class="historial-nota">${esc(e.nota)}</span>` : ""}
        ${e.registrado_por ? `<span class="historial-quien">${esc(e.registrado_por)}</span>` : ""}
      </li>`
    )
    .join("");

  return `<details class="historial"><summary>Historial completo</summary>
    <ol>${filas}</ol></details>`;
}
