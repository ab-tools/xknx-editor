#!/bin/sh
set -eu
# XKNX-Editor Linux uninstaller: removes the user-local install, the themed icon
# and the launcher that install.sh created.

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/xknx-editor"
DESKTOP_FILE="$DATA_HOME/applications/xknx-editor.desktop"
ICON_FILE="$DATA_HOME/icons/hicolor/512x512/apps/xknx-editor.png"

rm -rf "$APP_DIR"
rm -f "$DESKTOP_FILE" "$ICON_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true

echo "XKNX-Editor wurde entfernt."
