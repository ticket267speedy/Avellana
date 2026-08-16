// Punto de montaje. Registra las rutas y arranca el router.
//
// Este archivo NO tiene logica de producto: solo cablea. Es el equivalente en
// el navegador de `interfaz/arranque.py` — el unico sitio donde se nombran las
// piezas concretas.

import { registrar, arrancar, esc } from "./enrutador.js";
import { montar as montarBarra } from "./barra_demo.js";
import * as entrar from "./vistas/entrar.js";
import * as paciente from "./vistas/paciente.js";
import * as ruta from "./vistas/ruta.js";
import * as entrenate from "./vistas/entrenate.js";
import * as leccion from "./vistas/leccion.js";
import * as pasaporte from "./vistas/pasaporte.js";
import * as radar from "./vistas/radar.js";
import * as bandeja from "./vistas/bandeja.js";
import * as digitalizacion from "./vistas/digitalizacion.js";

const app = document.getElementById("app");
const barra = document.getElementById("barra-demo");

// Cada vista exporta `render()` y, si necesita manejadores, `enganchar()`.
// Registrarlas asi —en una tabla y no repartidas— hace que anadir la octava
// vista sea una linea, y que se vea de un vistazo cuantas hay.
const VISTAS = [
  ["/entrar", entrar],
  ["/paciente", paciente],
  ["/paciente/digitalizacion", digitalizacion],
  ["/paciente/ruta", ruta],
  ["/paciente/entrenate", entrenate],
  ["/paciente/leccion/:numero", leccion],
  ["/pasaporte/:id", pasaporte],
  ["/insn/radar", radar],
  ["/insn/digitalizacion", digitalizacion],
  ["/receptor/bandeja", bandeja],
];

let repintar = () => {};

VISTAS.forEach(([patron, modulo]) => {
  registrar(patron, async (parametros) => {
    const html = await modulo.render(parametros);
    // Se devuelve el enganche junto con el HTML, sin ejecutarlo aqui. Es el
    // router (`enrutador.js`) quien lo llama, y lo hace justo despues de
    // asignar `innerHTML` — nunca antes. Un `queueMicrotask` aqui corria antes
    // de que el HTML estuviera en el DOM, y por eso ningun boton respondia.
    return {
      html,
      enganchar: modulo.enganchar ? () => modulo.enganchar(app, repintar) : null,
    };
  });
});

function alFallar(error, contenedor) {
  // Un error se muestra con su mensaje, no se traga. Una pantalla vacia y
  // silenciosa es indistinguible de "no hay nada que mostrar", y en un sistema
  // clinico esa confusion es cara.
  const esPermiso = error.estado === 403 || error.estado === 404;
  contenedor.innerHTML = `
    <section class="tarjeta error">
      <h2>${esPermiso ? "Aqui no hay nada para ti" : "Algo fallo"}</h2>
      <p>${esc(error.message)}</p>
      ${
        esPermiso
          ? `<p class="error-nota">
               Si eres profesional de un hospital receptor, solo ves las
               referencias dirigidas a tu establecimiento.
             </p>`
          : ""
      }
      <p><a href="#/entrar" data-ir="/entrar">Volver al inicio</a></p>
    </section>`;
}

async function iniciar() {
  const pintar = arrancar(app, alFallar);
  repintar = async () => {
    await pintar();
    await montarBarra(barra, repintar);
  };
  await repintar();
}

iniciar();
