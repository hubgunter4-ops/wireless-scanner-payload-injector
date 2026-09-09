# Tutorial: instalación y diagnóstico seguro

Este recorrido valida la instalación sin activar la radio ni crear directorios operativos. La operación inalámbrica real queda fuera de este tutorial y requiere un laboratorio autorizado, una ventana definida y un procedimiento de limpieza.

## Requisitos

| Requisito | Valor |
|---|---|
| Sistema | Linux con Bash |
| Python | 3.10 o superior |
| Código | Clonado desde el repositorio canónico |
| Red | No necesaria para el diagnóstico |
| Privilegios | No necesarios para `--check-only` |

## Instalación sin activar funciones operativas

```bash
./install.sh --dry-run
./install.sh
export PATH="$HOME/.local/bin:$PATH"
wireless-injector --help
```

El instalador instala el paquete para el usuario actual. No crea ni activa un entorno virtual y no inicia captura, transmisión ni inyección.

## Diagnóstico JSON

```bash
wireless-injector --check-only --json --interface wlan0 --uplink eth0
```

El resultado muestra las herramientas detectadas, las interfaces derivadas y una nota de que no se inició la radio. La ausencia de una dependencia no debe resolverse instalando paquetes durante una operación activa; prepara primero una imagen o máquina de laboratorio.

## Pruebas locales

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile src/wireless_injector.py src/wireless_tool/*.py
git diff --check
```

## Preparación de un laboratorio

Antes de cualquier fase operacional, documenta por escrito el propietario, BSSID/SSID objetivo, clientes de prueba, interfaz, uplink, canales, subred, puertos, ventana de ejecución y procedimiento de rollback. Aísla el laboratorio de Internet y de redes de terceros cuando sea posible. Usa únicamente identidades y datos ficticios.

Consulta [authorization.md](authorization.md), [operator-checklist.md](operator-checklist.md) y [cleanup.md](cleanup.md). Un diagnóstico, un plan o una prueba de instalación no equivale a una vulnerabilidad confirmada.

## Limpieza

Detén los procesos, revierte las reglas de firewall y restaura la interfaz antes de abandonar el laboratorio. Conserva evidencia únicamente si está autorizada, anonimizada y almacenada fuera del repositorio público o compartido.
