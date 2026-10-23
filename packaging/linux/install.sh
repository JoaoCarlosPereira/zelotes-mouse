#!/bin/sh
# Copia o binário, os ícones e o atalho. A regra udev pede confirmação gráfica.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
BIN_DIR=${HOME}/.local/bin
APP_DIR=${HOME}/.local/share/applications
ICON_ROOT=${HOME}/.local/share/icons/hicolor
mkdir -p "$BIN_DIR" "$APP_DIR"
install -m 0755 "$ROOT/zelotes-mouse" "$BIN_DIR/zelotes-mouse"
if [ -d "$ROOT/icons" ]; then
    for icon in "$ROOT/icons/"*.png; do
        [ -f "$icon" ] || continue
        size=$(basename "$icon" .png)
        dest="$ICON_ROOT/${size}x${size}/apps"
        mkdir -p "$dest"
        install -m 0644 "$icon" "$dest/zelotes-mouse.png"
    done
fi
ICON="$ICON_ROOT/256x256/apps/zelotes-mouse.png"
cat > "$APP_DIR/zelotes-mouse.desktop" << EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Zelotes C-18
GenericName=Controle do mouse
Comment=Perfil, polling, luz e DPI do Zelotes C-18
Exec=$BIN_DIR/zelotes-mouse
Icon=$ICON
Terminal=false
Categories=Settings;HardwareSettings;
StartupWMClass=zelotes-mouse
EOF
chmod 0644 "$APP_DIR/zelotes-mouse.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$ICON_ROOT" >/dev/null 2>&1 || true
fi
echo "Programa instalado em $BIN_DIR/zelotes-mouse"
if [ -f "$ROOT/60-zelotes-c18.rules" ] && command -v pkexec >/dev/null 2>&1; then
    pkexec sh -c "install -m 0644 '$ROOT/60-zelotes-c18.rules' /etc/udev/rules.d/60-zelotes-c18.rules && udevadm control --reload-rules && udevadm trigger --subsystem-match=usb --subsystem-match=hidraw --attr-match=idVendor=12c9"
    echo "Regra udev instalada. Reconecte o mouse."
fi
