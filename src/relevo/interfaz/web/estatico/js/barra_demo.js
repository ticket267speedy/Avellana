// La barra de control de la demo. Fija en todas las pantallas.
//
// Cambiar rol, avanzar etapa, mover la fecha y reiniciar. Por debajo es lo que
// `sembrar.py` ya hacia por linea de comandos.
//
// Es ANDAMIO DE LA DEMOSTRACION, no funcionalidad del producto, y esta
// separada en su propio archivo para que se vea que lo es. El selector de rol
// no es autenticacion y la barra lo dice.

import { estadoDemo, reiniciarDemo, avanzarEtapa, cambiarRolServidor } from "./api.js";
import { fijarRol, fijarHoy, rolActual, hoyActual, pacienteActual } from "./estado.js";
import { esc, ir } from "./enrutador.js";

const ROLES = [
  ["paciente", "Paciente"],
  ["apoderado", "Apoderado"],
  ["profesional_insn", "Profesional INSN"],
  ["profesional_receptor", "Profesional receptor"],
  ["administrador", "Administrador"],
];

const ESTABLECIMIENTO_DEMO = "HOSPITAL NACIONAL  DOS DE MAYO";

export async function montar(contenedor, repintar) {
  const estado = await estadoDemo().catch(() => null);

  contenedor.innerHTML = `
    <span class="demo-etiqueta">DEMO</span>
    <select class="demo-rol" aria-label="Cambiar de rol">
      ${ROLES.map(
        ([codigo, nombre]) =>
          `<option value="${codigo}" ${codigo === rolActual() ? "selected" : ""}>
             ${nombre}</option>`
      ).join("")}
    </select>
    <input class="demo-fecha" type="date" value="${esc(hoyActual() || "2026-08-16")}"
           aria-label="Fecha de evaluacion" title="Mover la fecha sin tocar el reloj">
    <button class="demo-avanzar" title="Empuja el ciclo del paciente en foco">
      Avanzar etapa
    </button>
    <button class="demo-reiniciar" title="Vuelve al punto de partida. Misma semilla, misma cohorte">
      Reiniciar
    </button>
    ${
      estado
        ? `<span class="demo-conteo" title="Cadena de auditoria">
             ${estado.pacientes} pac · ${estado.ciclos} ciclos ·
             ${estado.cadena_intacta ? "cadena ✔" : "CADENA ROTA ✖"}
           </span>`
        : ""
    }`;

  enganchar(contenedor, repintar);
}

function enganchar(contenedor, repintar) {
  contenedor.querySelector(".demo-rol").addEventListener("change", async (evento) => {
    const rol = evento.target.value;
    // Actualiza el estado local antes de navegar para que la vista nueva use el
    // rol correcto aunque la respuesta del servidor tarde un instante.
    fijarRol(rol, rol === "profesional_receptor" ? ESTABLECIMIENTO_DEMO : "");
    const respuesta = await cambiarRolServidor(rol).catch(() => null);
    ir(respuesta ? respuesta.ruta_inicial : "#/entrar");
  });

  contenedor.querySelector(".demo-fecha").addEventListener("change", (evento) => {
    // Mover la fecha y ver como se mueven los plazos y la metrica de corte
    // etario es media demostracion, y no toca el reloj de la maquina.
    fijarHoy(evento.target.value);
    repintar();
  });

  contenedor.querySelector(".demo-avanzar").addEventListener("click", async (evento) => {
    const id = pacienteActual() || "DEMO-0001";
    evento.target.disabled = true;
    try {
      const resultado = await avanzarEtapa(id);
      evento.target.title = resultado.mensaje || "";
      repintar();
    } finally {
      evento.target.disabled = false;
    }
  });

  contenedor.querySelector(".demo-reiniciar").addEventListener("click", async (evento) => {
    evento.target.disabled = true;
    evento.target.textContent = "Reiniciando…";
    try {
      await reiniciarDemo();
      // La auditoria se conserva a proposito: un registro que se puede borrar
      // no es un registro de auditoria. Reiniciar dos veces deja rastro de las
      // dos, y eso es justo lo que se quiere poder ensenar.
      repintar();
    } finally {
      evento.target.disabled = false;
      evento.target.textContent = "Reiniciar";
    }
  });
}
