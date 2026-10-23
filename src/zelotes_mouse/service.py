"""Envia ao mouse a mesma ordem curta do Monitor.exe, e o bloco de luz quando pedido."""

from __future__ import annotations

import time

from zelotes_mouse.device import Mouse
from zelotes_mouse.protocol import OP_LIGHT, settings_packets
from zelotes_mouse.settings import Settings


def apply_settings(settings: Settings) -> str:
    profile = settings.perfil - 1
    with Mouse() as mouse:
        for packet in settings_packets(profile, settings.hz):
            mouse.send_feature(packet)
            time.sleep(0.01)
        if settings.gravar_luz:
            mouse.upload(OP_LIGHT, profile, settings.light_bytes())
    if settings.gravar_luz:
        return (
            f"Perfil {settings.perfil} gravado: {settings.hz} Hz, "
            f"luz {settings.modo}, DPI {', '.join(str(item) for item in settings.dpi)}."
        )
    return f"Perfil {settings.perfil} a {settings.hz} Hz enviado."
