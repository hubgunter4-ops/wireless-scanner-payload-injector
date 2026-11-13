"""Dependencias del sistema para el Wireless Tool.

Mapa binario -> paquete apt (Debian/Kali). Los nombres de los binarios
NO son paquetes apt: ``airmon-ng``, ``airodump-ng`` y ``aireplay-ng``
pertenecen todos al paquete ``aircrack-ng``.

Este módulo no activa radio, no escanea y no ejecuta ninguna de las
herramientas inalámbricas. Solo comprueba si están en PATH y, si el
operador lo pide explícitamente, las instala con apt-get.

Uso no interactivo: ninguna función de este módulo pregunta por stdin.
"""

from __future__ import annotations

import os
import shutil
import subprocess

# Binario -> paquete apt real. Orden de inserción = orden de
# REQUIRED_TOOLS en cli.py, para que los paquetes deduplicados
# salgan en un orden estable y predecible.
TOOL_PACKAGES = {
    "airmon-ng": "aircrack-ng",
    "airodump-ng": "aircrack-ng",
    "aireplay-ng": "aircrack-ng",
    "aircrack-ng": "aircrack-ng",
    "hostapd": "hostapd",
    "dnsmasq": "dnsmasq",
    "mitmproxy": "mitmproxy",
    "iptables": "iptables",
}

REQUIRED_TOOLS = tuple(TOOL_PACKAGES)

# Herramientas IoT de la guía uqbarun/uqbarun.github.io@4f09668
# ("IoT pentest", _wiki/iot-pentest.md, 2023-06-01, FredyRosero).
# Solo se añaden binarios con paquete apt real en Debian/Kali:
# tshark -> tshark, nmap -> nmap, binwalk -> binwalk,
# bluetoothctl/hcitool/gatttool -> bluez, rtl_sdr -> rtl-sdr,
# hackrf_info -> hackrf. Zigbee no tiene binario apt estándar:
# exige hardware dedicado (CC2531, ConBee II, KillerBee) y por eso
# no aparece aquí; su perfil lo documenta como hardware_required.
# Estas herramientas NO forman parte de REQUIRED_TOOLS: el
# --check-only base sigue comprobando solo el flujo Wi-Fi, y los
# perfiles IoT se comprueban aparte con --iot-profile.
IOT_TOOL_PACKAGES = {
    "tshark": "tshark",
    "nmap": "nmap",
    "binwalk": "binwalk",
    "bluetoothctl": "bluez",
    "hcitool": "bluez",
    "gatttool": "bluez",
    "rtl_sdr": "rtl-sdr",
    "hackrf_info": "hackrf",
}

ALL_TOOL_PACKAGES = {**TOOL_PACKAGES, **IOT_TOOL_PACKAGES}


def packages_for_tools(tools):
    """Paquetes apt deduplicados para una lista de binarios, en orden.

    Acepta binarios base (TOOL_PACKAGES) e IoT (IOT_TOOL_PACKAGES).
    """
    packages = []
    for tool in tools or []:
        package = ALL_TOOL_PACKAGES.get(tool)
        if package is None:
            raise ValueError(f"Herramienta desconocida: {tool!r}")
        if package not in packages:
            packages.append(package)
    return packages


def check_dependencies(tools=None):
    """Comprueba qué herramientas del sistema están disponibles.

    Devuelve un dict con:
      tools: {binario: ruta o None}
      missing: [binarios que faltan]
      packages: [paquetes apt deduplicados para los que faltan]
      missing_packages: alias de packages
    No ejecuta nada, no pregunta nada, no instala nada.
    """
    names = list(tools) if tools is not None else list(REQUIRED_TOOLS)
    found = {name: shutil.which(name) for name in names}
    missing = [name for name, path in found.items() if path is None]
    packages = packages_for_tools(missing)
    return {
        "tools": found,
        "missing": missing,
        "packages": packages,
        "missing_packages": packages,
    }


def _sudo_prefix(use_sudo=None):
    """Prefijo sudo si hace falta, o [] si se es root / no se pide.

    use_sudo=None -> automático: sudo solo si euid != 0 y sudo existe.
    use_sudo=True -> exige sudo, error si no existe.
    use_sudo=False -> nunca usa sudo; si euid != 0, error.
    """
    is_root = os.geteuid() == 0
    if use_sudo is True:
        if shutil.which("sudo") is None:
            raise RuntimeError(
                "Se pidió sudo pero no está disponible en este sistema"
            )
        return ["sudo"]
    if use_sudo is False:
        if not is_root:
            raise RuntimeError(
                "Instalar paquetes del sistema requiere root o sudo; "
                "ejecuta como root o permite sudo (use_sudo=True)"
            )
        return []
    # Automático.
    if is_root:
        return []
    if shutil.which("sudo") is None:
        raise RuntimeError(
            "Instalar paquetes del sistema requiere root o sudo y "
            "sudo no está disponible en este sistema"
        )
    return ["sudo"]


def build_install_commands(missing, use_sudo=None):
    """Comandos apt que instalarían lo que falta, sin ejecutarlos.

    Devuelve una lista de comandos (cada uno, una lista de argv):
    [apt-get update, apt-get install -y <paquetes deduplicados>].
    Si no falta nada, devuelve [].
    """
    packages = packages_for_tools(missing)
    if not packages:
        return []
    prefix = _sudo_prefix(use_sudo)
    return [
        [*prefix, "apt-get", "update"],
        [*prefix, "apt-get", "install", "-y", *packages],
    ]


def install_missing(missing, dry_run=False, use_sudo=None):
    """Instala los paquetes apt de las herramientas que faltan.

    - dry_run=True: solo imprime los comandos, no ejecuta subprocess.
    - dry_run=False: ejecuta apt-get update y luego
      apt-get install -y <paquetes deduplicados>.
    - Usa sudo si euid != 0 y sudo está disponible (o según use_sudo).
    - Falla con RuntimeError claro si no hay apt-get, si no hay
      permisos (ni root ni sudo) o si apt-get falla.
    - Después de instalar, verifica con shutil.which cada herramienta;
      si alguna sigue faltando, falla con RuntimeError.

    Devuelve True si no faltaba nada o si la instalación y la
    verificación posterior tuvieron éxito.
    """
    packages = packages_for_tools(missing)
    if not packages:
        return True
    commands = build_install_commands(missing, use_sudo=use_sudo)
    if dry_run:
        for command in commands:
            print("[DRY-RUN] " + " ".join(command))
        return True
    if shutil.which("apt-get") is None:
        raise RuntimeError(
            "apt-get no está disponible en este sistema; "
            "instala manualmente los paquetes: " + ", ".join(packages)
        )
    for command in commands:
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                "Falló el comando: " + " ".join(command) + ". "
                "Paquetes pendientes: " + ", ".join(packages)
            )
    # Verificación posterior: no dar por hecho que apt tuvo éxito.
    still_missing = [
        tool for tool in missing if shutil.which(tool) is None
    ]
    if still_missing:
        raise RuntimeError(
            "Tras instalar, siguen faltando: " + ", ".join(still_missing)
            + ". Paquetes instalados: " + ", ".join(packages)
        )
    return True
