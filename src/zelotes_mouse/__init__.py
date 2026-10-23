"""Controle multiplataforma do mouse Zelotes C-18."""

from zelotes_mouse.cli import main
from zelotes_mouse.device import Endpoint, Mouse, list_endpoints
from zelotes_mouse.protocol import feature, init_link, select_profile, set_polling

__all__ = [
    "Endpoint",
    "Mouse",
    "feature",
    "init_link",
    "list_endpoints",
    "main",
    "select_profile",
    "set_polling",
]

if __name__ == "__main__":
    raise SystemExit(main())
