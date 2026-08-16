// Vista 7 · La bandeja del hospital receptor.
//
// El receptor deja de ser un DATO y pasa a ser un USUARIO con acciones propias.
// Eso es el dolor B4, y es lo que convierte una transferencia FRIA —el ciclo
// avanzaba solo, sin que nadie del otro lado tocara nada— en la "transferencia
// calida" que el INSN pide con ese nombre en su entregable 7.
//
// CERO FORMULARIOS. Cada accion es un clic. Lo unico que el receptor escribe es
// el servicio que asigna, y lo unico que elige es de una lista cerrada.

import { verBandeja, accionReceptor } from "../api.js";
import { hoyActual } from "../estado.js";
import { esc } from "../enrutador.js";

const FALTANTES = [
  ["falta_epicrisis", "Falta la epicrisis"],
  ["falta_resultado_laboratorio", "Falta un resultado de laboratorio"],
  ["falta_consentimiento", "Falta el consentimiento"],
  ["falta_dato_de_contacto", "Falta un dato de contacto"],
  ["otro", "Otro"],
];

export async function render() {
  const filas = await verBandeja(hoyActual());

  if (!filas.length) {
    return `
      <section class="bandeja">
        <h1>Referencias entrantes</h1>
        <p class="vacio">
          No hay referencias dirigidas a su establecimiento. Solo se muestran
          las que le fueron referidas: la cohorte del INSN no es visible desde
          aqui.
        </p>
      </section>`;
  }

  return `
    <section class="bandeja">
      <h1>Referencias entrantes (${filas.length})</h1>
      <p class="bandeja-intro">
        Ordenadas por <strong>días hasta el corte etario</strong> y no por fecha
        de llegada: la urgente no es la más antigua, sino la del adolescente que
        se queda sin ningún servicio antes.
      </p>
      ${filas.map(tarjeta).join("")}
    </section>`;
}

function tarjeta(f) {
  const corte =
    f.dias_para_corte === null
      ? ""
      : f.dias_para_corte < 0
        ? `<span class="corte-pasado">Ya cumplió 18 hace ${-f.dias_para_corte} días</span>`
        : `<span class="${f.dias_para_corte < 90 ? "corte-cerca" : ""}">
             Cumple 18 en ${f.dias_para_corte} días</span>`;

  return `
    <article class="referencia ${f.situacion_plazo === "vencido" ? "vencida" : ""}">
      <header>
        <span class="referencia-id">${esc(f.paciente_id)}</span>
        <span class="referencia-edad">${f.edad} años</span>
        ${corte}
      </header>
      <p class="referencia-dx">${esc(f.diagnostico_principal)}</p>
      <p class="referencia-estado">
        ${esc(f.etiqueta)} · ${f.dias_en_estado} días
        <span class="plazo-${esc(f.situacion_plazo)}">${esc(f.situacion_plazo)}</span>
      </p>
      <div class="acciones">
        ${f.acciones.map((a) => botonAccion(f.paciente_id, a)).join("")}
        ${extras(f)}
      </div>
      <p class="respuesta" role="status" data-respuesta="${esc(f.paciente_id)}"></p>
    </article>`;
}

function botonAccion(id, accion) {
  return `<button class="boton-accion" data-paciente="${esc(id)}"
    data-accion="${esc(accion.codigo)}">${esc(accion.etiqueta)}</button>`;
}

// La accion 3 y la variante de inasistencia se pintan aparte porque no son un
// clic simple: una necesita la lista cerrada y la otra es la respuesta opuesta
// a la accion 6. En la bandeja aparecen juntas porque son las dos respuestas
// posibles a la misma pregunta.
function extras(f) {
  let html = "";
  if (f.estado === "en_evaluacion") {
    html += `
      <details class="solicitar">
        <summary>Solicitar informacion complementaria</summary>
        <p class="solicitar-nota">
          Esto es lo unico que convierte un rechazo silencioso en una peticion
          trazable. No retrocede el expediente: devuelve el turno al INSN.
        </p>
        ${FALTANTES.map(
          ([codigo, texto]) => `
          <label><input type="checkbox" name="falta" value="${codigo}"> ${texto}</label>`
        ).join("")}
        <button class="boton" data-paciente="${esc(f.paciente_id)}"
          data-accion="solicitar_informacion">Enviar peticion</button>
      </details>`;
  }
  if (f.estado === "cita_programada") {
    html += `<button class="boton-secundario" data-paciente="${esc(f.paciente_id)}"
      data-accion="registrar_inasistencia">No se presentó</button>`;
  }
  return html;
}

export function enganchar(contenedor, repintar) {
  contenedor.querySelectorAll("[data-accion]").forEach((boton) => {
    boton.addEventListener("click", async () => {
      const id = boton.dataset.paciente;
      const salida = contenedor.querySelector(`[data-respuesta="${id}"]`);
      boton.disabled = true;
      try {
        const resultado = await accionReceptor(id, boton.dataset.accion, cuerpo(boton));
        salida.textContent = resultado.mensaje;
        if (resultado.gano_destino_asegurado) salida.classList.add("logro");
        setTimeout(repintar, 900);
      } catch (error) {
        salida.textContent = `No se pudo: ${error.message}`;
        boton.disabled = false;
      }
    });
  });
}

function cuerpo(boton) {
  const datos = { quien: "Dr. receptor (demo)" };
  const contenedor = boton.closest("details");

  if (boton.dataset.accion === "solicitar_informacion" && contenedor) {
    datos.faltantes = [...contenedor.querySelectorAll("input[name=falta]:checked")].map(
      (c) => c.value
    );
  }
  if (boton.dataset.accion === "aceptar_con_servicio") {
    // Seleccion de la cartera del establecimiento, no texto clinico libre.
    datos.servicio = "Medicina Interna — consultorio 2";
  }
  if (boton.dataset.accion === "programar_cita") {
    const fecha = new Date();
    fecha.setDate(fecha.getDate() + 45);
    datos.fecha_cita = fecha.toISOString().slice(0, 10);
  }
  return datos;
}
