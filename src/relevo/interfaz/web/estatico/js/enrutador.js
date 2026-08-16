// Router por hash. Sin dependencias y sin configuracion de servidor.
//
// Por hash y no por History API a proposito: asi recargar #/insn/radar
// funciona sin ninguna regla de reescritura, y el despliegue sigue siendo un
// solo proceso — `uvicorn` y nada mas.

const rutas = [];

export function registrar(patron, render) {
  rutas.push({ segmentos: patron.split("/").filter(Boolean), render });
}

function emparejar(ruta) {
  const partes = ruta.split("/").filter(Boolean);
  for (const candidata of rutas) {
    if (candidata.segmentos.length !== partes.length) continue;
    const parametros = {};
    let coincide = true;
    for (let i = 0; i < partes.length; i += 1) {
      const esperado = candidata.segmentos[i];
      if (esperado.startsWith(":")) {
        parametros[esperado.slice(1)] = decodeURIComponent(partes[i]);
      } else if (esperado !== partes[i]) {
        coincide = false;
        break;
      }
    }
    if (coincide) return { render: candidata.render, parametros };
  }
  return null;
}

export function rutaActual() {
  return (window.location.hash || "#/entrar").slice(1);
}

export function ir(ruta) {
  window.location.hash = ruta.startsWith("#") ? ruta : `#${ruta}`;
}

export function arrancar(contenedor, alFallar) {
  async function pintar() {
    const ruta = rutaActual();
    const encontrada = emparejar(ruta);

    if (!encontrada) {
      contenedor.innerHTML =
        '<section class="tarjeta"><h2>No hay nada aqui</h2>' +
        '<p><a href="#/entrar">Volver a la eleccion de rol</a></p></section>';
      return;
    }

    contenedor.innerHTML = '<p class="cargando">Cargando…</p>';
    try {
      const resultado = await encontrada.render(encontrada.parametros);
      // Una vista puede devolver el HTML a secas, o { html, enganchar }
      // cuando necesita manejadores de clic. Se acepta lo primero por
      // simplicidad, pero SIEMPRE se resuelve a esta forma antes de tocar el
      // DOM: es lo que garantiza que enganchar() nunca corra antes de que el
      // HTML este pintado.
      const html = typeof resultado === "string" ? resultado : resultado.html;
      const enganchar =
        typeof resultado === "string" ? null : resultado.enganchar;

      contenedor.innerHTML = html;
      // Los manejadores se enganchan DESPUES de pintar, no con onclick en el
      // HTML: el HTML lo compone cada vista con datos del servidor, y un
      // onclick en linea seria un hueco de inyeccion abierto de par en par.
      contenedor.querySelectorAll("[data-ir]").forEach((elemento) => {
        elemento.addEventListener("click", (evento) => {
          evento.preventDefault();
          ir(elemento.dataset.ir);
        });
      });
      // Se llama de forma SINCRONA, aqui mismo, justo despues de asignar
      // innerHTML. Antes se enganchaba con `queueMicrotask` desde dentro de
      // la vista, y el orden real de la cola de microtareas hacia que
      // enganchar() corriera ANTES de que este innerHTML se asignara: los
      // botones existian un instante despues, pero ya sin manejador. Por eso
      // ningun boton de ninguna vista respondia a un clic.
      if (enganchar) enganchar();
    } catch (error) {
      alFallar(error, contenedor);
    }
  }

  window.addEventListener("hashchange", pintar);
  return pintar;
}

// Escapado de todo texto que venga del servidor. La aplicacion compone HTML
// con plantillas, asi que un nombre de establecimiento con un '&' o un '<'
// romperia el render — y, peor, un texto controlado por un usuario podria
// inyectar marcado.
export function esc(texto) {
  if (texto === null || texto === undefined) return "";
  return String(texto)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
