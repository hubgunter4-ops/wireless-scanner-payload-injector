#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHON_USER_BIN="${PYTHON_USER_BIN:-$HOME/.local/bin}"
DRY_RUN=0
INSTALL_SYSTEM_TOOLS=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --install-system-tools) INSTALL_SYSTEM_TOOLS=1 ;;
    -h|--help)
      printf '%s\n' 'Uso: ./install.sh [--dry-run] [--install-system-tools]' 'Instala el paquete para el usuario actual, sin crear ni activar un entorno virtual, y verifica el entrypoint wireless-injector.' 'Sin --install-system-tools no instala ninguna herramienta del sistema; solo advierte qué falta (airmon-ng, airodump-ng, aireplay-ng, aircrack-ng, hostapd, dnsmasq, mitmproxy, iptables).' 'Con --install-system-tools instala los paquetes apt reales (aircrack-ng, hostapd, dnsmasq, mitmproxy, iptables) con apt-get update + apt-get install -y, con sudo si no se es root.'
      exit 0 ;;
    *) printf 'Error: opción desconocida: %s\n' "$arg" >&2; exit 2 ;;
  esac
done
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Error: no se encontró $PYTHON_BIN" >&2; exit 2; }
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else "Se requiere Python >= 3.10")'
# Chequeo de dependencias del sistema, sin instalar nada por defecto.
# Se usa el CLI en modo --check-only (no crea directorios, no activa radio).
check_deps() {
  PYTHONPATH="$ROOT_DIR/src" "$PYTHON_BIN" -m wireless_tool.cli --check-only --json
}
if (( DRY_RUN )); then
  printf '%s\n' "[DRY-RUN] $PYTHON_BIN -m pip install --user -e $ROOT_DIR" "[DRY-RUN] $PYTHON_USER_BIN/wireless-injector --help"
  if (( INSTALL_SYSTEM_TOOLS )); then
    printf '%s\n' "[DRY-RUN] PYTHONPATH=$ROOT_DIR/src $PYTHON_BIN -m wireless_tool.cli --check-only --install-missing --dry-run"
  else
    printf '%s\n' "[DRY-RUN] Sin --install-system-tools no se instala ninguna herramienta del sistema; solo se advertiría qué falta con: PYTHONPATH=$ROOT_DIR/src $PYTHON_BIN -m wireless_tool.cli --check-only --json"
  fi
  exit 0
fi
"$PYTHON_BIN" -m pip install --user -e "$ROOT_DIR"
if command -v "wireless-injector" >/dev/null 2>&1; then
  "wireless-injector" --help >/dev/null
elif [[ -x "$PYTHON_USER_BIN/wireless-injector" ]]; then
  "$PYTHON_USER_BIN/wireless-injector" --help >/dev/null
else
  echo "Error: no se encontró el entrypoint wireless-injector; añade $PYTHON_USER_BIN al PATH o define PYTHON_USER_BIN." >&2
  exit 1
fi
printf '%s\n' 'Instalación completada sin venv.' "Entry point verificado: wireless-injector" "Si es necesario: export PATH=\"$PYTHON_USER_BIN:$PATH\""
if (( INSTALL_SYSTEM_TOOLS )); then
  echo "Instalando herramientas del sistema que falten (apt-get)..."
  PYTHONPATH="$ROOT_DIR/src" "$PYTHON_BIN" -m wireless_tool.cli --check-only --install-missing --json
else
  echo "Comprobando herramientas del sistema (sin instalar nada)..."
  deps_json="$(check_deps)"
  missing="$(printf '%s' "$deps_json" | "$PYTHON_BIN" -c 'import json,sys; d=json.load(sys.stdin); print(", ".join(d.get("missing_tools", [])))')"
  if [[ -n "$missing" ]]; then
    echo "Aviso: faltan herramientas del sistema: $missing" >&2
    echo "Paquetes apt: $(printf '%s' "$deps_json" | "$PYTHON_BIN" -c 'import json,sys; d=json.load(sys.stdin); print(", ".join(d.get("missing_packages", [])))')" >&2
    echo "Para instalarlas, vuelve a ejecutar: ./install.sh --install-system-tools" >&2
  else
    echo "Todas las herramientas del sistema están disponibles."
  fi
fi
