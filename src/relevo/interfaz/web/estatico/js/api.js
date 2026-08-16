// EL UNICO ARCHIVO CON fetch(). Una funcion por endpoint.
//
// Por que la regla: cuando cada vista hace su propia llamada, cambiar una
// cabecera —o anadir la de sesion cuando exista autenticacion— obliga a tocar
// diez archivos y siempre queda uno sin tocar. `tests/interfaz/` verifica por
// grep que fetch() no aparece en ningun otro .js.

import { rolActual, establecimientoActual } from "./estado.js";

const BASE = "";

// El rol viaja en cabecera mientras no haya sesion de servidor. NO es
// autenticacion y no finge serlo: el servidor le cree al cliente. Cuando exista
// la cookie de sesion (C6), este es el unico sitio que cambia.
function cabeceras() {
  const h = { "Content-Type": "application/json" };
  const rol = rolActual();
  if (rol) h["X-Relevo-Rol"] = rol;
  const establecimiento = establecimientoActual();
  if (establecimiento) h["X-Relevo-Establecimiento"] = establecimiento;
  return h;
}

async function pedir(ruta, opciones = {}) {
  const respuesta = await fetch(BASE + ruta, { headers: cabeceras(), ...opciones });
  if (respuesta.status === 204) return null;

  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    // Se lanza un Error con el mensaje del servidor y no un objeto de estado:
    // asi una vista que se olvide de comprobar el resultado falla de forma
    // visible en vez de pintar una pantalla vacia y silenciosa.
    const detalle = cuerpo && cuerpo.detail ? cuerpo.detail : respuesta.statusText;
    const error = new Error(detalle);
    error.estado = respuesta.status;
    throw error;
  }
  return cuerpo;
}

function enviar(ruta, datos) {
  return pedir(ruta, { method: "POST", body: JSON.stringify(datos || {}) });
}

// ── Radar y pacientes ───────────────────────────────────────────────────────

export const listarPacientes = (hoy) => pedir(`/api/pacientes${consulta({ hoy })}`);
export const verPaciente = (id, hoy) => pedir(`/api/pacientes/${id}${consulta({ hoy })}`);
export const verCiclo = (id, hoy) => pedir(`/api/pacientes/${id}/ciclo${consulta({ hoy })}`);

export const avanzarCiclo = (id, datos) =>
  enviar(`/api/pacientes/${id}/ciclo/avanzar`, datos);

export const urlPasaporte = (id) => `/api/pacientes/${id}/pasaporte`;

// ── Entrenate ───────────────────────────────────────────────────────────────

export const verAprendizaje = (id) => pedir(`/api/pacientes/${id}/aprendizaje`);
export const verLeccion = (id, numero) => pedir(`/api/pacientes/${id}/lecciones/${numero}`);
export const avanzarHabilidad = (id, datos) =>
  enviar(`/api/pacientes/${id}/aprendizaje/avanzar`, datos);

// ── Conciliacion ────────────────────────────────────────────────────────────

export const verConciliacion = (id) => pedir(`/api/pacientes/${id}/conciliacion`);
export const declararMedicacion = (id, medicamentos) =>
  enviar(`/api/pacientes/${id}/medicacion/declarar`, { medicamentos });
export const resolverConciliacion = (id, datos) =>
  enviar(`/api/insn/${id}/conciliacion/resolver`, datos);

// ── Receptor ────────────────────────────────────────────────────────────────

export const verBandeja = (hoy) => pedir(`/api/receptor/bandeja${consulta({ hoy })}`);
export const accionReceptor = (id, accion, datos) =>
  enviar(`/api/receptor/${id}/${accion}`, datos);

// ── INSN ────────────────────────────────────────────────────────────────────

export const registrarReingreso = (id, datos) =>
  enviar(`/api/insn/${id}/reingreso`, datos);
export const reingresosEstancados = () => pedir("/api/insn/reingresos-estancados");

// ── Apoderado ───────────────────────────────────────────────────────────────

export const permisosApoderado = (id, hoy) =>
  pedir(`/api/apoderado/${id}/permisos${consulta({ hoy })}`);

// ── Metricas ────────────────────────────────────────────────────────────────

export const metricaCorteEtario = (hoy) =>
  pedir(`/api/metricas/corte-etario${consulta({ hoy })}`);
export const coberturaDestinos = () => pedir("/api/metricas/cobertura-destinos");

// ── Demo ────────────────────────────────────────────────────────────────────

export const estadoDemo = () => pedir("/api/demo/estado");
export const reiniciarDemo = () => enviar("/api/demo/reiniciar");
export const avanzarEtapa = (pacienteId) =>
  enviar("/api/demo/avanzar-etapa", { paciente_id: pacienteId });
export const cambiarRolServidor = (rol) => enviar("/api/demo/cambiar-rol", { rol });

function consulta(parametros) {
  const partes = Object.entries(parametros)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`);
  return partes.length ? `?${partes.join("&")}` : "";
}
