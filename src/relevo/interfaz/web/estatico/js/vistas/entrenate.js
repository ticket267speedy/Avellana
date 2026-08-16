// Vista 4 · Entrenate. Siete habilidades, siete lecciones.
//
// El TRAQ deja de ser un numero de reporte y pasa a ser el diagnostico que
// decide la intervencion: medir -> intervenir -> volver a medir. Ese bucle es
// el cierre del dolor B3, que estaba en un 10 %.
//
// Seis de las siete lecciones van SELLADAS como pendientes de validacion
// clinica del INSN. No se esconde: un esqueleto honesto es mas fuerte ante un
// jurado clinico que siete lecciones que nadie del equipo puede defender.

import { verAprendizaje, avanzarHabilidad } from "../api.js";
import { pacienteActual } from "../estado.js";
import { esc, ir } from "../enrutador.js";

const CLASES_ESTADO = {
  por_iniciar: "hab-inicio",
  en_practica: "hab-practica",
  lograda: "hab-lograda",
  necesita_refuerzo: "hab-refuerzo",
};

export async function render() {
  const id = pacienteActual();
  if (!id) return '<section class="tarjeta"><p>Elige un rol primero.</p></section>';

  const datos = await verAprendizaje(id);
  const lecciones = new Map(datos.lecciones.map((le) => [le.habilidad, le]));

  return `
    <section class="entrenate">
      <h1>Entrenate</h1>
      <p class="franja">
        ${esc(datos.franja_etiqueta || "Fuera del recorrido")}
        ${datos.version_pasaporte
          ? `· Pasaporte ${esc(datos.version_pasaporte)}`
          : ""}
      </p>

      <div class="tarjeta destacada">
        <p class="progreso-resumen">${esc(datos.resumen)}</p>
        <p class="motivo-recomendacion">${esc(datos.motivo)}</p>
        ${
          datos.siguiente_leccion
            ? `<button class="boton" data-leccion="${datos.siguiente_leccion}">
                 Empezar la lección ${datos.siguiente_leccion}</button>`
            : ""
        }
      </div>

      <p class="invariante">
        Ninguna lección condiciona tu traspaso. Aprender es para ti, no un
        requisito para que te deriven.
      </p>

      <div class="rejilla-habilidades">
        ${datos.habilidades.map((h) => tarjetaHabilidad(h, lecciones)).join("")}
      </div>
    </section>`;
}

function tarjetaHabilidad(habilidad, lecciones) {
  const leccion = lecciones.get(habilidad.codigo);
  const clase = CLASES_ESTADO[habilidad.estado] || "hab-inicio";
  const sello = leccion && leccion.sello
    ? `<span class="sello">${esc(leccion.sello)}</span>`
    : '<span class="sello sello-ok">Contenido validado</span>';

  return `
    <article class="habilidad ${clase}">
      <p class="habilidad-numero">Lección ${habilidad.numero}</p>
      <h2>${esc(habilidad.titulo)}</h2>
      <p class="habilidad-estado">${esc(habilidad.estado_etiqueta)}</p>
      ${sello}
      <button class="boton-secundario" data-leccion="${habilidad.numero}">
        Abrir
      </button>
    </article>`;
}

export function enganchar(contenedor) {
  contenedor.querySelectorAll("[data-leccion]").forEach((boton) => {
    boton.addEventListener("click", () => {
      ir(`/paciente/leccion/${boton.dataset.leccion}`);
    });
  });
}

// ── Marcar una habilidad ────────────────────────────────────────────────────
// Lo marca el ADOLESCENTE sobre si mismo, nunca el personal de salud. Ver una
// leccion y lograr la habilidad son cosas distintas: confundirlas produciria
// una metrica que sube sola con solo abrir pantallas.
export async function marcar(habilidad, estado) {
  const id = pacienteActual();
  return avanzarHabilidad(id, { habilidad, estado, nota: "" });
}
