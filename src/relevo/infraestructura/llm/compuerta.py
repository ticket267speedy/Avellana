"""Compuerta: un interruptor entre el mundo y el Ollama de esta maquina.

EL PROBLEMA
Cuando la aplicacion desplegada apunta al Ollama de un portatil a traves de un
tunel, quien presta el portatil pierde el control de sus propios recursos: si
alguien pulsa "leer en vivo" desde la pagina, la CPU de esa maquina se va dos
minutos al 100% sin que su dueno pueda decir que no.

Apagar el tunel sirve, pero es todo o nada y obliga a repetir el pegado del
secreto, porque un tunel gratuito cambia de URL cada vez que arranca.

LA SOLUCION
Un proxy minusculo delante de Ollama, con un interruptor. El tunel apunta AQUI
en vez de a Ollama:

    Streamlit Cloud ──tunel──► compuerta (8787) ──► Ollama (11434)
                                    ▲
                                    │
                        panel en http://localhost:8787

- **Abierta:** todo pasa a Ollama. La pagina web dice "LLM ACTIVA".
- **Cerrada:** responde 503 sin tocar Ollama. La pagina web dice "LLM NO
  ACTIVA — el servidor del modelo esta caido", que es exactamente lo que se
  quiere que vea, y la CPU del portatil no se entera.

La URL del tunel NO cambia al cerrar y abrir: el tunel sigue en pie, lo que se
mueve es la compuerta. Se puede abrir y cerrar durante una demo sin volver a
tocar los secretos de Streamlit.

Solo libreria estandar: esto tiene que arrancar en cualquier portatil sin
instalar nada.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

PUERTO_POR_DEFECTO = 8787
OLLAMA_POR_DEFECTO = "http://localhost:11434"

# Una lectura con modelo de vision tarda minutos en CPU; el sondeo de estado
# tiene que ser rapido o la pagina se queda colgada esperandolo.
TIMEOUT_LECTURA = 330.0
TIMEOUT_SONDEO = 10.0
RUTAS_RAPIDAS = ("/api/tags", "/api/ps", "/api/version")


class Interruptor:
    """El estado de la compuerta. Se consulta desde varios hilos a la vez."""

    def __init__(self, abierta: bool = True) -> None:
        self._abierta = abierta
        self._candado = threading.Lock()

    @property
    def abierta(self) -> bool:
        with self._candado:
            return self._abierta

    def poner(self, abierta: bool) -> bool:
        with self._candado:
            self._abierta = abierta
            return self._abierta


PAGINA = """<!doctype html>
<meta charset="utf-8">
<title>Compuerta Relevo</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#f7fafc; color:#1a202c;
         display:flex; align-items:center; justify-content:center;
         min-height:100vh; margin:0; }}
  .caja {{ background:#fff; border:1px solid #cbd5e0; border-radius:10px;
           padding:32px 40px; max-width:520px; }}
  h1 {{ font-size:1.15rem; color:#1a365d; margin:0 0 4px; }}
  .sub {{ font-size:0.82rem; color:#4a5568; margin-bottom:22px; }}
  .estado {{ font-size:1.3rem; font-weight:700; padding:14px 18px;
             border-radius:6px; margin-bottom:20px; }}
  .abierta {{ background:#f0fff4; color:#22543d; border-left:6px solid #38a169; }}
  .cerrada {{ background:#fff5f5; color:#9b2c2c; border-left:6px solid #e53e3e; }}
  button {{ font-size:1rem; font-weight:600; padding:13px 26px; border:0;
            border-radius:6px; cursor:pointer; color:#fff; width:100%; }}
  .apagar {{ background:#c53030; }}
  .encender {{ background:#2f855a; }}
  .nota {{ font-size:0.78rem; color:#718096; margin-top:20px; line-height:1.5; }}
  code {{ background:#edf2f7; padding:1px 5px; border-radius:3px; }}
</style>
<div class="caja">
  <h1>Compuerta Relevo</h1>
  <div class="sub">Controla si la pagina web puede usar la LLM de esta maquina.</div>
  <div class="estado {clase}">{titulo}</div>
  <form method="post" action="{accion}">
    <button class="{boton}">{etiqueta}</button>
  </form>
  <div class="nota">
    {explicacion}<br><br>
    Ollama: <code>{ollama}</code> &middot; compuerta en el puerto <code>{puerto}</code>.<br>
    Cerrarla no tumba el tunel: la URL sigue siendo la misma al volver a abrir.
  </div>
</div>
"""


def _pagina(interruptor: Interruptor, ollama: str, puerto: int) -> bytes:
    if interruptor.abierta:
        datos = {
            "clase": "abierta",
            "titulo": "LLM ACTIVA — la pagina web puede usarla",
            "accion": "/apagar",
            "boton": "apagar",
            "etiqueta": "Apagar: dejar de prestar la LLM",
            "explicacion": (
                "Ahora mismo cualquiera que abra la aplicacion desplegada puede "
                "lanzar una lectura y ocupar la CPU de esta maquina un par de "
                "minutos."
            ),
        }
    else:
        datos = {
            "clase": "cerrada",
            "titulo": "LLM APAGADA — la pagina web no la ve",
            "accion": "/encender",
            "boton": "encender",
            "etiqueta": "Encender: prestar la LLM a la pagina",
            "explicacion": (
                "La pagina web muestra «LLM NO ACTIVA» y sigue funcionando con "
                "las transcripciones ya guardadas. Ollama no recibe nada."
            ),
        }
    return PAGINA.format(ollama=ollama, puerto=puerto, **datos).encode("utf-8")


def crear_manejador(
    interruptor: Interruptor, ollama: str, puerto: int
) -> type[BaseHTTPRequestHandler]:
    """Construye el manejador con sus dependencias ya dentro."""

    class Manejador(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, formato: str, *args: Any) -> None:
            estado = "abierta" if interruptor.abierta else "CERRADA"
            print(f"[compuerta {estado}] {self.command} {self.path}")

        # ── Respuestas ────────────────────────────────────────────────
        def _responder(
            self, codigo: int, cuerpo: bytes, tipo: str = "text/html; charset=utf-8"
        ) -> None:
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _redirigir(self) -> None:
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        # ── Rutas ─────────────────────────────────────────────────────
        def do_GET(self) -> None:  # noqa: N802 — lo impone BaseHTTPRequestHandler
            if self.path in ("/", "/index.html"):
                self._responder(200, _pagina(interruptor, ollama, puerto))
                return
            if self.path == "/estado":
                cuerpo = json.dumps({"abierta": interruptor.abierta}).encode()
                self._responder(200, cuerpo, "application/json")
                return
            self._proxy("GET")

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/apagar":
                interruptor.poner(False)
                print("[compuerta] APAGADA a mano desde el panel")
                self._redirigir()
                return
            if self.path == "/encender":
                interruptor.poner(True)
                print("[compuerta] ENCENDIDA a mano desde el panel")
                self._redirigir()
                return
            self._proxy("POST")

        # ── Reenvio a Ollama ──────────────────────────────────────────
        def _proxy(self, metodo: str) -> None:
            if not interruptor.abierta:
                # 503 y no 403: para quien pregunta, esto es un servidor que no
                # esta disponible ahora mismo. Es literalmente cierto, y es lo
                # que hace que la pagina web diga "el servidor esta caido".
                cuerpo = json.dumps(
                    {"error": "compuerta cerrada por el dueno de la maquina"}
                ).encode()
                self._responder(503, cuerpo, "application/json")
                return

            largo = int(self.headers.get("Content-Length") or 0)
            datos = self.rfile.read(largo) if largo else None

            peticion = urllib.request.Request(
                f"{ollama}{self.path}", data=datos, method=metodo
            )
            if self.headers.get("Content-Type"):
                peticion.add_header("Content-Type", self.headers["Content-Type"])

            espera = (
                TIMEOUT_SONDEO
                if self.path.startswith(RUTAS_RAPIDAS)
                else TIMEOUT_LECTURA
            )
            try:
                with urllib.request.urlopen(peticion, timeout=espera) as r:
                    self._responder(
                        r.status,
                        r.read(),
                        r.headers.get("Content-Type", "application/json"),
                    )
            except urllib.error.HTTPError as e:
                self._responder(e.code, e.read(), "application/json")
            except Exception as e:  # noqa: BLE001 — Ollama caido o sin responder
                cuerpo = json.dumps({"error": f"Ollama no responde: {e}"}).encode()
                self._responder(502, cuerpo, "application/json")

    return Manejador


def servir(
    puerto: int = PUERTO_POR_DEFECTO,
    ollama: str = OLLAMA_POR_DEFECTO,
    abierta: bool = True,
) -> None:
    """Levanta la compuerta y se queda escuchando."""
    interruptor = Interruptor(abierta=abierta)
    # ThreadingHTTPServer y no el simple: una lectura ocupa un hilo dos minutos,
    # y mientras tanto el sondeo de estado de la pagina tiene que seguir
    # contestando o la interfaz declara el modelo caido por congestion propia.
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), crear_manejador(
        interruptor, ollama, puerto
    ))
    print(f"Compuerta en http://localhost:{puerto}  ->  {ollama}")
    print(f"Estado inicial: {'ABIERTA' if abierta else 'CERRADA'}")
    print("Abre esa direccion en el navegador para encender y apagar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCompuerta cerrada.")
        servidor.shutdown()
