"""Idioma da janela e abertura junto com a sessão."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zelotes_mouse.i18n import normalize_lang
from zelotes_mouse.launcher import set_autostart
from zelotes_mouse.settings import config_path


@dataclass
class Preferences:
    idioma: str = "pt-BR"
    iniciar_com_sistema: bool = False
    marcadores: dict[int, tuple[float, float]] | None = None


def preferences_path():
    return config_path().parent / "preferences.json"


def load_preferences() -> Preferences:
    path = preferences_path()
    if not path.is_file():
        return Preferences()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Preferences()
    if not isinstance(payload, dict):
        return Preferences()
    return Preferences(
        idioma=normalize_lang(str(payload.get("idioma", "pt-BR"))),
        iniciar_com_sistema=payload.get("iniciar_com_sistema") is True,
        marcadores=_marks(payload.get("marcadores")),
    )


def save_preferences(preferences: Preferences) -> None:
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "idioma": normalize_lang(preferences.idioma),
        "iniciar_com_sistema": preferences.iniciar_com_sistema,
    }
    if preferences.marcadores:
        payload["marcadores"] = {
            str(number): [round(x, 4), round(y, 4)] for number, (x, y) in sorted(preferences.marcadores.items())
        }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    set_autostart(preferences.iniciar_com_sistema)


def _marks(raw: object) -> dict[int, tuple[float, float]] | None:
    if not isinstance(raw, dict):
        return None
    marks: dict[int, tuple[float, float]] = {}
    for key, value in raw.items():
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        if number not in range(1, 12) or not isinstance(value, list) or len(value) != 2:
            continue
        try:
            x, y = float(value[0]), float(value[1])
        except (TypeError, ValueError):
            continue
        if 0 <= x <= 1 and 0 <= y <= 1:
            marks[number] = (x, y)
    return marks or None
