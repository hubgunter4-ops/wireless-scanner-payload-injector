#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      printf '%s\n' 'Uso: ./install.sh [--dry-run]' 'Crea un entorno virtual local, instala el paquete editable y verifica el entrypoint wireless-injector.'
      exit 0 ;;
    *) printf 'Error: opción desconocida: %s\n' "$arg" >&2; exit 2 ;;
  esac
done
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Error: no se encontró $PYTHON_BIN" >&2; exit 2; }
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else "Se requiere Python >= 3.10")'
if (( DRY_RUN )); then
  printf '%s\n' "[DRY-RUN] $PYTHON_BIN -m venv $VENV_DIR" "[DRY-RUN] $VENV_DIR/bin/python -m pip install --upgrade pip" "[DRY-RUN] $VENV_DIR/bin/python -m pip install -e $ROOT_DIR" "[DRY-RUN] $VENV_DIR/bin/wireless-injector --help"
  exit 0
fi
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "$ROOT_DIR"
"$VENV_DIR/bin/wireless-injector" --help >/dev/null
printf '%s\n' 'Instalación completada.' "Activa el entorno con: . $VENV_DIR/bin/activate" "Entry point verificado: $VENV_DIR/bin/wireless-injector"
