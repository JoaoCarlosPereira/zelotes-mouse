"""Atalho que coloca o C-18 na grade e permite fixar na barra de aplicativos."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "zelotes-mouse"
ICON_SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)


def _program_path() -> Path:
    argv = Path(sys.argv[0])
    if argv.name == "zelotes-mouse" and argv.is_file():
        return argv.resolve()
    candidates = [
        Path(sys.prefix) / "bin" / "zelotes-mouse",
        Path(__file__).resolve().parents[2] / ".venv" / "bin" / "zelotes-mouse",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return Path(sys.executable).resolve()


def icon_file(size: int = 256) -> Path:
    return Path(__file__).resolve().parent / "ui" / "icons" / f"{size}.png"


def install_launcher() -> Path:
    """Grava o atalho e os ícones que a barra e a grade usam."""
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    hicolor = Path.home() / ".local" / "share" / "icons" / "hicolor"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    stale = hicolor / "scalable" / "apps" / f"{APP_ID}.svg"
    if stale.is_file():
        stale.unlink()
    for size in ICON_SIZES:
        source = icon_file(size)
        if not source.is_file():
            continue
        destination = hicolor / f"{size}x{size}" / "apps"
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination / f"{APP_ID}.png")
    program = _program_path()
    installed = hicolor / "256x256" / "apps" / f"{APP_ID}.png"
    entry = desktop_dir / f"{APP_ID}.desktop"
    entry.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Version=1.0",
                "Name=Zelotes C-18",
                "GenericName=Controle do mouse",
                "Comment=Perfil, polling, luz e DPI do Zelotes C-18",
                f"Exec={program}",
                f"Icon={installed}",
                "Terminal=false",
                "Categories=Settings;HardwareSettings;",
                f"StartupWMClass={APP_ID}",
                "DBusActivatable=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    os.chmod(entry, 0o644)
    updater = shutil.which("update-desktop-database")
    if updater:
        subprocess.run([updater, str(desktop_dir)], check=False, capture_output=True)
    cache = shutil.which("gtk-update-icon-cache")
    if cache:
        subprocess.run([cache, "-f", "-t", str(hicolor)], check=False, capture_output=True)
    return entry


def autostart_path() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(root) if root else Path.home() / ".config"
    return base / "autostart" / f"{APP_ID}.desktop"


def set_autostart(enabled: bool) -> None:
    """Cria ou remove o atalho que a sessão gráfica abre no login."""
    path = autostart_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    program = _program_path()
    installed = Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_ID}.png"
    icon = installed if installed.is_file() else icon_file(256)
    path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Version=1.0",
                "Name=Zelotes C-18",
                "Comment=Perfil, polling, luz e DPI do Zelotes C-18",
                f"Exec={program}",
                f"Icon={icon}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o644)
