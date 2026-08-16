// Vista 6 · El radar del INSN.
//
// LA MÉTRICA DE CORTE ETARIO VA ARRIBA DE TODO. Cualquier otra cifra del
// sistema —Pasaportes emitidos, referencias enviadas— mide actividad. Esta
// mide el daño que el proyecto existe para evitar: cuántos adolescentes
// cumplen 18 sin ningún servicio al que ir.
//
// El TÍTULO en pantalla no dice "corte etario": ese es el nombre técnico
// interno (viene de `dominio/servicios/corte_etario.py`) y no dice nada por sí
// solo a alguien sin roce con el vocabulario del proyecto. El título grande
// dice la consecuencia humana; el nombre técnico va como subtítulo, entre
// paréntesis, para quien lo necesite.

import { listarPacientes, metricaCorteEtario, coberturaDestinos } from "../api.js";
import { hoyActual, fijarPaciente } from "../estado.js";
import { esc, ir } from "../enrutador.js";
import { semaforo } from "../componentes/semaforo.js";
import { turnoBreve } from "../componentes/turno.js";

const FILTROS = {
  todos: () => true,
  accion_insn: (f) => f.responsable === "Equipo de transición del INSN",
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
      ${tarjetaDigitalizacion()}

      <div class="filtros" role="group" aria-label="Filtros del radar">
        <button class="filtro activo" data-filtro="todos">Todas (${filas.length})</button>
        <button class="filtro" data-filtro="accion_insn">Requieren acción del INSN</button>
        <button class="filtro" data-filtro="esperando_receptor">Esperando al hospital receptor</button>
        <button class="filtro" data-filtro="sin_destino">Sin destino asegurado</button>
        <button class="filtro" data-filtro="completadas">Completadas</button>
      </div>

      <table class="tabla-radar">
        <thead>
          <tr>
            <th>Paciente</th><th>Edad</th><th>Prioridad</th>
            <th>Etapa del trámite</th><th>¿A quién le toca?</th><th>Tiempo hasta el corte</th>
          </tr>
        </thead>
        <tbody>${filas.map(fila).join("")}</tbody>
      </table>

      <p class="nota-iut">
        Este número <strong>no prioriza pacientes: ordena esta lista de trabajo</strong>.
        No decide quién se atiende primero en un hospital; decide a quién llama
        primero la trabajadora social. Cada puntaje muestra sus ocho factores
        con su peso, y cualquier persona puede reordenar la lista a mano.
      </p>
    </section>`;
}

function cabeceraCorteEtario(corte) {
  return `
    <div class="corte-etario">
      <h1>Pacientes en riesgo de quedarse sin hospital</h1>
      <p class="corte-subtitulo">(métrica de corte etario)</p>
      <div class="corte-cifras">
        <div class="cifra cifra-riesgo">
          <span class="numero">${corte.en_riesgo_90_dias}</span>
          <span class="etiqueta">cumplen 18 años en menos de ${corte.horizonte_dias} días
            <strong>sin tener aún un hospital de adultos asegurado</strong></span>
        </div>
        <div class="cifra cifra-dano">
          <span class="numero">${corte.ya_cumplieron_sin_destino}</span>
          <span class="etiqueta">ya cumplieron 18 años sin un hospital asegurado</span>
        </div>
        <div class="cifra cifra-total">
          <span class="numero">${corte.total_cohorte}</span>
          <span class="etiqueta">pacientes en seguimiento</span>
        </div>
      </div>
      <p class="corte-aclaracion">
        <strong>Cumplir 18 años no es, por sí solo, un problema.</strong> La
        primera cita en el hospital de adultos ocurre, por definición, después
        de los 18. El problema es cumplir 18 años <em>sin tener ya asegurado a
        dónde va a ir</em>.
      </p>
      ${
        corte.sin_fecha_de_nacimiento.length
          ? `<p class="corte-incompletos">
               ${corte.sin_fecha_de_nacimiento.length} pacientes no tienen
               fecha de nacimiento registrada: no se pueden evaluar y no
               entran en estos números.
             </p>`
          : ""
      }
    </div>`;
}

function tarjetaDestinos(destinos) {
  return `
    <div class="tarjeta destinos">
      <h2>¿A cuántos les falta un hospital de adultos?</h2>
      <p class="destinos-cifra">
        <strong>${destinos.sin_destino} de ${destinos.total_evaluados}</strong>
        pacientes todavía no tienen un hospital de adultos identificado
        (${destinos.porcentaje_sin_destino} %)
      </p>
      <p class="destinos-nota">
        El sistema <strong>no inventa un hospital: muestra cuando falta uno</strong>.
        Este número hoy no lo tiene nadie, y es evidencia de un vacío real de
        oferta de servicios que se puede llevar a una mesa de gestión.
      </p>
      <p class="destinos-directorio">${esc(destinos.resumen_directorio)}</p>
    </div>`;
}

function tarjetaDigitalizacion() {
  return `
    <div class="tarjeta digitalizacion-accion">
      <h2>Digitalización de historias clínicas</h2>
      <p>
        El perfil del INSN puede subir documentos escaneados para que la lectura
        automática extraiga campos clave y deje una vista previa antes de la
        revisión humana final.
      </p>
      <p><a class="boton" href="#/insn/digitalizacion" data-ir="/insn/digitalizacion">
        Abrir OCR e ingreso de documentos →
      </a></p>
    </div>`;
}

function fila(f) {
  const corte =
    f.dias_para_corte === null
      ? "—"
      : f.dias_para_corte < 0
        ? `<span class="corte-pasado">cumplió hace ${-f.dias_para_corte} d</span>`
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
