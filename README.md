# WIRELESS INJECTOR — Wireless Assessment Workflow

![Flujo de transición y operación](assets/operation-flow.png)

## Higiene del repo

Workflow wireless ofensivo autorizado para scan, captura de handshake, rogue AP, MITM y payload/callback. El diagnóstico está separado de la operación y no convierte las rutas ofensivas en simulación. El repositorio público no contiene credenciales, tokens, configuraciones de engagement, capturas reales, logs ni artefactos generados. Las carpetas `evidence/`, `screenshots/` y `pruebas/` se mantienen fuera del árbol publicado; `tests/` se conserva exclusivamente como control de regresión técnica. Las plantillas y fixtures, cuando existen, usan valores de laboratorio y no conceden autorización.

## Licencia

El código se distribuye bajo **MIT License**. Consulta el archivo `LICENSE` para el texto legal completo. El uso de funciones que envían tráfico, transmiten RF, interactúan con dispositivos, ejecutan módulos o procesan material de autenticación requiere autorización escrita independiente.

## Estructura

`src/wireless_tool/` separa CLI y engine; `check_environment` permite diagnóstico sin directorios ni radio; `archive/original/` mantiene trazabilidad; `tests/` verifica validaciones y cleanup. La imagen `assets/operation-flow.png` resume la transición operacional; el banner interno se mantiene en el entrypoint o núcleo de la herramienta.

## Flujo recomendado

El flujo recomendado es ejecutar `--guided` o `--interactive`, usar `--check-only --json` para conocer dependencias, preparar interfaz monitor/uplink y cleanup, y solo después abrir el menú operacional con privilegios y alcance RF aprobado. El operador debe registrar target, ventana, privilegios, dependencias, resultado y procedimiento de cleanup. Un plan, dry-run o diagnóstico no equivale a una ejecución real ni a una vulnerabilidad confirmada.

## Pasos de instalación

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
wireless-injector --guided
wireless-injector --check-only --json
```
Airmon-ng, hostapd, dnsmasq, mitmproxy, iptables y hardware compatible se preparan fuera de la instalación Python.

Punto de entrada principal: `wireless-injector` o `python3 src/wireless_injector.py`. Revisa siempre `--help` y la autorización vigente antes de elegir una operación activa.
