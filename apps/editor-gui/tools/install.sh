#!/bin/sh
set -eu
# XKNX-Editor Linux installer (user-local, no root). Run it from the extracted
# "XKNX-Editor" folder. It copies the app under ~/.local/share, installs the icon
# into the hicolor theme and writes a .desktop launcher, so the app appears in the
# application menu with its icon. A Linux ELF binary cannot embed an icon the way a
# Windows .exe or a macOS .app bundle can, so the launcher + themed icon are the
# only way the desktop environment shows one.

SRC="$(cd "$(dirname "$0")" && pwd)"

# The installer must sit next to the app files. If only the script was extracted
# (e.g. opened straight from an archive viewer), the copy below would do nothing.
if [ ! -x "$SRC/XKNX-Editor" ]; then
  echo "FEHLER: XKNX-Editor wurde neben dieser install.sh nicht gefunden." >&2
  echo "Bitte das Archiv zuerst vollstaendig entpacken und install.sh aus dem" >&2
  echo "entpackten Ordner starten." >&2
  exit 1
fi

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/xknx-editor"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/512x512/apps"
DESKTOP_FILE="$DESKTOP_DIR/xknx-editor.desktop"

echo ""
echo "XKNX-Editor wird installiert nach:"
echo "  $APP_DIR"
echo ""

# Replace any previous install so stale files do not linger.
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR" "$DESKTOP_DIR" "$ICON_DIR"
cp -a "$SRC/." "$APP_DIR/"
# The installer artefacts themselves do not belong in the installed app folder.
rm -f "$APP_DIR/install.sh" "$APP_DIR/uninstall.sh"
chmod +x "$APP_DIR/XKNX-Editor"

# Use the app's own bundled icon rather than shipping a loose PNG next to the binary (users kept
# clicking that PNG instead of running the app or this installer).
ICON_SRC="$SRC/_internal/editor_gui/assets/app_settings/icon.png"
if [ -f "$ICON_SRC" ]; then
  cp -f "$ICON_SRC" "$ICON_DIR/xknx-editor.png"
else
  echo "WARNUNG: App-Icon nicht gefunden; der Starter wird ohne eigenes Icon angelegt." >&2
fi

# Icon is referenced by theme name (not path) so the environment can pick a size.
# StartupWMClass lets the window manager group the running window under this entry
# and show its icon; it must match the app's X11 WM_CLASS / Wayland app_id.
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=XKNX Editor
Comment=KNX project editor
Exec=$APP_DIR/XKNX-Editor
Icon=xknx-editor
Terminal=false
Categories=Utility;Development;
StartupWMClass=XKNX-Editor
EOF
chmod 644 "$DESKTOP_FILE"

# Refresh the desktop/icon caches when the tools are available (best-effort).
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true

echo "Fertig. XKNX-Editor erscheint jetzt im Anwendungsmenue."
echo "Diesen entpackten Ordner koennen Sie loeschen."
echo ""
echo "Zum Deinstallieren uninstall.sh ausfuehren."
