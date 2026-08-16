// "¿Quien tiene el turno ahora?"
//
// Es la mejor pieza de comunicacion del proyecto: cabe en una linea, no
// necesita explicacion y le sirve igual al paciente que a la trabajadora
// social. El INSN pidio responsables dos veces en su documento —en el
// entregable 1 y en su Insight 5— y esto es la respuesta, visible en cada
// pantalla donde hay un ciclo.

import { esc } from "../enrutador.js";

const ICONOS = {
  equipo_insn: "🏥",
  hospital_receptor: "🏨",
  paciente: "🙋",
  apoderado: "👪",
  nadie: "✅",
};

// Que le toca hacer a cada uno. Sin esto, saber de quien es el turno no sirve
// de nada: "le toca al receptor" no le dice al paciente si tiene que esperar o
// llamar.
const QUE_HACER = {
  equipo_insn: "El equipo del INSN esta preparando o destrabando el tramite.",
  hospital_receptor: "El hospital de adultos tiene que responder.",
  paciente: "Te toca a ti: presentarte a tu cita.",
  apoderado: "Le toca a tu apoderado.",
  nadie: "No hay nada pendiente. El traspaso se completo.",
};

export function turno(responsable, etiqueta, opciones = {}) {
  const icono = ICONOS[responsable] || "•";
  const clase = responsable === "nadie" ? "turno turno-cerrado" : "turno";
  const explicacion = opciones.conExplicacion
    ? `<p class="turno-que-hacer">${esc(QUE_HACER[responsable] || "")}</p>`
    : "";

  return `
    <div class="${clase}">
      <p class="turno-pregunta">¿Quien tiene el turno ahora?</p>
      <p class="turno-respuesta"><span aria-hidden="true">${icono}</span> ${esc(etiqueta)}</p>
      ${explicacion}
    </div>`;
}

// Version compacta, para una celda de tabla del radar.
export function turnoBreve(responsable, etiqueta) {
  const icono = ICONOS[responsable] || "•";
  return `<span class="turno-breve" title="${esc(etiqueta)}">${icono} ${esc(etiqueta)}</span>`;
}
