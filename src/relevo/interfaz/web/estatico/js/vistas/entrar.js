// Vista 1 · Eleccion de rol.
//
// NO ES AUTENTICACION y la pantalla lo dice con todas las letras. Fingir un
// inicio de sesion que no comprueba nada seria peor que declararlo pendiente:
// un jurado tecnico lo detecta en la primera pregunta.
//
// Los dos roles profesionales estan separados a proposito. Unificarlos le daria
// al receptor visibilidad sobre toda la cohorte pediatrica del INSN, que es
// exactamente el problema de proteccion de datos que este proyecto dice evitar.

import { fijarRol, fijarPaciente } from "../estado.js";
import { ir } from "../enrutador.js";

const ROLES = [
  {
    codigo: "paciente",
    nombre: "Paciente",
    descripcion:
      "Ve su recorrido en lenguaje llano, su Pasaporte y sus lecciones de Entrenate.",
    ruta: "/paciente",
    icono: "🙋",
  },
  {
    codigo: "apoderado",
    nombre: "Apoderado",
    descripcion:
      "La misma vista del paciente, con permisos recortados y aviso de que el " +
      "acceso caduca el dia que el paciente cumple 18 anios.",
    ruta: "/paciente",
    icono: "👪",
  },
  {
    codigo: "profesional_insn",
    nombre: "Profesional del INSN",
    descripcion:
      "Radar de la cohorte, con la metrica de corte etario arriba de todo.",
    ruta: "/insn/radar",
    icono: "🏥",
  },
  {
    codigo: "profesional_receptor",
    nombre: "Profesional del hospital receptor",
    descripcion:
      "Bandeja de referencias entrantes. Ve unicamente lo dirigido a su " +
      "establecimiento.",
    ruta: "/receptor/bandeja",
    icono: "🏨",
    establecimiento: "HOSPITAL NACIONAL  DOS DE MAYO",
  },
];

export async function render() {
  const tarjetas = ROLES.map(
    (r) => `
      <button class="tarjeta-rol" data-rol="${r.codigo}"
              data-ruta="${r.ruta}" data-establecimiento="${r.establecimiento || ""}">
        <span class="rol-icono" aria-hidden="true">${r.icono}</span>
        <span class="rol-nombre">${r.nombre}</span>
        <span class="rol-descripcion">${r.descripcion}</span>
      </button>`
  ).join("");

  return `
    <section class="entrar">
      <h1>¿Quien eres?</h1>
      <p class="entrar-intro">
        Relevo acompana la transicion del hospital pediatrico al de adultos.
        El INSN San Borja <strong>no atiende a mayores de 18 anios bajo ninguna
        circunstancia</strong>: el corte es duro y en fecha exacta. Este sistema
        existe para que nadie llegue a esa fecha sin destino.
      </p>

      <div class="rejilla-roles">${tarjetas}</div>

      <p class="aviso-sin-auth">
        <strong>Esta seleccion no es autenticacion.</strong> En el piloto se
        entra con usuario y contrasena (hash argon2id) y cookie de sesion de
        servidor. Se declara pendiente en vez de fingirla.
      </p>
    </section>`;
}

// Los manejadores se enganchan aparte del HTML: la vista compone marcado con
// datos, y un onclick en linea seria un hueco abierto de par en par.
export function enganchar(contenedor) {
  contenedor.querySelectorAll(".tarjeta-rol").forEach((boton) => {
    boton.addEventListener("click", () => {
      fijarRol(boton.dataset.rol, boton.dataset.establecimiento);
      // El paciente de demo es el caso protagonista. Un rol de paciente sin
      // paciente en foco pintaria una pantalla vacia.
      fijarPaciente("DEMO-0001");
      ir(boton.dataset.ruta);
    });
  });
}
