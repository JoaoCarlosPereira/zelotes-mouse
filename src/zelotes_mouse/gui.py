"""API local do C-18. A janela de desktop e outros programas falam com estes caminhos."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from zelotes_mouse.device import (
    Mouse,
    MouseError,
    MouseNotFound,
    MousePermissionError,
    control_endpoints,
)
from zelotes_mouse.protocol import FACTORY_ACTIONS, LIGHT_MODES, POLLING_CODE_BY_HZ, ProtocolError
from zelotes_mouse.service import apply_settings
from zelotes_mouse.settings import SESSION, parse_settings, save_settings

PAGE = (Path(__file__).parent / "ui" / "index.html").read_text(encoding="utf-8")
HOST = "127.0.0.1"


class PanelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path == "/api/status":
            self._json(200, probe())
            return
        if path == "/api/state":
            self._json(200, SESSION.settings.to_dict())
            return
        if path == "/api/capabilities":
            self._json(200, capabilities(self.server.server_address[1]))
            return
        if path in ("/", "/index.html"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(404, {"message": "não encontrado"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path not in ("/api/apply", "/api/state"):
            self._json(404, {"message": "não encontrado"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 16384:
            self._json(400, {"message": "pedido grande demais"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            settings = parse_settings(payload, SESSION.settings)
        except (json.JSONDecodeError, TypeError, ValueError, ProtocolError) as exc:
            self._json(400, {"message": str(exc) or "pedido inválido"})
            return
        if path == "/api/state":
            SESSION.settings = settings
            save_settings(settings)
            self._json(200, settings.to_dict())
            return
        try:
            message = apply_settings(settings)
        except MouseNotFound as exc:
            self._json(404, {"message": str(exc)})
            return
        except MousePermissionError as exc:
            self._json(403, {"message": str(exc)})
            return
        except MouseError as exc:
            self._json(500, {"message": str(exc)})
            return
        SESSION.settings = settings
        save_settings(settings)
        self._json(200, {"message": message, "state": settings.to_dict()})

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def capabilities(port: int) -> dict[str, object]:
    return {
        "nome": "Zelotes C-18",
        "base": f"http://{HOST}:{port}",
        "implementado": ["perfil", "polling", "luz", "cor", "brilho", "velocidade", "dpi"],
        "modos": [{"id": key, "nome": label} for key, label in LIGHT_MODES],
        "polling_hz": list(POLLING_CODE_BY_HZ),
        "ainda_nao_enviado": list(FACTORY_ACTIONS),
        "nota": (
            "POST /api/apply com luz ou dpi grava o bloco de 128 bytes. "
            "Esse bloco leva a cor e os cinco estágios de DPI juntos. "
            "Atribuição de botão e macro usa outro pacote, que este programa ainda não envia."
        ),
    }


def probe() -> dict[str, str]:
    if not control_endpoints():
        return {"state": "absent", "detail": "Nenhum C-18 no USB."}
    try:
        with Mouse():
            pass
    except MousePermissionError as exc:
        return {"state": "denied", "detail": str(exc)}
    except MouseError as exc:
        return {"state": "error", "detail": str(exc)}
    return {"state": "ready", "detail": "Mouse na interface de controle."}


def start_server(port: int = 8765) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((HOST, port), PanelHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def serve(port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((HOST, port), PanelHandler)
    print(f"api em http://{HOST}:{port}/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\napi fechada")
    finally:
        httpd.server_close()
