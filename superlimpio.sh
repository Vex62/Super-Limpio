#!/bin/sh
# Abre Super Limpio en Linux con el Python del sistema (3.10 o posterior, con tkinter).
#
#   ./superlimpio.sh              abre la aplicación
#   ./superlimpio.sh --instalar   añade «Super Limpio» al menú de aplicaciones de tu usuario
#   ./superlimpio.sh --quitar     lo quita del menú
#
# No instala nada en el sistema ni necesita permisos de administrador.

set -e
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENTRY="${XDG_DATA_HOME:-$HOME/.local/share}/applications/superlimpio.desktop"

PYTHON=
for candidate in python3 python3.13 python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PYTHON=$candidate
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Super Limpio necesita Python 3.10 o posterior." >&2
    echo "  Debian/Ubuntu:  sudo apt install python3 python3-tk" >&2
    echo "  Fedora:         sudo dnf install python3 python3-tkinter" >&2
    echo "  Arch:           sudo pacman -S python tk" >&2
    exit 1
fi

if ! "$PYTHON" -c 'import tkinter' 2>/dev/null; then
    echo "Falta tkinter, la parte de Python que dibuja las ventanas." >&2
    echo "  Debian/Ubuntu:  sudo apt install python3-tk" >&2
    echo "  Fedora:         sudo dnf install python3-tkinter" >&2
    echo "  Arch:           sudo pacman -S tk" >&2
    exit 1
fi

case "${1:-}" in
    --instalar|--install)
        mkdir -p "$(dirname -- "$ENTRY")"
        cat > "$ENTRY" <<EOF
[Desktop Entry]
Type=Application
Name=Super Limpio
Comment=Analizador y limpiador de espacio y memoria
Comment[en]=Disk space and memory analyzer and cleaner
Exec="$HERE/superlimpio.sh"
Icon=$HERE/app/superlimpio/ui/assets/logo-60.png
Terminal=false
Categories=System;Utility;
StartupWMClass=SuperLimpio
EOF
        echo "Añadido al menú de aplicaciones: $ENTRY"
        exit 0
        ;;
    --quitar|--uninstall)
        rm -f -- "$ENTRY"
        echo "Quitado del menú de aplicaciones."
        exit 0
        ;;
esac

# -I: modo aislado, igual que en Windows: ignora PYTHONPATH y los paquetes del usuario.
exec "$PYTHON" -I "$HERE/app/main.py" "$@"
