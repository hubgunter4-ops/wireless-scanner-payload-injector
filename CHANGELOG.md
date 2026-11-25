# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

## [Unreleased]

## [2.2.0] — 2026-11-25

### CLI, diagnóstico y distribución Debian

- Se añade `--dashboard` con pestañas Resumen, Ejecutores, Perfiles y Monitor, tema negro/rojo/magenta y carga animada.
- El monitor permite repetir la consulta local de disponibilidad en `PATH`; no lanza herramientas, no crea directorios ni activa radio.
- Se incorpora el logo Wi‑Fi animado y tres mockups; la documentación explica los efectos del modo operacional.
- Se agrega `packaging/build-deb.sh` para producir un paquete Debian `Architecture: all` con dependencia Python 3.10+; instalar el `.deb` no instala herramientas wireless del sistema.
- La suite de verificación incluye pruebas del dashboard y mantiene la compilación sintáctica.

### IoT pentest como base

- 6 perfiles IoT de diagnóstico basados en la guía pública
  `uqbarun/uqbarun.github.io@4f09668` ("IoT pentest",
  `_wiki/iot-pentest.md`, 2023-06-01): `web-api`, `firmware`, `wifi`,
  `ble`, `zigbee` y `sdr`, con habilidades, pasos y
  CWE/CAPEC/CPE de la guía (`src/wireless_tool/iot_profiles.py`,
  `docs/iot-pentest.md`).
- Mapa binario → paquete apt para las herramientas IoT con paquete
  real: `tshark`, `nmap`, `binwalk`, `bluez` (bluetoothctl/hcitool/
  gatttool), `rtl-sdr` y `hackrf`. Zigbee no tiene binario apt
  estándar y se marca como hardware dedicado, sin inventar paquete.
- CLI: `--list-iot-profiles` y `--iot-profile <perfil>` solo con
  `--check-only` (diagnóstico; también con `--dry-run` y
  `--install-missing`). El `--check-only` base no cambia.
- Los perfiles solo comprueban dependencias con `shutil.which`;
  no activan radio, no escanean, no descifran ni ejecutan ataques.

### Verificación

- Suite completa de 48 pruebas, compilación Python y `git diff --check` correctos.

[2.2.0]: https://github.com/hubgunter4-ops/wireless-scanner-payload-injector/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/hubgunter4-ops/wireless-scanner-payload-injector/releases/tag/v2.1.0
