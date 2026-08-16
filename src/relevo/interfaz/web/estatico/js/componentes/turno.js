// "¿Quién tiene el turno ahora?"
//
// Es la mejor pieza de comunicación del proyecto: cabe en una línea, no
// necesita explicación y le sirve igual al paciente que a la trabajadora
// social. El INSN pidió responsables dos veces en su documento —en el
// entregable 1 y en su Insight 5— y esto es la respuesta, visible en cada
// pantalla donde hay un ciclo.
//
// Se usa la pregunta LITERAL y no una paráfrasis ("Turno actual", etc.): el
// documento de fusión la señala explícitamente como la mejor frase del
// proyecto, y cambiarla le resta la fuerza de pregunta directa que tiene.

import { esc } from "../enrutador.js";

// Etiquetas cortas en texto, no emoji: el emoji se renderiza distinto según
// el sistema operativo y el navegador, y para personal sin mucho roce con
// tecnología una palabra corta es más fiable que un símbolo que puede no
// significar nada para ellos. El aspecto de "insignia" lo da el CSS
// (`.turno-icono`), no el carácter en sí.
const ETIQUETAS_CORTAS = {
  equipo_insn: "INSN",
  hospital_receptor: "Receptor",
  paciente: "Paciente",
  apoderado: "Apoderado",
  nadie: "Listo",
};

// Qué le toca hacer a cada uno. Sin esto, saber de quién es el turno no sirve
// de nada: "le toca al receptor" no le dice al paciente si tiene que esperar
// o llamar.
const QUE_HACER = {
  equipo_insn: "El equipo del INSN está preparando o destrabando el trámite.",
  hospital_receptor: "El hospital de adultos tiene que responder.",
  paciente: "Te toca a ti: presentarte a tu cita.",
  apoderado: "Le toca a tu apoderado.",
  nadie: "No hay nada pendiente. El traspaso se completó.",
};

export function turno(responsable, etiqueta, opciones = {}) {
  const corta = ETIQUETAS_CORTAS[responsable] || "—";
  const clase = responsable === "nadie" ? "turno turno-cerrado" : "turno";
  const explicacion = opciones.conExplicacion
    ? `<p class="turno-que-hacer">${esc(QUE_HACER[responsable] || "")}</p>`
    : "";

  return `
    <div class="${clase}">
      <p class="turno-pregunta">¿Quién tiene el turno ahora?</p>
      <p class="turno-respuesta">
        <span class="turno-icono" aria-hidden="true">${esc(corta)}</span>
        ${esc(etiqueta)}
      </p>
      ${explicacion}
    </div>`;
}

// Versión compacta, para una celda de tabla del radar.
export function turnoBreve(responsable, etiqueta) {
  const corta = ETIQUETAS_CORTAS[responsable] || "—";
  return `<span class="turno-breve" title="${esc(etiqueta)}">
    <span class="turno-icono" aria-hidden="true">${esc(corta)}</span> ${esc(etiqueta)}
  </span>`;
}
