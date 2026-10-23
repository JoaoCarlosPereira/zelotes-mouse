"""Textos da janela. O idioma escolhido não muda o protocolo do mouse."""

from __future__ import annotations

LANGS = ("pt-BR", "en")

MODE_IDS = ("desligado", "padrao", "respiracao", "neon", "onda", "fluxo", "espectro")
DEFAULT_BUTTON_IDS = ("click", "menu", "wheel", "forward", "back", "dpi", "w", "s", "a", "d", "space")
ASSIGNMENT_IDS = (
    "click",
    "menu",
    "wheel",
    "double",
    "off",
    "forward",
    "back",
    "scroll_up",
    "scroll_down",
    "dpi",
    "dpi_up",
    "dpi_down",
    "macro",
    "profile",
    "fire",
    "led",
    "w",
    "a",
    "s",
    "d",
    "space",
    "volume_up",
    "volume_down",
    "mute",
    "play",
    "copy",
    "paste",
    "undo",
)

_UI = {
    "pt-BR": {
        "badge": "DRIVER DO MOUSE",
        "tab.buttons": "Botões",
        "tab.performance": "Desempenho",
        "tab.lighting": "Iluminação",
        "tab.macros": "Macros",
        "tab.settings": "Configuração",
        "rate": "Taxa de resposta",
        "mode": "Modo",
        "color": "Selecione a cor da luz:",
        "brightness": "Brilho",
        "speed": "Velocidade",
        "macros": "Gerenciador de macros",
        "macro.select": "Selecionar macro",
        "macro.record": "Gravar antes",
        "macro.delay": "Inserir atraso",
        "macro.click": "Inserir clique",
        "macro.delete": "Excluir",
        "macro.item.select": "Macro {n}",
        "macro.item.record": "Macro {n}: gravação",
        "macro.item.delay": "Macro {n}: atraso",
        "macro.item.click": "Macro {n}: clique",
        "profile": "Perfil {n}",
        "profile.default": "Padrão {n}",
        "description": "Descrição da\nconfiguração",
        "correlation": "Programa associado",
        "export": "Exportar configuração",
        "import": "Importar configuração",
        "restore": "Restaurar\npadrão",
        "apply": "Aplicar",
        "driver": "Versão do driver: 1.0   www.zelotes.cn",
        "dedication": 'By <a href="https://github.com/JoaoCarlosPereira">João Carlos Pereira</a>',
        "settings.language": "Idioma",
        "settings.autostart": "Iniciar com o sistema",
        "settings.autostart_hint": "Abre o Zelotes quando você entra na sessão.",
        "status.applied_light": "Perfil {perfil} gravado: {hz} Hz, luz {modo}, DPI {dpi}.",
        "status.applied": "Perfil {perfil} a {hz} Hz enviado.",
        "status.local_only": "Botões e macros ficam salvos na janela.",
        "status.factory": "Valores de fábrica deste perfil, ainda sem gravar no mouse.",
        "status.port": "A porta {port} já está em uso.",
        "status.dpi": "DPI precisa ser um número de 0 a 100",
        "status.language": "Idioma salvo nesta janela.",
        "status.autostart_on": "O Zelotes vai abrir junto com a sessão.",
        "status.autostart_off": "O Zelotes não abre mais com a sessão.",
        "tray.open": "Abrir",
        "tray.quit": "Sair",
        "mode.desligado": "LED ligado/desligado",
        "mode.padrao": "Padrão",
        "mode.respiracao": "Respiração",
        "mode.neon": "Neon",
        "mode.onda": "Onda",
        "mode.fluxo": "Fluxo",
        "mode.espectro": "Modo 2",
    },
    "en": {
        "badge": "GAMING MOUSE DRIVER",
        "tab.buttons": "Buttons",
        "tab.performance": "Performance",
        "tab.lighting": "Lighting",
        "tab.macros": "Macros",
        "tab.settings": "Settings",
        "rate": "Report rate",
        "mode": "Mode",
        "color": "Select the color of the light:",
        "brightness": "Brightness",
        "speed": "Speed",
        "macros": "Macro manager",
        "macro.select": "Select a macro",
        "macro.record": "Start record",
        "macro.delay": "Insert delay",
        "macro.click": "Insert click",
        "macro.delete": "Delete",
        "macro.item.select": "Macro {n}",
        "macro.item.record": "Macro {n}: record",
        "macro.item.delay": "Macro {n}: delay",
        "macro.item.click": "Macro {n}: click",
        "profile": "Profile {n}",
        "profile.default": "Default {n}",
        "description": "Configuration\nfile description",
        "correlation": "Correlation program",
        "export": "Export configuration",
        "import": "Import configuration",
        "restore": "Restore\nthe default",
        "apply": "Apply",
        "driver": "Driver Ver: 1.0   www.zelotes.cn",
        "dedication": 'By <a href="https://github.com/JoaoCarlosPereira">João Carlos Pereira</a>',
        "settings.language": "Language",
        "settings.autostart": "Start with the system",
        "settings.autostart_hint": "Opens Zelotes when you sign in.",
        "status.applied_light": "Profile {perfil} saved: {hz} Hz, light {modo}, DPI {dpi}.",
        "status.applied": "Profile {perfil} sent at {hz} Hz.",
        "status.local_only": "Buttons and macros stay saved in the window.",
        "status.factory": "Factory values for this profile, not written to the mouse yet.",
        "status.port": "Port {port} is already in use.",
        "status.dpi": "DPI must be a number from 0 to 100",
        "status.language": "Language saved in this window.",
        "status.autostart_on": "Zelotes will open with the session.",
        "status.autostart_off": "Zelotes will no longer open with the session.",
        "tray.open": "Open",
        "tray.quit": "Quit",
        "mode.desligado": "LED On/Off",
        "mode.padrao": "Standard",
        "mode.respiracao": "Cycle breathing",
        "mode.neon": "Neon",
        "mode.onda": "Wave",
        "mode.fluxo": "Flowing",
        "mode.espectro": "Mode 2",
    },
}

_ASSIGNMENT = {
    "pt-BR": {
        "click": "Clique",
        "menu": "Menu",
        "wheel": "Clique da roda",
        "double": "Clique duplo",
        "off": "Botão desligado",
        "forward": "Avançar",
        "back": "Voltar",
        "scroll_up": "Rolar para cima",
        "scroll_down": "Rolar para baixo",
        "dpi": "Ciclo de DPI",
        "dpi_up": "DPI acima",
        "dpi_down": "DPI abaixo",
        "macro": "Atribuir macro",
        "profile": "Trocar perfil",
        "fire": "Botão de disparo",
        "led": "LED ligado/desligado",
        "w": "W",
        "a": "A",
        "s": "S",
        "d": "D",
        "space": "Espaço",
        "volume_up": "Aumentar volume",
        "volume_down": "Diminuir volume",
        "mute": "Mudo",
        "play": "Reproduzir/pausar",
        "copy": "Copiar",
        "paste": "Colar",
        "undo": "Desfazer",
    },
    "en": {
        "click": "Click",
        "menu": "Menu",
        "wheel": "Wheel click",
        "double": "Double-click",
        "off": "Button off",
        "forward": "IE Forward",
        "back": "IE Backward",
        "scroll_up": "Scroll up",
        "scroll_down": "Scroll down",
        "dpi": "DPI Cycle",
        "dpi_up": "DPI Up",
        "dpi_down": "DPI Down",
        "macro": "Assign Macro",
        "profile": "Profile switch",
        "fire": "Fire button",
        "led": "LED On/Off",
        "w": "W",
        "a": "A",
        "s": "S",
        "d": "D",
        "space": "Space",
        "volume_up": "Volume Up",
        "volume_down": "Volume Down",
        "mute": "Mute",
        "play": "Play/Pause",
        "copy": "Copy",
        "paste": "Paste",
        "undo": "Undo",
    },
}

_ASSIGNMENT_OF = {
    label.casefold(): key
    for table in _ASSIGNMENT.values()
    for key, label in table.items()
}


def normalize_lang(lang: str) -> str:
    return lang if lang in _UI else "pt-BR"


def tr(lang: str, key: str) -> str:
    table = _UI[normalize_lang(lang)]
    if key in table:
        return table[key]
    return _UI["pt-BR"].get(key, key)


def assignment_label(lang: str, name: str) -> str:
    """Traduz um id ou um nome conhecido. Texto livre permanece como foi gravado."""
    table = _ASSIGNMENT[normalize_lang(lang)]
    if name in table:
        return table[name]
    key = _ASSIGNMENT_OF.get(name.casefold())
    if key is None:
        return name
    return table[key]


def profile_name(lang: str, name: str, number: int) -> str:
    for code in LANGS:
        if name == tr(code, "profile.default").format(n=number):
            return tr(lang, "profile.default").format(n=number)
    return name
