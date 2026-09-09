# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

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
