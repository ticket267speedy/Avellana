// Vista 2 · El paciente. Todo en lenguaje llano.
//
// "Tu nuevo hospital esta revisando tu informacion" y no "EN_EVALUACION". Es la
// misma verdad en un idioma que se entiende sin haber trabajado nunca en un
// hospital.
//
// Sirve tambien al APODERADO: es la misma vista con permisos recortados y el
// aviso de caducidad. No se duplica — duplicarla habria producido dos sitios
// donde arreglar cada cosa, y uno de los dos se habria quedado atras.

import { verCiclo, verAprendizaje, permisosApoderado, urlPasaporte } from "../api.js";
import { pacienteActual, hoyActual, rolActual } from "../estado.js";
import { esc } from "../enrutador.js";
import { turno } from "../componentes/turno.js";

export async function render() {
  const id = pacienteActual();
  if (!id) return '<section class="tarjeta"><p>Elige un rol primero.</p></section>';

  const esApoderado = rolActual() === "apoderado";
  const permisos = esApoderado ? await permisosApoderado(id, hoyActual()) : null;

  if (esApoderado && !permisos.puede_ver_estado_del_ciclo) {
    return bloqueadoPorEdad(permisos);
  }

  const ciclo = await verCiclo(id, hoyActual());
  const aprendizaje = esApoderado ? null : await verAprendizaje(id);

  return `
    <section class="paciente">
      ${esApoderado ? avisoApoderado(permisos) : ""}
      <h1>${esApoderado ? "Como va el traspaso" : "Tu traspaso"}</h1>

      <div class="tarjeta destacada">
        <p class="estado-llano">${esc(ciclo.etiqueta_llana)}</p>
        ${turno(ciclo.responsable, ciclo.responsable_etiqueta, { conExplicacion: true })}
        <p><a class="enlace-ruta" href="#/paciente/ruta" data-ir="/paciente/ruta">
          Ver el recorrido completo →</a></p>
      </div>

      ${aprendizaje ? proximaActividad(aprendizaje) : ""}

      <div class="tarjeta">
        <h2>Tu Pasaporte de Salud 18+</h2>
        <p>
          Es el documento que te llevas y que le entregas al medico de adultos.
          Lo firma tu medico tratante.
        </p>
        ${
          !esApoderado || permisos.puede_ver_pasaporte
            ? `<p><a class="boton" href="${urlPasaporte(id)}" target="_blank"
                 rel="noopener">Abrir mi Pasaporte (PDF)</a></p>
               <p><a href="#/pasaporte/${esc(id)}" data-ir="/pasaporte/${esc(id)}">
                 Ver el detalle en pantalla →</a></p>`
            : `<p class="aviso">El paciente no autorizo el acceso al Pasaporte
                 completo. Puede hacerlo desde su propia sesion.</p>`
        }
      </div>

      ${aprendizaje ? "" : ""}
      <div class="tarjeta">
        <h2>Tus tareas pendientes</h2>
        ${tareas(ciclo, aprendizaje)}
      </div>
    </section>`;
}

function proximaActividad(aprendizaje) {
  if (!aprendizaje.siguiente_leccion) {
    return `<div class="tarjeta">
      <h2>Entrenate</h2><p>${esc(aprendizaje.motivo)}</p>
      <p><a href="#/paciente/entrenate" data-ir="/paciente/entrenate">
        Ver mis siete habilidades →</a></p></div>`;
  }
  return `
    <div class="tarjeta">
      <h2>Lo siguiente que te toca aprender</h2>
      <p class="motivo-recomendacion">${esc(aprendizaje.motivo)}</p>
      <p class="progreso-resumen">${esc(aprendizaje.resumen)}</p>
      <p><a class="boton" href="#/paciente/entrenate" data-ir="/paciente/entrenate">
        Ir a Entrenate</a></p>
    </div>`;
}

function tareas(ciclo, aprendizaje) {
  const lista = [];

  if (ciclo.responsable === "paciente") {
    lista.push(
      ciclo.fecha_cita
        ? `Presentarte a tu cita del <strong>${esc(ciclo.fecha_cita)}</strong>.`
        : "Estar pendiente de tu cita."
    );
  }
  if (aprendizaje && aprendizaje.siguiente_leccion) {
    lista.push(
      `Trabajar la leccion ${aprendizaje.siguiente_leccion} de Entrenate.`
    );
  }
  lista.push("Revisar que tu telefono este actualizado.");
  lista.push("Contarnos que medicamentos estas tomando de verdad.");

  return `<ul class="tareas">${lista.map((t) => `<li>${t}</li>`).join("")}</ul>`;
}

// ── Apoderado ───────────────────────────────────────────────────────────────

function avisoApoderado(permisos) {
  if (!permisos.aviso) return "";
  return `<div class="aviso-caducidad">
    <p>${esc(permisos.aviso)}</p>
    <p class="norma">${esc(permisos.norma)}</p>
  </div>`;
}

function bloqueadoPorEdad(permisos) {
  return `
    <section class="tarjeta bloqueado">
      <h1>Tu acceso termino</h1>
      <p>${esc(permisos.aviso || "")}</p>
      <p class="norma">
        Base legal: ${esc(permisos.base_legal_etiqueta)} · ${esc(permisos.norma)}
      </p>
      <p>
        Esto no es un fallo del sistema. Al cumplir 18 anios, la informacion de
        salud pasa a ser exclusivamente del paciente, y solo el puede volver a
        autorizar el acceso.
      </p>
    </section>`;
}
