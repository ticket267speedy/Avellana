// La insignia que dice DE DONDE SALE cada dato.
//
// Es la capa de presentacion de `EstadoCampo` (VERDE/AMBAR/ROJO). El dominio
// sigue razonando en esos tres estados; esto los traduce a la pregunta que se
// hace una persona:
//
//     EstadoCampo responde  "¿me puedo fiar de esto?"   -> pregunta del sistema
//     OrigenDato  responde  "¿quien dijo esto?"          -> pregunta de la persona
//
// Un adolescente mirando su Pasaporte no necesita saber que un campo esta en
// ambar; necesita saber que esa dosis la dijo el, y que el INSN todavia no la
// coteja con su historia. Es la misma informacion contada desde el otro lado, y
// la segunda version es la que permite que alguien la corrija.

import { esc } from "../enrutador.js";

const ESTILOS = {
  verificado_insn: { clase: "origen-verde", icono: "✔" },
  informado_por_paciente: { clase: "origen-ambar", icono: "🗣" },
  pendiente_de_cotejo: { clase: "origen-rojo", icono: "?" },
};

export function badgeOrigen(origen, insignia) {
  const estilo = ESTILOS[origen] || ESTILOS.pendiente_de_cotejo;
  return `<span class="badge-origen ${estilo.clase}" title="${esc(origen)}">
    <span aria-hidden="true">${estilo.icono}</span> ${esc(insignia)}
  </span>`;
}

// Una linea de medicacion con su insignia y, si toca, su hueco.
//
// El hueco es DELIBERADO: si la dosis no esta verificada en la fuente, no se
// imprime un valor plausible. Un hueco visible obliga al medico a llenarlo; una
// dosis inventada no obliga a nada, y es el peor fallo posible de este sistema.
export function lineaMedicacion(linea) {
  const dosis = linea.hay_que_completar
    ? '<span class="hueco">dosis: ____________ (completar)</span>'
    : esc(linea.dosis || "—");
  const frecuencia = linea.frecuencia ? ` · ${esc(linea.frecuencia)}` : "";

  return `
    <li class="linea-medicacion">
      <span class="medicamento-nombre">${esc(linea.nombre)}</span>
      <span class="medicamento-dosis">${dosis}${frecuencia}</span>
      ${badgeOrigen(linea.origen, linea.insignia)}
    </li>`;
}

export function listaDiscrepancias(discrepancias) {
  if (!discrepancias.length) {
    return '<p class="sin-discrepancias">Se cotejo la medicacion y coincide.</p>';
  }
  const filas = discrepancias
    .map(
      (d) => `
      <li class="discrepancia">
        <span class="discrepancia-tipo">${esc(d.etiqueta)}</span>
        <span class="discrepancia-texto">${esc(d.descripcion)}</span>
      </li>`
    )
    .join("");

  return `
    <div class="discrepancias">
      <p class="discrepancias-aviso">
        El sistema <strong>no decide cual version es la correcta</strong>: solo
        reporta la diferencia. Lo revisa el equipo del INSN.
      </p>
      <ul>${filas}</ul>
    </div>`;
}
