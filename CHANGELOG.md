# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

## [Unreleased]

### IoT pentest como base

- 6 perfiles IoT de diagnóstico basados en la guía pública
  `uqbarun/uqbarun.github.io@4f09668` ("IoT pentest",
  `_wiki/iot-pentest.md`, 2023-06-01): `web-api`, `firmware`,
  `wifi`, `ble`, `zigbee` y `sdr`, con habilidades, pasos y
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

## [2.1.0] — 2026-09-09

### Documentación

- Se documenta el flujo de diagnóstico, operación autorizada y limpieza.
- Se aclara la diferencia entre el paquete Python y las dependencias de sistema.
- Se registra que el diagnóstico local encontró ausentes `airmon-ng`, `airodump-ng`, `aireplay-ng`, `aircrack-ng`, `hostapd`, `dnsmasq` y `mitmproxy`; `iptables` estaba disponible.
- Se añade una política de seguridad con alcance, datos prohibidos y reporte responsable.
- Se añade un tutorial reproducible con diagnóstico seguro y laboratorio aislado.
- Se añaden materiales de promoción, redistribución y un feed Atom estático.
- Se aclaran las capacidades sensibles: deauth, handshakes, rogue AP, MITM, DNS spoofing, payloads y callbacks.

### Verificación

- Las funciones principales del script no se modifican en esta actualización.
- Las pruebas existentes y la compilación sintáctica deben pasar antes de etiquetar una release.

[2.1.0]: https://github.com/hubgunter4-ops/wireless-scanner-payload-injector/compare/56fed5b...HEAD
