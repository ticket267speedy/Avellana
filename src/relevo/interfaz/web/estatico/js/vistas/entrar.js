// Vista 1 · Acceso al sistema e inicio de sesion institucional.
//
// Autenticacion institucional real (§8.3): hash argon2id, sesion en cookie
// HttpOnly / SameSite=Strict y registro en la cadena de hash de auditoria.

import { fijarRol, fijarPaciente } from "../estado.js";
import { ir } from "../enrutador.js";
import { login } from "../api.js";

const ROLES = [
  {
    codigo: "paciente",
    usuario: "paciente_mateo",
    password: "mateo18",
    nombre: "Paciente (Mateo)",
    descripcion:
      "Ve su recorrido en lenguaje llano, su Pasaporte y sus lecciones de Entrenate.",
    ruta: "/paciente",
    paciente_id: "DEMO-0001",
  },
  {
    codigo: "apoderado",
    usuario: "apoderado_rosa",
    password: "rosa18",
    nombre: "Apoderado (Rosa Quispe)",
    descripcion:
      "La misma vista del paciente, con permisos recortados y aviso de caducidad a los 18.",
    ruta: "/paciente",
    paciente_id: "DEMO-0001",
  },
  {
    codigo: "profesional_insn",
    usuario: "dra_valdez",
    password: "insn2026",
    nombre: "Profesional del INSN",
    descripcion:
      "Radar de la cohorte con metrica de corte etario y seguimiento clinico.",
    ruta: "/insn/radar",
  },
  {
    codigo: "profesional_receptor",
    usuario: "dr_mendoza",
    password: "dosdemayo2026",
    nombre: "Profesional Receptor (Dos de Mayo)",
    descripcion:
      "Bandeja de referencias entrantes para el Hospital Nacional Dos de Mayo.",
    ruta: "/receptor/bandeja",
    establecimiento: "Hospital Nacional Dos de Mayo",
  },
  {
    codigo: "administrador",
    usuario: "admin",
    password: "admin2026",
    nombre: "Administrador Tecnico",
    descripcion:
      "Mantenimiento, siembra de datos, auditoria y consola de operaciones.",
    ruta: "/insn/radar",
  },
];

export async function render() {
  const tarjetas = ROLES.map(
    (r) => `
      <button type="button" class="tarjeta-rol" data-usuario="${r.usuario}"
              data-password="${r.password}" data-rol="${r.codigo}"
              data-ruta="${r.ruta}" data-establecimiento="${r.establecimiento || ""}"
              data-paciente="${r.paciente_id || ""}">
        <span class="rol-nombre">${r.nombre}</span>
        <span class="rol-descripcion">${r.descripcion}</span>
      </button>`
  ).join("");

  return `
    <section class="entrar">
      <h1>Portal de Acceso Institucional</h1>
      <p class="entrar-intro">
        Relevo acompaña la transición del hospital pediátrico al de adultos.
        El INSN San Borja <strong>no atiende a mayores de 18 años bajo ninguna
        circunstancia</strong>: el corte es duro y en fecha exacta.
      </p>

      <form id="login-form" class="login-form" autocomplete="off">
        <label>
          <span>Usuario</span>
          <input id="login-usuario" name="usuario" type="text" placeholder="usuario" required />
        </label>
        <label>
          <span>Contraseña</span>
          <input id="login-password" name="password" type="password" placeholder="contraseña" required />
        </label>
        <button type="submit" class="boton-principal">Iniciar sesión</button>
      </form>
      <p id="login-error" class="login-error" hidden></p>

      <div class="rejilla-roles">
        <p class="rejilla-titulo">Acceso rápido de demostración</p>
        ${tarjetas}
      </div>

      <p class="aviso-sin-auth" style="background:#edf2f7;color:#2d3748;border-left:4px solid #3182ce;">
        <strong>Autenticación activa (§8.3):</strong> credenciales verificadas con
        <strong>argon2id</strong>, cookie de sesión de servidor <code>HttpOnly</code> /
        <code>SameSite=Strict</code> y trazabilidad en la cadena de auditoría.
      </p>
    </section>`;
}

export function enganchar(contenedor) {
  const formulario = contenedor.querySelector("#login-form");
  const error = contenedor.querySelector("#login-error");

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const usuario = formulario.querySelector("#login-usuario").value.trim();
    const password = formulario.querySelector("#login-password").value;

    error.hidden = true;
    error.textContent = "";

    try {
      const sesion = await login(usuario, password);
      const rol = sesion.rol;
      const establecimiento = sesion.establecimiento || "";
      fijarRol(rol, establecimiento);
      fijarPaciente(sesion.id_paciente || "DEMO-0001");

      const rolDestino = ROLES.find((r) => r.codigo === rol);
      ir(rolDestino ? rolDestino.ruta : "/entrar");
    } catch (err) {
      const detalle = err && err.message ? err.message : "No se pudo iniciar sesión.";
      error.textContent = detalle;
      error.hidden = false;
    }
  });

  contenedor.querySelectorAll(".tarjeta-rol").forEach((boton) => {
    boton.addEventListener("click", () => {
      const usuario = boton.dataset.usuario;
      const password = boton.dataset.password;
      const inputUsuario = formulario.querySelector("#login-usuario");
      const inputPassword = formulario.querySelector("#login-password");

      inputUsuario.value = usuario;
      inputPassword.value = password;
      inputPassword.focus();
      error.hidden = true;
      error.textContent = "";
    });
  });
}
