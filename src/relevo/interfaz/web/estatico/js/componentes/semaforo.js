// El semaforo del IUT y su desglose.
//
// ═══════════════════════════════════════════════════════════════════════════
// EL INDICE NO PRIORIZA PACIENTES: ORDENA LA COLA DE TRABAJO
// ═══════════════════════════════════════════════════════════════════════════
//
// El INSN excluyo de su alcance una IA que "priorice pacientes de manera
// autonoma", y tiene razon. Esto no decide quien se atiende primero en un
// hospital: decide a quien llama primero la trabajadora social.
//
// Por eso el desglose es OBLIGATORIO en la interfaz y no un detalle
// desplegable opcional: un numero sin sus factores es opaco, y un numero opaco
// no se puede discutir. Con los ocho factores a la vista, un medico puede
// mirarlo, no estar de acuerdo, y reordenar la cola a mano.

import { esc } from "../enrutador.js";

const NOMBRES = {
  rojo: "Prioridad alta",
  ambar: "Prioridad media",
  verde: "Prioridad baja",
};

export function semaforo(indice) {
  const estado = indice.estado || "verde";
  const dudoso = indice.datos_insuficientes
    ? '<span class="marca-dudosa" title="El indice se calculo con datos imputados">datos incompletos</span>'
    : "";

  return `
    <span class="semaforo semaforo-${esc(estado)}">
      <span class="punto" aria-hidden="true"></span>
      ${esc(NOMBRES[estado] || estado)}
      <span class="valor">${(indice.valor * 100).toFixed(0)}</span>
    </span>${dudoso}`;
}

export function desglose(indice) {
  const aportes = [...(indice.aportes || [])].sort((a, b) => b.aporte - a.aporte);
  const maximo = Math.max(...aportes.map((a) => Math.abs(a.aporte)), 0.001);

  const filas = aportes
    .map((a) => {
      const ancho = (Math.abs(a.aporte) / maximo) * 100;
      const faltante = a.dato_faltante
        ? '<span class="imputado" title="dato ausente: se imputo y se marca">imputado</span>'
        : "";
      return `
        <li class="aporte">
          <span class="aporte-nombre">${esc(a.nombre)} ${faltante}</span>
          <span class="aporte-barra"><i style="width:${ancho.toFixed(0)}%"></i></span>
          <span class="aporte-cifra">${a.aporte.toFixed(2)}</span>
          <span class="aporte-beta">β=${a.beta.toFixed(1)}</span>
        </li>`;
    })
    .join("");

  return `
    <details class="desglose" open>
      <summary>De donde sale este numero</summary>
      <p class="desglose-nota">
        El sistema <strong>no prioriza pacientes: ordena esta cola</strong>. Los
        pesos (β) los define un medico del INSN en un archivo que el hospital
        versiona. Cualquier persona puede reordenar la lista a mano.
      </p>
      <ul class="aportes">${filas}</ul>
      <p class="desglose-pie">
        Confianza del calculo: ${(indice.confianza * 100).toFixed(0)} %.
        ${indice.datos_insuficientes ? "Hay factores imputados por falta de dato." : ""}
      </p>
    </details>`;
}
