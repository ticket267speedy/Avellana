// Una leccion abierta: los cinco pasos y sus fuentes.
//
// Las fuentes van VISIBLES, al lado del contenido y no en un pie que nadie
// abre. Una leccion que le dice a un adolescente que su madre ya no puede
// pedir sus resultados tiene que poder decirle en que norma esta escrito, o es
// indistinguible de un rumor.

import { verLeccion } from "../api.js";
import { pacienteActual } from "../estado.js";
import { esc } from "../enrutador.js";
import { marcar } from "./entrenate.js";

export async function render(parametros) {
  const id = pacienteActual();
  if (!id) return '<section class="tarjeta"><p>Elige un rol primero.</p></section>';

  const leccion = await verLeccion(id, parametros.numero);

  return `
    <section class="leccion">
      <p><a href="#/paciente/entrenate" data-ir="/paciente/entrenate">← Entrenate</a></p>
      <h1>${esc(leccion.titulo)}</h1>
      <p class="objetivo"><strong>Al terminar:</strong> ${esc(leccion.objetivo)}</p>

      ${leccion.sello ? selloEsqueleto(leccion.sello) : ""}

      ${leccion.completa ? pasos(leccion) : ""}
      ${leccion.fuentes.length ? fuentes(leccion.fuentes) : ""}

      ${
        leccion.completa
          ? `<div class="tarjeta">
               <h2>¿Ya la trabajaste?</h2>
               <p>Marcalo tu. Nadie lo marca por ti.</p>
               <button class="boton" data-marcar="${esc(leccion.habilidad)}">
                 Marcar como lograda
               </button>
             </div>`
          : ""
      }
    </section>`;
}

function selloEsqueleto(sello) {
  return `
    <div class="tarjeta esqueleto">
      <p class="sello-grande">${esc(sello)}</p>
      <p>
        Esta lección tiene su título, su objetivo y su estructura —aprender,
        practicar, desafío, tarea de la vida real, retroalimentación— pero el
        contenido no está escrito.
      </p>
      <p>
        <strong>Y se dice en vez de rellenarlo.</strong> Escribir contenido
        clínico sin la firma de un médico del INSN violaría la regla que
        atraviesa este proyecto entero: ninguna salida clínica se emite sin
        revisión humana explícita.
      </p>
    </div>`;
}

function pasos(leccion) {
  return leccion.pasos
    .filter((p) => p.contenido.trim())
    .map(
      (p) => `
      <article class="paso">
        <h2>${esc(p.titulo)}</h2>
        <div class="paso-contenido">${parrafos(p.contenido)}</div>
      </article>`
    )
    .join("");
}

// Markdown minimo: parrafos y negritas. No se usa una libreria porque el
// contenido sale de un YAML que escribimos nosotros, y meter un parser
// completo para dos marcas seria traer una dependencia entera —y su superficie
// de ataque— a cambio de nada.
function parrafos(texto) {
  return texto
    .split(/\n\s*\n/)
    .map((bloque) => {
      const limpio = esc(bloque.trim()).replace(
        /\*\*(.+?)\*\*/g,
        "<strong>$1</strong>"
      );
      if (limpio.startsWith("&gt;")) {
        return `<blockquote>${limpio.replace(/^&gt;\s?/gm, "")}</blockquote>`;
      }
      if (/^\d\.\s/m.test(limpio)) {
        const puntos = limpio
          .split("\n")
          .filter(Boolean)
          .map((l) => `<li>${l.replace(/^\d\.\s*/, "")}</li>`)
          .join("");
        return `<ol>${puntos}</ol>`;
      }
      return `<p>${limpio.replaceAll("\n", "<br>")}</p>`;
    })
    .join("");
}

function fuentes(lista) {
  const filas = lista
    .map(
      (f) => `
      <li>
        <p class="fuente-afirmacion">${esc(f.afirmacion)}</p>
        <p class="fuente-norma">${esc(f.norma)}</p>
        ${f.detalle ? `<p class="fuente-detalle">${esc(f.detalle)}</p>` : ""}
      </li>`
    )
    .join("");

  return `
    <section class="fuentes">
      <h2>De dónde sale cada cosa</h2>
      <p class="fuentes-nota">
        Cada afirmación con su norma. Sin esto, "tu madre ya no puede pedir tus
        resultados" sería un rumor.
      </p>
      <ul>${filas}</ul>
    </section>`;
}

export function enganchar(contenedor) {
  const boton = contenedor.querySelector("[data-marcar]");
  if (!boton) return;
  boton.addEventListener("click", async () => {
    boton.disabled = true;
    await marcar(boton.dataset.marcar, "lograda");
    boton.textContent = "Marcada como lograda ✔";
  });
}
