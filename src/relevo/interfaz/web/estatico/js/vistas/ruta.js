// Vista 3 · La ruta de referencia, contada al paciente.
//
// Tres preguntas, en este orden:
//   1. ¿Por donde voy?          -> la linea de las siete etapas
//   2. ¿Quien tiene el turno?   -> el responsable, con todas las letras
//   3. ¿Que tengo que hacer yo? -> lo unico accionable para el
//
// El orden importa. Empezar por "que tengo que hacer" sin decir antes en que
// punto esta el tramite convierte el sistema en una lista de deberes.

import { verCiclo } from "../api.js";
import { pacienteActual, hoyActual } from "../estado.js";
import { esc } from "../enrutador.js";
import { turno } from "../componentes/turno.js";
import { lineaTiempo, estadoPlazo, historial } from "../componentes/linea_tiempo.js";

export async function render() {
  const id = pacienteActual();
  if (!id) return '<section class="tarjeta"><p>Elige un rol primero.</p></section>';

  const ciclo = await verCiclo(id, hoyActual());

  return `
    <section class="ruta">
      <h1>Tu recorrido</h1>
      <p class="ruta-intro">
        Son siete etapas. Cumplir 18 años <strong>no interrumpe</strong> este
        recorrido: la primera cita en el hospital de adultos ocurre, por
        definición, después de tu cumpleaños. Lo que sí termina ese día es la
        atención en el INSN.
      </p>

      <div class="tarjeta">
        ${lineaTiempo(ciclo, { llano: true })}
        <p class="plazo-linea">${estadoPlazo(ciclo)}</p>
      </div>

      <div class="tarjeta destacada">
        ${turno(ciclo.responsable, ciclo.responsable_etiqueta, { conExplicacion: true })}
      </div>

      <div class="tarjeta">
        <h2>¿Qué tengo que hacer yo?</h2>
        ${queHacer(ciclo)}
      </div>

      ${destino(ciclo)}

      <div class="tarjeta">
        ${historial(ciclo)}
      </div>
    </section>`;
}

function queHacer(ciclo) {
  // Se responde SIEMPRE, incluso cuando la respuesta es "nada". "No tienes que
  // hacer nada ahora mismo, estamos nosotros" es información útil: la
  // alternativa es que el paciente se quede con la duda de si se le olvidó algo.
  const respuestas = {
    preparacion:
      "Nada por ahora. Tu equipo del INSN está armando tu expediente. Si te " +
      "cambia el teléfono, avísanos: es lo único que puede hacer que te " +
      "perdamos.",
    referencia_enviada:
      "Nada por ahora. Estamos esperando que tu nuevo hospital confirme que " +
      "recibió tus papeles.",
    recepcion_confirmada:
      "Nada por ahora. Tu nuevo hospital ya tiene tus papeles y le toca " +
      "revisarlos.",
    en_evaluacion:
      "Nada por ahora. Un médico de tu nuevo hospital está revisando tu caso.",
    aceptado_con_servicio:
      "Ya te aceptaron. Están buscando fecha para tu primera cita. Mantén tu " +
      "teléfono encendido.",
    cita_programada:
      "Te toca a ti: presentarte a tu cita. Lleva tu Pasaporte impreso y tu " +
      "documento de identidad.",
    primera_atencion_confirmada:
      "Nada pendiente. Ya te atendieron en tu nuevo hospital. Guarda tu " +
      "Pasaporte: te va a servir en cada consulta nueva.",
    perdida_de_seguimiento:
      "Contáctanos. Perdimos tu rastro y queremos ayudarte a terminar el " +
      "traspaso.",
    reingreso:
      "Nada por ahora. Retomamos tu caso y lo estamos reubicando en el " +
      "recorrido.",
  };

  const texto = respuestas[ciclo.estado] || "Consulta con tu equipo del INSN.";
  const cita =
    ciclo.estado === "cita_programada" && ciclo.fecha_cita
      ? `<p class="cita-destacada">Tu cita: <strong>${esc(ciclo.fecha_cita)}</strong>
         ${ciclo.servicio_asignado ? `· ${esc(ciclo.servicio_asignado)}` : ""}</p>`
      : "";

  return `<p class="que-hacer">${esc(texto)}</p>${cita}`;
}

function destino(ciclo) {
  if (!ciclo.establecimiento_receptor) {
    return `
      <div class="tarjeta alerta">
        <h2>Tu destino todavía no está definido</h2>
        <p>
          Esto no es un olvido: para algunas condiciones no existe todavía un
          servicio de adultos equivalente en el país. El sistema no lo inventa —
          lo cuenta, para que alguien pueda resolverlo.
        </p>
      </div>`;
  }
  return `
    <div class="tarjeta">
      <h2>Tu nuevo hospital</h2>
      <p class="destino-nombre">${esc(ciclo.establecimiento_receptor)}</p>
      ${
        ciclo.servicio_asignado
          ? `<p>Servicio asignado: <strong>${esc(ciclo.servicio_asignado)}</strong></p>`
          : "<p>Todavía sin servicio asignado.</p>"
      }
    </div>`;
}
