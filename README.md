# WIRELESS INJECTOR — Wireless Assessment Workflow

![Flujo de transición y operación](assets/operation-flow.png)

## Higiene del repo

Workflow Python wireless ofensivo autorizado para scan, captura de handshake, rogue AP, MITM y payload/callback. El engine conserva rutas reales y el CLI separa diagnóstico, menú operacional y cleanup; `--check-only` inspecciona binarios e interfaces sin crear directorios ni activar radio. Requiere Scapy/entorno Python y herramientas de estación según el flujo seleccionado. El repositorio público no contiene credenciales, tokens, configuraciones de engagement, capturas reales, logs ni artefactos generados. Las carpetas `evidence/`, `screenshots/` y `pruebas/` se mantienen fuera del árbol publicado; `tests/` se conserva exclusivamente como control de regresión técnica. Las plantillas y fixtures, cuando existen, usan valores de laboratorio y no conceden autorización.

## Licencia

El código se distribuye bajo **MIT License**. Consulta el archivo `LICENSE` para el texto legal completo. El uso de funciones que envían tráfico, transmiten RF, interactúan con dispositivos, ejecutan módulos o procesan material de autenticación requiere autorización escrita independiente.

## Estructura

`src/wireless_tool/` separa CLI y engine; `check_environment` permite diagnóstico sin directorios ni radio; `archive/original/` mantiene trazabilidad; `tests/` verifica validaciones y cleanup. La imagen `assets/operation-flow.png` resume la transición operacional; el banner interno se mantiene en el entrypoint o núcleo de la herramienta.

## Flujo recomendado

El flujo recomendado es ejecutar `--guided` o `--interactive`, usar `--check-only --json` para conocer dependencias, revisar `--interface` y `--uplink`, y solo después abrir el menú operacional. La operación real —scan, handshake, rogue AP, MITM y payload/callback— necesita privilegios, cleanup y alcance RF aprobado. El operador debe registrar target, ventana, privilegios, dependencias, resultado y procedimiento de cleanup. Un plan, dry-run o diagnóstico no equivale a una ejecución real ni a una vulnerabilidad confirmada.

## PASOS DE INSTALACION

Requiere Bash y Python 3.10 o superior. El instalador usa el site de paquetes del usuario actual y no crea ni activa `.venv`; el entrypoint suele quedar en `$HOME/.local/bin`.

```bash
./install.sh --help
./install.sh
export PATH="$HOME/.local/bin:$PATH"
wireless-injector --help
wireless-injector --check-only --json
```

El modo `--check-only` permite comprobar configuración sin transmitir. No se ejecutan capturas ni inyecciones durante la instalación; cualquier operación de laboratorio exige autorización y confirmación explícita según el flujo documentado.

## Guía de ejecución

Empieza con el modo de comprobación:

```bash
./install.sh --help
./install.sh --guided
PYTHONPATH=src python3 src/wireless_injector.py --check-only
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

`--check-only` valida dependencias y configuración sin root ni radio. La operación real requiere una interfaz wireless compatible, permisos de laboratorio y autorización para cada target; revisa límites, firewall y cleanup antes de activar cualquier fase. No guardes capturas, hashes, credenciales ni artefactos operativos en Git.
