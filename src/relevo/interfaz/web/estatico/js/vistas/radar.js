// Vista 6 · El radar del INSN.
//
// LA METRICA DE CORTE ETARIO VA ARRIBA DE TODO. Cualquier otra cifra del
// sistema —Pasaportes emitidos, referencias enviadas— mide actividad. Esta mide
// el dano que el proyecto existe para evitar: cuantos adolescentes cumplen 18
// sin ningun servicio al que ir.

import { listarPacientes, metricaCorteEtario, coberturaDestinos } from "../api.js";
import { hoyActual, fijarPaciente } from "../estado.js";
import { esc, ir } from "../enrutador.js";
import { semaforo } from "../componentes/semaforo.js";
import { turnoBreve } from "../componentes/turno.js";

const FILTROS = {
  todos: () => true,
  accion_insn: (f) => f.responsable === "Equipo de transicion del INSN",
  esperando_receptor: (f) => f.responsable === "Hospital receptor",
  sin_destino: (f) => !f.tiene_destino_asegurado,
  completadas: (f) => f.estado_ciclo === "primera_atencion_confirmada",
};

export async function render() {
  const hoy = hoyActual();
  const [filas, corte, destinos] = await Promise.all([
    listarPacientes(hoy),
    metricaCorteEtario(hoy),
    coberturaDestinos(),
  ]);

  return `
    <section class="radar">
      ${cabeceraCorteEtario(corte)}
      ${tarjetaDestinos(destinos)}

      <div class="filtros" role="group" aria-label="Filtros del radar">
        <button class="filtro activo" data-filtro="todos">Todas (${filas.length})</button>
        <button class="filtro" data-filtro="accion_insn">Requieren accion del INSN</button>
        <button class="filtro" data-filtro="esperando_receptor">Esperando al receptor</button>
        <button class="filtro" data-filtro="sin_destino">Sin destino asegurado</button>
        <button class="filtro" data-filtro="completadas">Completadas</button>
      </div>

      <table class="tabla-radar">
        <thead>
          <tr>
            <th>Paciente</th><th>Edad</th><th>Prioridad</th>
            <th>Etapa</th><th>Turno</th><th>Corte</th>
          </tr>
        </thead>
        <tbody>${filas.map(fila).join("")}</tbody>
      </table>

      <p class="nota-iut">
        El indice <strong>no prioriza pacientes: ordena esta cola de trabajo</strong>.
        No decide quien se atiende primero en un hospital; decide a quien llama
        primero la trabajadora social. Cada puntaje muestra sus ocho factores con
        su peso, y cualquier persona puede reordenar la lista a mano.
      </p>
    </section>`;
}

function cabeceraCorteEtario(corte) {
  return `
    <div class="corte-etario">
      <h1>Corte etario</h1>
      <div class="corte-cifras">
        <div class="cifra cifra-riesgo">
          <span class="numero">${corte.en_riesgo_90_dias}</span>
          <span class="etiqueta">cumplen 18 en menos de ${corte.horizonte_dias} dias
            <strong>sin destino asegurado</strong></span>
        </div>
        <div class="cifra cifra-dano">
          <span class="numero">${corte.ya_cumplieron_sin_destino}</span>
          <span class="etiqueta">ya cumplieron 18 sin destino</span>
        </div>
        <div class="cifra cifra-total">
          <span class="numero">${corte.total_cohorte}</span>
          <span class="etiqueta">ciclos en seguimiento</span>
        </div>
      </div>
      <p class="corte-aclaracion">
        <strong>Cumplir 18 no es el fracaso.</strong> La primera cita en el
        hospital de adultos ocurre, por definicion, despues de los 18. El
        fracaso es cumplir 18 <em>sin destino asegurado</em>.
      </p>
      ${
        corte.sin_fecha_de_nacimiento.length
          ? `<p class="corte-incompletos">
               ${corte.sin_fecha_de_nacimiento.length} ciclos sin fecha de
               nacimiento: no se pueden evaluar y no se cuentan en el
               denominador.
             </p>`
          : ""
      }
    </div>`;
}

function tarjetaDestinos(destinos) {
  return `
    <div class="tarjeta destinos">
      <h2>Cobertura de destinos</h2>
      <p class="destinos-cifra">
        <strong>${destinos.sin_destino} de ${destinos.total_evaluados}</strong>
        sin destino identificado (${destinos.porcentaje_sin_destino} %)
      </p>
      <p class="destinos-nota">
        El sistema <strong>no inventa destinos: mide su ausencia</strong>. Este
        numero hoy no lo tiene nadie, y es evidencia de brecha de oferta que se
        puede llevar a una mesa de gestion.
      </p>
      <p class="destinos-directorio">${esc(destinos.resumen_directorio)}</p>
    </div>`;
}

function fila(f) {
  const corte =
    f.dias_para_corte === null
      ? "—"
      : f.dias_para_corte < 0
        ? `<span class="corte-pasado">cumplio hace ${-f.dias_para_corte} d</span>`
        : `<span class="${f.dias_para_corte < 90 ? "corte-cerca" : ""}">${f.dias_para_corte} d</span>`;

  return `
    <tr class="${f.requiere_atencion_ahora ? "fila-urgente" : ""}"
        data-paciente="${esc(f.id)}"
        data-responsable="${esc(f.responsable || "")}"
        data-estado="${esc(f.estado_ciclo || "")}"
        data-destino="${f.tiene_destino_asegurado}">
      <td class="celda-id">${esc(f.id)}<br><small>${esc(f.diagnostico_principal)}</small></td>
      <td>${f.edad}</td>
      <td>${semaforo(f.indice)}</td>
      <td>${esc(f.estado_ciclo_etiqueta || "sin ciclo")}</td>
      <td>${f.responsable ? turnoBreve("", f.responsable) : "—"}</td>
      <td>${corte}</td>
    </tr>`;
}

export function enganchar(contenedor) {
  contenedor.querySelectorAll(".filtro").forEach((boton) => {
    boton.addEventListener("click", () => {
      contenedor.querySelectorAll(".filtro").forEach((b) => b.classList.remove("activo"));
      boton.classList.add("activo");
      aplicarFiltro(contenedor, boton.dataset.filtro);
    });
  });

  contenedor.querySelectorAll("tr[data-paciente]").forEach((fila) => {
    fila.addEventListener("click", () => {
      fijarPaciente(fila.dataset.paciente);
      ir(`/pasaporte/${fila.dataset.paciente}`);
    });
  });
}

function aplicarFiltro(contenedor, nombre) {
  const predicado = FILTROS[nombre] || FILTROS.todos;
  contenedor.querySelectorAll("tr[data-paciente]").forEach((fila) => {
    const datos = {
      responsable: fila.dataset.responsable,
      estado_ciclo: fila.dataset.estado,
      tiene_destino_asegurado: fila.dataset.destino === "true",
    };
    fila.hidden = !predicado(datos);
  });
}
