#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/dist}"
PACKAGE="wireless-scanner-payload-injector"
VERSION="$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$ROOT_DIR/pyproject.toml" | head -n 1)"

if [[ -z "$VERSION" ]]; then
  echo "No se encontró project.version en pyproject.toml" >&2
  exit 1
fi
if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "Falta dpkg-deb; instala el paquete dpkg en la máquina de construcción." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
PKG_ROOT="$WORK_DIR/$PACKAGE"
DEB_PATH="$OUTPUT_DIR/${PACKAGE}_${VERSION}-1_all.deb"

install -d "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/usr/lib/python3/dist-packages" \
  "$PKG_ROOT/usr/lib/python3/dist-packages/wireless_tool" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT/usr/share/doc/$PACKAGE"
cp -a "$ROOT_DIR/src/wireless_tool/." "$PKG_ROOT/usr/lib/python3/dist-packages/wireless_tool/"
find "$PKG_ROOT/usr/lib/python3/dist-packages" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$PKG_ROOT/usr/lib/python3/dist-packages" -type f -name '*.pyc' -delete

cat > "$PKG_ROOT/usr/bin/wireless-injector" <<'PYTHON'
#!/usr/bin/python3
from wireless_tool.cli import main

raise SystemExit(main())
PYTHON
chmod 0755 "$PKG_ROOT/usr/bin/wireless-injector"
install -m 0644 "$ROOT_DIR/README.md" "$PKG_ROOT/usr/share/doc/$PACKAGE/README.md"
install -m 0644 "$ROOT_DIR/LICENSE" "$PKG_ROOT/usr/share/doc/$PACKAGE/LICENSE"
install -m 0644 "$ROOT_DIR/CHANGELOG.md" "$PKG_ROOT/usr/share/doc/$PACKAGE/CHANGELOG.md"

cat > "$PKG_ROOT/DEBIAN/control" <<CONTROL
Package: $PACKAGE
Version: ${VERSION}-1
Section: net
Priority: optional
Architecture: all
Depends: python3 (>= 3.10)
Maintainer: hubgunter4-ops <hubgunter4-ops@users.noreply.github.com>
Homepage: https://github.com/hubgunter4-ops/wireless-scanner-payload-injector
Description: authorized wireless assessment and payload workflow tool
 Python CLI for authorized Linux wireless assessment and controlled lab workflows.
 Operational features can alter radio interfaces, processes, files, networking,
 forwarding, NAT, or firewall rules. Use only in an authorized lab environment.
CONTROL

chmod 0755 "$PKG_ROOT/DEBIAN"
dpkg-deb --root-owner-group --build "$PKG_ROOT" "$DEB_PATH"
printf 'Paquete generado: %s\n' "$DEB_PATH"
