"""Estado que a janela e a API local compartilham."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from zelotes_mouse.protocol import LIGHT_MODES, POLLING_CODE_BY_HZ, ProtocolError, light_block

DEFAULT_DPI = (15, 25, 40, 70, 100)
DEFAULT_BUTTONS = (
    "Clique",
    "Menu",
    "Clique da roda",
    "Avançar",
    "Voltar",
    "Ciclo de DPI",
    "W",
    "S",
    "A",
    "D",
    "Espaço",
)


@dataclass
class Settings:
    perfil: int = 1
    hz: int = 1000
    modo: str = "padrao"
    nivel: int = 1
    brilho: int = 10
    velocidade: int = 10
    cor: str = "#ff0000"
    dpi: tuple[int, int, int, int, int] = DEFAULT_DPI
    gravar_luz: bool = False
    nome: str = ""
    botoes: tuple[str, ...] = DEFAULT_BUTTONS
    correlacao: bool = False
    programa: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "perfil": self.perfil,
            "nome": self.nome,
            "hz": self.hz,
            "luz": {
                "modo": self.modo,
                "nivel": self.nivel,
                "brilho": self.brilho,
                "velocidade": self.velocidade,
                "cor": self.cor,
            },
            "dpi": list(self.dpi),
            "gravar_luz": self.gravar_luz,
            "botoes": list(self.botoes),
            "correlacao": self.correlacao,
            "programa": self.programa,
        }

    def light_bytes(self) -> bytes:
        return light_block(
            self.modo,
            self.nivel,
            self.brilho,
            self.velocidade,
            parse_color(self.cor),
            self.dpi,
        )


def parse_settings(payload: object, base: Settings | None = None, *, remember: bool = False) -> Settings:
    """Lê o JSON da API. Campos ausentes ficam com o valor já guardado."""
    if not isinstance(payload, dict):
        raise ProtocolError("o pedido precisa ser um objeto JSON")
    current = base or Settings()
    perfil = _int_field(payload, "perfil", current.perfil)
    hz = _int_field(payload, "hz", current.hz)
    if not 1 <= perfil <= 8:
        raise ProtocolError("perfil vai de 1 a 8")
    if hz not in POLLING_CODE_BY_HZ:
        options = ", ".join(str(item) for item in POLLING_CODE_BY_HZ)
        raise ProtocolError(f"polling deve ser um destes Hz: {options}")

    luz = payload.get("luz", {})
    if luz is None:
        luz = {}
    if not isinstance(luz, dict):
        raise ProtocolError("luz precisa ser um objeto")
    modo = str(luz.get("modo", current.modo))
    if modo not in {key for key, _label in LIGHT_MODES}:
        names = ", ".join(key for key, _label in LIGHT_MODES)
        raise ProtocolError(f"modo de luz desconhecido. Use um destes: {names}")
    nivel = _int_field(luz, "nivel", current.nivel)
    brilho = _int_field(luz, "brilho", current.brilho)
    velocidade = _int_field(luz, "velocidade", current.velocidade)
    cor = str(luz.get("cor", current.cor))
    parse_color(cor)

    dpi_raw = payload.get("dpi", list(current.dpi))
    if not isinstance(dpi_raw, list) or len(dpi_raw) != 5:
        raise ProtocolError("dpi precisa ser uma lista com cinco estágios")
    dpi = tuple(_plain_int(item, "estágio de DPI") for item in dpi_raw)
    # Só este pedido decide se o bloco de 128 bytes sai no USB.
    # Um POST só com perfil e polling não regrava luz nem DPI.
    asked = payload.get("gravar_luz")
    if remember:
        gravar = asked is True
    else:
        gravar = "luz" in payload or "dpi" in payload or asked is True
    nome = str(payload.get("nome", current.nome))
    programa = str(payload.get("programa", current.programa))
    correlacao = current.correlacao if "correlacao" not in payload else payload.get("correlacao") is True
    settings = Settings(
        perfil=perfil,
        hz=hz,
        modo=modo,
        nivel=nivel,
        brilho=brilho,
        velocidade=velocidade,
        cor=cor.lower(),
        dpi=dpi,  # type: ignore[arg-type]
        gravar_luz=gravar,
        nome=nome,
        botoes=_buttons(payload, current.botoes),
        correlacao=correlacao,
        programa=programa,
    )
    if gravar:
        settings.light_bytes()
    return settings


def parse_color(text: str) -> tuple[int, int, int]:
    raw = text.strip().lstrip("#")
    if len(raw) != 6:
        raise ProtocolError("cor precisa ser #RRGGBB")
    try:
        value = int(raw, 16)
    except ValueError as exc:
        raise ProtocolError("cor precisa ser #RRGGBB") from exc
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF


def config_path() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(root) if root else Path.home() / ".config"
    return base / "zelotes-mouse" / "state.json"


@dataclass
class Library:
    """Os dois perfis que a tela de fábrica mostra ao mesmo tempo."""

    active: int = 1
    slots: dict[int, Settings] = field(default_factory=dict)
    macros: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.slots.setdefault(1, Settings(perfil=1, nome="Padrão 1"))
        self.slots.setdefault(2, Settings(perfil=2, nome="Padrão 2"))
        if self.active not in (1, 2):
            self.active = 1

    def current(self) -> Settings:
        return self.slots[self.active]


def load_library() -> Library:
    path = config_path()
    if not path.is_file():
        return Library()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Library()
    if not isinstance(payload, dict):
        return Library()
    if "perfis" not in payload:
        try:
            one = parse_settings(payload, remember=True)
        except ProtocolError:
            return Library()
        library = Library(active=1 if one.perfil not in (1, 2) else one.perfil)
        library.slots[library.active] = one
        return library
    library = Library(active=_plain_active(payload.get("ativo", 1)))
    raw_slots = payload.get("perfis")
    if isinstance(raw_slots, list):
        for item in raw_slots:
            try:
                settings = parse_settings(item, remember=True)
            except ProtocolError:
                continue
            if settings.perfil in (1, 2):
                library.slots[settings.perfil] = settings
    macros = payload.get("macros", [])
    if isinstance(macros, list):
        library.macros = [str(item) for item in macros if str(item).strip()]
    return library


def save_library(library: Library) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ativo": library.active,
        "perfis": [library.slots[1].to_dict(), library.slots[2].to_dict()],
        "macros": library.macros,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings() -> Settings:
    return load_library().current()


def save_settings(settings: Settings) -> None:
    library = load_library()
    perfil = settings.perfil if settings.perfil in (1, 2) else library.active
    settings.perfil = perfil
    library.slots[perfil] = settings
    library.active = perfil
    save_library(library)


def _plain_active(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value in (1, 2):
        return value
    return 1


def _buttons(payload: dict[str, object], current: tuple[str, ...]) -> tuple[str, ...]:
    if "botoes" not in payload:
        return current
    raw = payload["botoes"]
    if not isinstance(raw, list) or len(raw) != 11:
        raise ProtocolError("botoes precisa ser uma lista com onze nomes")
    names: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ProtocolError("cada botão precisa de um nome")
        names.append(item.strip()[:40])
    return tuple(names)


def _int_field(payload: dict[str, object], key: str, default: int) -> int:
    if key not in payload:
        return default
    return _plain_int(payload[key], key)


def _plain_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError(f"{name} precisa ser um número inteiro")
    return value


@dataclass
class Session:
    settings: Settings = field(default_factory=load_settings)


SESSION = Session()
