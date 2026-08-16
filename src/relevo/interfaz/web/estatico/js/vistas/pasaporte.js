// Vista 5 · El Pasaporte 18+ en pantalla, con insignias de origen.
//
// Cada dato dice DE DONDE SALE. Es lo que convierte un documento en algo que se
// puede corregir: si el paciente ve que una dosis la declaro el y el INSN
// todavia no la cotejo, puede decirlo. Si todo se presentara igual de firme,
// nadie corregiria nada.
//
// El PDF se descarga del endpoint que ya existia. Sale con marca de agua y con
// el aviso normativo al pie.

import { verPaciente, verConciliacion, declararMedicacion, urlPasaporte } from "../api.js";
import { hoyActual } from "../estado.js";
import { esc } from "../enrutador.js";
import { lineaMedicacion, listaDiscrepancias } from "../componentes/badge_origen.js";

export async function render(parametros) {
  const id = parametros.id;
  const [paciente, conciliacion] = await Promise.all([
    verPaciente(id, hoyActual()),
    verConciliacion(id),
  ]);

  return `
    <section class="pasaporte">
      <h1>Pasaporte de Salud 18+</h1>
      <p class="pasaporte-meta">
        ${esc(id)} · ${paciente.edad} anios ·
        ${paciente.meses_restantes >= 0
          ? `${paciente.meses_restantes} meses hasta el corte`
          : "ya cumplio 18"}
        · Seguro: ${esc(paciente.tipo_seguro)}
      </p>

      <p><a class="boton" href="${urlPasaporte(id)}" target="_blank" rel="noopener">
        Descargar el PDF para imprimir y firmar</a></p>

      <div class="tarjeta">
        <h2>Que tengo</h2>
        <ul class="lista-simple">
          ${paciente.diagnosticos.map((d) => `<li>${esc(d)}</li>`).join("") ||
            "<li>Sin diagnosticos registrados</li>"}
        </ul>
      </div>

      <div class="tarjeta">
        <h2>Que tomo</h2>
        <ul class="lista-medicacion">
          ${conciliacion.lineas.map(lineaMedicacion).join("") ||
            "<li>Sin medicacion registrada</li>"}
        </ul>
        ${listaDiscrepancias(conciliacion.discrepancias)}
        ${formularioDeclaracion(id)}
      </div>

      <div class="tarjeta">
        <h2>A que soy alergico</h2>
        <ul class="lista-simple">
          ${paciente.alergias.map((a) => `<li>${esc(a)}</li>`).join("") ||
            "<li>Sin alergias registradas</li>"}
        </ul>
      </div>

      ${
        paciente.dispositivos.length
          ? `<div class="tarjeta"><h2>Dispositivos</h2>
             <ul class="lista-simple">
               ${paciente.dispositivos.map((d) => `<li>${esc(d)}</li>`).join("")}
             </ul></div>`
          : ""
      }

      <p class="aviso-normativo">
        Documento informativo complementario para la transicion asistencial. No
        reemplaza la historia clinica ni el resumen de historia clinica normado
        (RM 214-2018-MINSA). Elaborado con apoyo automatizado, revisado y
        firmado por el medico tratante.
      </p>
    </section>`;
}

// El unico formulario clinico de texto libre de todo el producto, y lo llena EL
// PACIENTE. No es doble digitacion: ese dato no lo tenia nadie mas. Lo que
// declare aqui nunca sobrescribe el Pasaporte — abre un caso que revisa el
// equipo del INSN.
function formularioDeclaracion(id) {
  return `
    <details class="declarar">
      <summary>Lo que tomo de verdad no coincide con esta lista</summary>
      <p class="declarar-nota">
        Cuentanoslo. <strong>No se cambia tu Pasaporte con esto</strong>: se
        abre una revision para que el equipo del INSN lo coteje contigo.
      </p>
      <form data-declarar="${esc(id)}">
        <label>Medicamento
          <input name="nombre" required maxlength="160" autocomplete="off">
        </label>
        <label>Dosis (como te la sabes)
          <input name="dosis" maxlength="80" autocomplete="off">
        </label>
        <label>Cada cuanto
          <input name="frecuencia" maxlength="80" autocomplete="off">
        </label>
        <button class="boton" type="submit">Enviar para revision</button>
      </form>
      <p class="respuesta-declaracion" role="status"></p>
    </details>`;
}

export function enganchar(contenedor) {
  const formulario = contenedor.querySelector("[data-declarar]");
  if (!formulario) return;

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const datos = new FormData(formulario);
    const salida = contenedor.querySelector(".respuesta-declaracion");
    try {
      const resultado = await declararMedicacion(formulario.dataset.declarar, [
        {
          nombre: datos.get("nombre"),
          dosis: datos.get("dosis") || null,
          frecuencia: datos.get("frecuencia") || null,
          lo_sigue_tomando: true,
        },
      ]);
      salida.textContent = resultado.titular;
      formulario.reset();
    } catch (error) {
      salida.textContent = `No se pudo registrar: ${error.message}`;
    }
  });
}
