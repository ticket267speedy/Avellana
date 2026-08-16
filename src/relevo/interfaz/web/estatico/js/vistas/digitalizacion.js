import { rolActual } from "../estado.js";
import { esc } from "../enrutador.js";
import {
  cargarBlobDesdeRuta,
  estadoDigitalizacion,
  listarEjemplosDigitalizacion,
  leerDocumento,
} from "../api.js";

// ─────────────────────────────────────────────────────────────────────────
// VALIDADORES
// ─────────────────────────────────────────────────────────────────────────

function validarDNI(texto) {
  const limpio = texto.replace(/\D/g, "");
  if (limpio.length !== 8) return { valido: false, mensaje: "DNI debe tener 8 dígitos" };
  return { valido: true, mensaje: "" };
}

function validarCelular(texto) {
  const limpio = texto.replace(/\D/g, "");
  if (limpio.length !== 9) return { valido: false, mensaje: "Celular debe tener 9 dígitos" };
  if (!limpio.startsWith("9")) return { valido: false, mensaje: "Celular debe empezar con 9" };
  return { valido: true, mensaje: "" };
}

function validarNumeroHC(texto) {
  const limpio = texto.replace(/\D/g, "");
  if (!limpio) return { valido: false, mensaje: "Número de HC requerido" };
  if (limpio.length > 10) return { valido: false, mensaje: "Número de HC muy largo" };
  return { valido: true, mensaje: "" };
}

function validarFecha(texto) {
  if (!texto) return { valido: false, mensaje: "Fecha requerida" };
  // Acepta formato DD/MM/YYYY
  const match = texto.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return { valido: false, mensaje: "Formato: DD/MM/YYYY" };
  const [, d, m, a] = match;
  const fecha = new Date(`${a}-${m}-${d}`);
  if (isNaN(fecha.getTime())) return { valido: false, mensaje: "Fecha inválida" };
  return { valido: true, mensaje: "" };
}

// ─────────────────────────────────────────────────────────────────────────

async function cargarEjemplos() {
  try {
    return await listarEjemplosDigitalizacion();
  } catch {
    return [];
  }
}

async function cargarEstadoLlm() {
  try {
    return await estadoDigitalizacion();
  } catch {
    return { activo: false, modelo: "sin-modelo", host: "http://localhost:11434" };
  }
}

export async function render() {
  const rol = rolActual();
  const esInsn = rol === "profesional_insn" || rol === "administrador";
  const estado = await cargarEstadoLlm();
  const muestras = await cargarEjemplos();

  const valorInicial = muestras[0]?.id || "";
  const opcionesDocumentos = (muestras.length
    ? muestras
        .map(
          (m) => `<button type="button" class="opcion-documento" data-doc-id="${esc(m.id)}" data-doc-variante="${esc(m.variante || "manual")}">${esc(m.id)} · ${esc(m.variante || "manual")}</button>`
        )
        .join("")
    : '<div class="opcion-vacia">No hay documentos disponibles</div>'
  );
  const selectorCorpus = esInsn ? `
      <div class="filtro-documentos">
        <label for="filtro-id">Buscar por código:</label>
        <div class="selector-combinado">
          <input 
            id="filtro-id" 
            type="text" 
            placeholder="ej: hr_001" 
            class="filtro-input"
            value="${esc(valorInicial)}"
          />
          <button id="boton-desplegar-documentos" class="boton-dropdown" type="button" aria-expanded="false" aria-controls="lista-documentos">
            ▾
          </button>
        </div>
        <div id="lista-documentos" class="lista-documentos" role="listbox" aria-label="Documentos sugeridos">
          ${opcionesDocumentos}
        </div>
      </div>
    ` : `
      <div class="filtro-documentos restringido">
        <label>Buscar por código:</label>
        <div class="selector-combinado selector-restringido">
          <input type="text" class="filtro-input" value="Solo disponible para Profesional INSN" disabled />
        </div>
      </div>
    `;

  return `
    <section class="digitalizacion">
      <h1>Digitalización de documentos</h1>
      <p class="digitalizacion-intro">
        Lectura automática con OCR local + verificación en tres capas. 
        Ningún documento sale de esta máquina.
      </p>

      <div class="tarjeta-estado">
        <div class="estado-ocr">
          <strong>OCR:</strong> 
          <span class="estado-badge ${estado.activo ? "activo" : "inactivo"}">
            ${estado.activo ? `${esc(estado.modelo)}` : "modelo no disponible"}
          </span>
        </div>
        <div class="estado-host">
          <strong>Host:</strong> ${esc(estado.host)}
        </div>
        <div id="watchdog-mensaje" class="watchdog-mensaje">
          Estado del watchdog: ${estado.activo ? "modelo activo y respondiendo" : "modelo sin respuesta"}
        </div>
      </div>

      <div class="contenedor-lectura">
        <!-- COLUMNA IZQUIERDA: Navegación y selector -->
        <div class="columna-selector">
          <h3>Documentos del corpus</h3>
          ${selectorCorpus}

          <div id="preview-imagen" class="preview-imagen">
            <p class="placeholder-preview">La imagen aparecerá aquí</p>
          </div>

          <div class="info-documento">
            <small id="info-variante">—</small>
          </div>
        </div>

        <!-- COLUMNA DERECHA: Verificación de campos -->
        <div class="columna-verificacion">
          <h3>Verificación de campos</h3>
          
          <div id="estado-lectura" class="estado-lectura">
            <p class="instruccion">Selecciona un documento para comenzar la lectura.</p>
          </div>

          <div id="formulario-campos" class="formulario-campos" style="display:none;">
            <div class="campo-grupo">
              <label for="campo-dni">DNI del paciente</label>
              <input id="campo-dni" type="text" placeholder="8 dígitos" class="campo-input" />
              <small id="error-dni" class="error-msg"></small>
            </div>

            <div class="campo-grupo">
              <label for="campo-celular">Celular de contacto</label>
              <input id="campo-celular" type="text" placeholder="9 dígitos, empieza en 9" class="campo-input" />
              <small id="error-celular" class="error-msg"></small>
            </div>

            <div class="campo-grupo">
              <label for="campo-hc">N.º Historia Clínica</label>
              <input id="campo-hc" type="text" placeholder="solo dígitos" class="campo-input" />
              <small id="error-hc" class="error-msg"></small>
            </div>

            <div class="campo-grupo">
              <label for="campo-fecha">Fecha de nacimiento</label>
              <input id="campo-fecha" type="text" placeholder="DD/MM/YYYY" class="campo-input" />
              <small id="error-fecha" class="error-msg"></small>
            </div>

            <div class="campo-grupo">
              <label for="campo-revisor">Revisado por (nombre):</label>
              <input id="campo-revisor" type="text" placeholder="Tu nombre" class="campo-input" />
            </div>

            <div class="acciones-formulario">
              <button id="boton-descargar" class="boton boton-descargar">📥 Descargar acta</button>
              <button id="boton-confirmar" class="boton boton-confirmar" type="primary">✓ Confirmar lectura</button>
            </div>
          </div>
        </div>
      </div>

      <div class="tarjeta-upload">
        <h3>Cargar documento personal</h3>
        <div class="zona-upload">
          <input id="archivo-ocr" type="file" accept="image/*,.pdf" />
          <label for="archivo-ocr" class="label-archivo">
            Selecciona un documento o arrastralo aquí
          </label>
          <button id="boton-leer" class="boton boton-leer">Leer documento</button>
        </div>
      </div>

      <div id="resultado-ocr" class="resultado-ocr" style="display:none;">
        <div class="contenedor-resultado">
          <h2>Resultado de la lectura</h2>
          <div id="detalles-resultado"></div>
        </div>
      </div>
    </section>`;
}

export function enganchar(contenedor) {
  const listaDocumentos = contenedor.querySelector("#lista-documentos");
  const filtroId = contenedor.querySelector("#filtro-id");
  const botonDesplegar = contenedor.querySelector("#boton-desplegar-documentos");
  const previewImg = contenedor.querySelector("#preview-imagen");
  const estadoLectura = contenedor.querySelector("#estado-lectura");
  const formulariocampos = contenedor.querySelector("#formulario-campos");
  const botonLeer = contenedor.querySelector("#boton-leer");
  const inputArchivo = contenedor.querySelector("#archivo-ocr");
  const resultadoOcr = contenedor.querySelector("#resultado-ocr");
  const detallesResultado = contenedor.querySelector("#detalles-resultado");
  const watchdogMensaje = contenedor.querySelector("#watchdog-mensaje");
  const rol = rolActual();
  const esInsn = rol === "profesional_insn" || rol === "administrador";

  if (!previewImg || !estadoLectura) return;
  if (!esInsn) {
    if (filtroId) filtroId.disabled = true;
    if (botonDesplegar) botonDesplegar.disabled = true;
    if (listaDocumentos) listaDocumentos.classList.remove("abierto");
    return;
  }
  if (!listaDocumentos || !filtroId) return;

  const actualizarWatchdog = async () => {
    try {
      const estado = await cargarEstadoLlm();
      if (watchdogMensaje) {
        const momento = new Date().toLocaleTimeString("es-PE", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        watchdogMensaje.textContent = `Estado del watchdog: ${estado.activo ? "modelo activo y respondiendo" : "modelo sin respuesta"} · ${momento}`;
        watchdogMensaje.classList.toggle("watchdog-ok", Boolean(estado.activo));
      }
    } catch {
      if (watchdogMensaje) {
        watchdogMensaje.textContent = "Estado del watchdog: sin respuesta del servicio OCR";
        watchdogMensaje.classList.remove("watchdog-ok");
      }
    }
  };

  const normalizarFiltro = (texto) => texto.toLowerCase().trim();

  const actualizarSugerencias = () => {
    const filtro = normalizarFiltro(filtroId.value);
    const opciones = Array.from(listaDocumentos.querySelectorAll(".opcion-documento"));
    let visibles = 0;

    opciones.forEach((opcion) => {
      const textoOpcion = `${opcion.dataset.docId ?? ""} ${opcion.dataset.docVariante ?? ""}`.toLowerCase();
      const coincide = !filtro || textoOpcion.includes(filtro);
      const hidden = !coincide;
      opcion.hidden = hidden;
      if (coincide) visibles += 1;
    });

    if (visibles === 0 && !listaDocumentos.querySelector(".opcion-vacia")) {
      listaDocumentos.classList.add("lista-vacia");
    } else {
      listaDocumentos.classList.remove("lista-vacia");
    }
  };

  const cargarDocumentoActual = async (docId = filtroId.value) => {
    if (!docId) return;

    resultadoOcr.style.display = "none";

    try {
      const blob = await cargarBlobDesdeRuta(`/data/corpus/imagenes/${docId}.jpg`);
      const imgUrl = URL.createObjectURL(blob);
      const opcionSeleccionada = Array.from(listaDocumentos.querySelectorAll(".opcion-documento")).find(
        (opcion) => opcion.dataset.docId === docId
      );
      const variante = opcionSeleccionada?.dataset.docVariante || "—";

      filtroId.value = docId;
      previewImg.innerHTML = `
        <img src="${imgUrl}" alt="${esc(docId)}" class="imagen-documento" />
      `;

      contenedor.querySelector("#info-variante").textContent = `Variante: ${variante}`;

      estadoLectura.innerHTML = `
        <div class="estado-cargado">
          <p>📄 Documento <strong>${esc(docId)}</strong> cargado</p>
          <button class="boton-lectura" id="boton-leer-corpus">Leer con OCR local</button>
        </div>
      `;

      contenedor.querySelector("#boton-leer-corpus")?.addEventListener("click", async () => {
        await ejecutarLectura(blob, docId);
      });
    } catch (error) {
      estadoLectura.innerHTML = `<p class="error">Error al cargar: ${esc(error.message)}</p>`;
    }
  };

  // ─────────────────────────────────────────────────────────────────────
  // MANEJO DEL SELECTOR DE DOCUMENTOS
  // ─────────────────────────────────────────────────────────────────────

  const abrirLista = () => {
    listaDocumentos.classList.add("abierto");
    botonDesplegar.setAttribute("aria-expanded", "true");
  };

  const cerrarLista = () => {
    listaDocumentos.classList.remove("abierto");
    botonDesplegar.setAttribute("aria-expanded", "false");
  };

  botonDesplegar?.addEventListener("click", () => {
    const estaAbierta = listaDocumentos.classList.contains("abierto");
    if (estaAbierta) {
      cerrarLista();
    } else {
      abrirLista();
      actualizarSugerencias();
    }
  });

  listaDocumentos.querySelectorAll(".opcion-documento").forEach((opcion) => {
    opcion.addEventListener("click", () => {
      const docId = opcion.dataset.docId || "";
      if (!docId) return;
      filtroId.value = docId;
      actualizarSugerencias();
      cerrarLista();
      void cargarDocumentoActual(docId);
    });
  });

  filtroId.addEventListener("input", () => {
    actualizarSugerencias();
  });

  document.addEventListener("click", (event) => {
    const estaDentro = contenedor.contains(event.target);
    if (!estaDentro) {
      cerrarLista();
    }
  });

  const valorInicial = filtroId.value || "";
  if (valorInicial) {
    void cargarDocumentoActual(valorInicial);
  }

  void actualizarWatchdog();
  const relojWatchdog = window.setInterval(() => {
    void actualizarWatchdog();
  }, 5000);

  window.addEventListener("beforeunload", () => {
    window.clearInterval(relojWatchdog);
  }, { once: true });

  actualizarSugerencias();

  // ─────────────────────────────────────────────────────────────────────
  // VALIDACIÓN EN TIEMPO REAL
  // ─────────────────────────────────────────────────────────────────────

  const validadores = {
    "campo-dni": { validar: validarDNI, error: "error-dni" },
    "campo-celular": { validar: validarCelular, error: "error-celular" },
    "campo-hc": { validar: validarNumeroHC, error: "error-hc" },
    "campo-fecha": { validar: validarFecha, error: "error-fecha" },
  };

  Object.entries(validadores).forEach(([id, { validar, error }]) => {
    const input = contenedor.querySelector(`#${id}`);
    const errorSpan = contenedor.querySelector(`#${error}`);
    if (!input) return;

    input.addEventListener("blur", () => {
      const res = validar(input.value);
      if (errorSpan) {
        errorSpan.textContent = res.valido ? "" : res.mensaje;
        input.classList.toggle("campo-error", !res.valido);
      }
    });
  });

  // ─────────────────────────────────────────────────────────────────────
  // LECTURA DE DOCUMENTOS
  // ─────────────────────────────────────────────────────────────────────

  const ejecutarLectura = async (archivo, etiqueta) => {
    botonLeer.disabled = true;
    let indexMensajes = 0;
    const mensajesTrabajo = [
      "Estamos trabajando, aguarda un poco más…",
      "La OCR sigue revisando la ficha y validando campos…",
      "Todavía estamos verificando, no te preocupes: va bien…",
    ];
    const mostrarMensajeTrabajo = () => {
      const mensaje = mensajesTrabajo[indexMensajes % mensajesTrabajo.length];
      indexMensajes += 1;
      estadoLectura.innerHTML = `<p class="trabajando">${mensaje}</p>`;
    };
    const relojTrabajo = window.setInterval(mostrarMensajeTrabajo, 3000);
    mostrarMensajeTrabajo();

    try {
      const cuerpo = await leerDocumento(archivo);

      // Mostrar resultado
      const camposHtml = (cuerpo.campos || [])
        .map((c) => {
          const valor = c.valor ?? "—";
          const estado = c.requiere_revision ? "🟠 revisión" : "🟢 validado";
          return `<div class="campo-resultado">
            <strong>${esc(c.nombre)}</strong>: ${esc(valor)}
            <span class="estado-campo">${estado}</span>
          </div>`;
        })
        .join("");

      detallesResultado.innerHTML = `
        <p><strong>Documento:</strong> ${esc(cuerpo.documento_id)}</p>
        <p><strong>Transcriptor:</strong> ${esc(cuerpo.lector)}</p>
        <div class="campos-resultado">${camposHtml || "<p>Sin campos extraídos.</p>"}</div>
      `;
      resultadoOcr.style.display = "block";

      // Rellenar campos automáticamente
      if (cuerpo.campos) {
        const porNombre = Object.fromEntries(
          cuerpo.campos.map((c) => [c.nombre, c.valor])
        );
        if (porNombre.dni) contenedor.querySelector("#campo-dni").value = porNombre.dni;
        if (porNombre.celular) contenedor.querySelector("#campo-celular").value = porNombre.celular;
        if (porNombre.numero_hc) contenedor.querySelector("#campo-hc").value = porNombre.numero_hc;
        if (porNombre.fecha_nacimiento) contenedor.querySelector("#campo-fecha").value = porNombre.fecha_nacimiento;
      }

      formulariocampos.style.display = "block";
      estadoLectura.innerHTML = "";
    } catch (error) {
      estadoLectura.innerHTML = `<p class="error">❌ ${esc(error.message)}</p>`;
    } finally {
      clearInterval(relojTrabajo);
      botonLeer.disabled = false;
    }
  };

  // Botón "Leer documento"
  botonLeer.addEventListener("click", async () => {
    const archivo = inputArchivo.files?.[0];
    if (!archivo) {
      estadoLectura.innerHTML = "<p class='error'>Selecciona un archivo primero.</p>";
      return;
    }
    await ejecutarLectura(archivo, archivo.name);
  });

  // Botón "Confirmar lectura"
  contenedor.querySelector("#boton-confirmar")?.addEventListener("click", () => {
    const revisor = contenedor.querySelector("#campo-revisor").value || "anónimo";
    alert(`Lectura confirmada por: ${revisor}`);
    // Aquí iría la lógica de guardar
  });

  // Botón "Descargar acta"
  contenedor.querySelector("#boton-descargar")?.addEventListener("click", () => {
    alert("Funcionalidad de descarga en desarrollo.");
    // Aquí iría la descarga del PDF
  });
}
