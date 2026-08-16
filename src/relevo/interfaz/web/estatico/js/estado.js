// El estado de la sesion, EN MEMORIA. Nada clinico toca el navegador.
//
// ═══════════════════════════════════════════════════════════════════════════
// POR QUE NO SE USA localStorage
// ═══════════════════════════════════════════════════════════════════════════
//
// La Ley 29733 clasifica los datos de salud como DATOS SENSIBLES (art. 2.5).
// Guardarlos en el navegador —sin cifrado, sin control de acceso y sin
// registro de quien los toco— no es una implementacion incompleta: es una que
// no se puede desplegar.
//
// Y hay un motivo practico igual de fuerte: un portatil compartido en un
// consultorio conserva ese localStorage para el siguiente que se siente.
//
// Todo lo de aqui vive en memoria y se pierde al recargar. Esa perdida es
// deliberada y es la unica politica de retencion que este proyecto puede
// prometer sin mentir.
//
// `tests/interfaz/test_sin_almacenamiento_navegador.py` falla si aparece
// localStorage o sessionStorage en cualquier archivo.

const estado = {
  rol: null,
  establecimiento: "",
  pacienteId: null,
  // La fecha de evaluacion. Se puede mover para demostrar el paso del tiempo
  // sin tocar el reloj de la maquina.
  hoy: "",
  // Cache de la ultima respuesta, solo para no repetir la peticion al volver
  // atras dentro del mismo minuto. Se limpia al cambiar de rol.
  cache: new Map(),
};

const suscriptores = new Set();

export function suscribir(fn) {
  suscriptores.add(fn);
  return () => suscriptores.delete(fn);
}

function notificar() {
  suscriptores.forEach((fn) => fn(estado));
}

// ── Rol ─────────────────────────────────────────────────────────────────────

export const rolActual = () => estado.rol;
export const establecimientoActual = () => estado.establecimiento;

export function fijarRol(rol, establecimiento = "") {
  estado.rol = rol;
  estado.establecimiento = establecimiento;
  // Cambiar de rol vacia la cache SIEMPRE. Si no, una vista podria pintar con
  // datos que el rol nuevo no tiene derecho a ver — que es exactamente la fuga
  // que el aislamiento por establecimiento viene a impedir.
  estado.cache.clear();
  notificar();
}

// ── Paciente en foco ────────────────────────────────────────────────────────

export const pacienteActual = () => estado.pacienteId;

export function fijarPaciente(id) {
  estado.pacienteId = id;
  notificar();
}

// ── Fecha ───────────────────────────────────────────────────────────────────

export const hoyActual = () => estado.hoy;

export function fijarHoy(fecha) {
  estado.hoy = fecha || "";
  estado.cache.clear();
  notificar();
}

// ── Caché de lectura ────────────────────────────────────────────────────────

export function recordar(clave, valor) {
  estado.cache.set(clave, valor);
  return valor;
}

export function recordado(clave) {
  return estado.cache.get(clave);
}

export function olvidarTodo() {
  estado.cache.clear();
}
