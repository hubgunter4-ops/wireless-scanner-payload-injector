#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHON_USER_BIN="${PYTHON_USER_BIN:-$HOME/.local/bin}"
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      printf '%s\n' 'Uso: ./install.sh [--dry-run]' 'Instala el paquete para el usuario actual, sin crear ni activar un entorno virtual, y verifica el entrypoint wireless-injector.'
      exit 0 ;;
    *) printf 'Error: opción desconocida: %s\n' "$arg" >&2; exit 2 ;;
  esac
done
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Error: no se encontró $PYTHON_BIN" >&2; exit 2; }
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else "Se requiere Python >= 3.10")'
if (( DRY_RUN )); then
  printf '%s\n' "[DRY-RUN] $PYTHON_BIN -m pip install --user -e $ROOT_DIR" "[DRY-RUN] $PYTHON_USER_BIN/wireless-injector --help"
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
