"""Perfiles IoT para el Wireless Tool, basados en la guía pública
``uqbarun/uqbarun.github.io`` commit ``4f09668`` ("IoT pentest",
``_wiki/iot-pentest.md``, 2023-06-01, FredyRosero).

La guía tiene 3 secciones y este módulo las convierte en 6 perfiles
de diagnóstico, sin ejecutar ningún ataque:

  Sección 1 (servicios web de redes IoT) -> ``web-api``
  Sección 2 (hardware y firmware)       -> ``firmware``
  Sección 3 (inalámbrico)               -> ``wifi``, ``ble``,
                                            ``zigbee``, ``sdr``

Cada perfil es solo datos: habilidades y pasos copiados como lista
de verificación de la guía, IDs CWE/CAPEC/CPE que la guía asigna a
su sección, y los binarios que hacen falta para ese perfil.

Este módulo NO activa radio, NO escanea, NO captura, NO descifra
claves, NO explota BLE/Zigbee y NO transmite nada. Solo comprueba
con ``shutil.which`` si los binarios del perfil están en PATH y
resuelve sus paquetes apt con ``dependencies``. Zigbee no tiene
binario apt estándar: su perfil marca ``hardware_required`` y no
inventa ningún paquete.

Uso autorizado únicamente: laboratorio propio con autorización
escrita, como el resto del proyecto (ver ``docs/authorization.md``).
"""

from __future__ import annotations

import shutil

from .dependencies import IOT_TOOL_PACKAGES, TOOL_PACKAGES, packages_for_tools

SOURCE = {
    "repo": "uqbarun/uqbarun.github.io",
    "commit": "4f096689b0ac4527682f66c36a8d29ca87ff647d",
    "file": "_wiki/iot-pentest.md",
    "author": "FredyRosero",
    "date": "2023-06-01",
}

# Perfil: id -> dict con title, source_section, description, skills,
# steps, cwe, capec, cpe, tools (binarios) y hardware (si lo exige).
IOT_PROFILES = {
    "web-api": {
        "title": "Servicios web y API de IoT",
        "source_section": "Sección 1",
        "description": (
            "Reconocimiento de red, vulnerabilidades web en dispositivos "
            "IoT, solicitudes de API y técnicas de explotación web."
        ),
        "skills": [
            "Comprender los objetivos y la metodología para probar IoT.",
            "Familiarizarse con las herramientas de pentest IoT.",
            "Aprender descubrimiento y reconocimiento de redes.",
            "Explorar explotación de redes específica de IoT.",
            "Comprender servicios web en IoT y reconocimiento de apps web y API.",
            "Conocer las herramientas para probar servicios web.",
            "Identificar tipos de ataques a servicios web y métodos de explotación.",
        ],
        "steps": [
            "Usar filtros de Wireshark e inspeccionar archivos PCAP.",
            "Escanear con Nmap un dispositivo IoT.",
            "Interceptar secretos con Burp Suite en un portal web de IoT.",
            "Enviar datos a una API de IoT (Postman en la guía).",
            "Probar portales IoT de grado de consumo en laboratorio.",
            "Probar inyección de comandos en servicios web vulnerables de IoT.",
        ],
        "cwe": ["CWE-200", "CWE-287", "CWE-89", "CWE-94"],
        "capec": ["CAPEC-7", "CAPEC-88", "CAPEC-155", "CAPEC-234"],
        "cpe": ["cpe:2.3:a:IoTDevice:*"],
        # mitmproxy ya es herramienta base del proyecto; nmap y tshark
        # son las nuevas de este perfil.
        "tools": ["nmap", "tshark", "mitmproxy"],
        "hardware": [],
    },
    "firmware": {
        "title": "Interfaces de hardware y análisis de firmware",
        "source_section": "Sección 2",
        "description": (
            "Identificación de hardware, interfaces Serie/SPI/JTAG, "
            "recuperación de firmware y extracción de secretos del "
            "sistema de archivos."
        ),
        "skills": [
            "Comprender la importancia del hardware IoT en el pentest.",
            "Abrir dispositivos IoT e identificar sus componentes.",
            "Descubrir e identificar puertos de hardware.",
            "Introducción a las técnicas de soldadura.",
            "Espiar, interactuar y explotar puertos Serie, SPI y JTAG.",
            "Dominar la recuperación de firmware de dispositivos IoT.",
            "Conocer técnicas de análisis de firmware.",
            "Extraer información valiosa del firmware.",
        ],
        "steps": [
            "Obtener y analizar hojas de especificaciones del dispositivo.",
            "Espiar la comunicación serie y SPI.",
            "Recuperar firmware de archivos PCAP capturados.",
            "Usar binwalk para extraer y analizar sistemas de archivos del firmware.",
            "Extraer información valiosa del sistema de archivos.",
        ],
        "cwe": ["CWE-327", "CWE-78", "CWE-494", "CWE-119"],
        "capec": ["CAPEC-28", "CAPEC-186", "CAPEC-221", "CAPEC-226"],
        "cpe": ["cpe:2.3:h:IoTDevice:Firmware:*"],
        "tools": ["binwalk", "tshark"],
        "hardware": ["UART/Serie", "SPI", "JTAG"],
    },
    "wifi": {
        "title": "IoT inalámbrico: Wi-Fi",
        "source_section": "Sección 3",
        "description": (
            "Captura de tráfico Wi-Fi, acceso a la red y claves "
            "precompartidas (PSK) de dispositivos IoT, en laboratorio."
        ),
        "skills": [
            "Comprender los conceptos básicos de Wi-Fi.",
            "Aprender técnicas para descifrar claves precompartidas (PSK) de Wi-Fi.",
        ],
        "steps": [
            "Descifrar claves precompartidas de Wi-Fi para obtener acceso a la red.",
        ],
        "cwe": ["CWE-798", "CWE-250", "CWE-327", "CWE-319"],
        "capec": ["CAPEC-108", "CAPEC-141", "CAPEC-545"],
        "cpe": ["cpe:2.3:a:WiFiDevice:*"],
        # Reutiliza el flujo Wi-Fi base del proyecto (aircrack-ng) y
        # añade tshark para inspeccionar la captura.
        "tools": ["airmon-ng", "airodump-ng", "aircrack-ng", "tshark"],
        "hardware": ["Adaptador Wi-Fi con modo monitor"],
    },
    "ble": {
        "title": "IoT inalámbrico: Bluetooth Low Energy (BLE)",
        "source_section": "Sección 3",
        "description": (
            "Interacción y explotación de dispositivos BLE en laboratorio."
        ),
        "skills": [
            "Comprender los conceptos básicos de Bluetooth Low Energy (BLE).",
            "Comprender la interacción y explotación de dispositivos BLE.",
        ],
        "steps": [
            "Interactuar y explotar dispositivos BLE.",
        ],
        "cwe": ["CWE-798", "CWE-250", "CWE-327", "CWE-319"],
        "capec": ["CAPEC-199", "CAPEC-141", "CAPEC-545"],
        "cpe": ["cpe:2.3:a:BLEDevice:*"],
        "tools": ["bluetoothctl", "hcitool", "gatttool"],
        "hardware": ["Adaptador Bluetooth / BLE"],
    },
    "zigbee": {
        "title": "IoT inalámbrico: Zigbee",
        "source_section": "Sección 3",
        "description": (
            "Captura y análisis de tráfico Zigbee en laboratorio. "
            "No hay binario apt estándar para esto: exige hardware "
            "dedicado y este perfil solo lo documenta y lo comprueba "
            "como pendiente, sin inventar un paquete."
        ),
        "skills": [
            "Comprender los conceptos básicos de Zigbee.",
            "Capturar y analizar tráfico Zigbee.",
        ],
        "steps": [
            "Capturar y analizar el tráfico de la red Zigbee.",
        ],
        "cwe": ["CWE-798", "CWE-250", "CWE-327", "CWE-319"],
        "capec": ["CAPEC-141", "CAPEC-545"],
        "cpe": ["cpe:2.3:a:ZigbeeDevice:*"],
        "tools": [],
        "hardware": ["CC2531", "ConBee II", "KillerBee"],
        "hardware_required": True,
    },
    "sdr": {
        "title": "IoT inalámbrico: LoRa y SDR",
        "source_section": "Sección 3",
        "description": (
            "Análisis y explotación de comunicaciones RF no estándar y "
            "propietarias (LoRa, SDR) y ataques de repetición, en "
            "laboratorio."
        ),
        "skills": [
            "Comprender los conceptos básicos de LoRa y Software-Defined Radio (SDR).",
            "Realizar ataques de transmisión de repetición en dispositivos IoT con RF no estándar.",
        ],
        "steps": [
            "Realizar ataques de transmisión de repetición en dispositivos IoT.",
        ],
        "cwe": ["CWE-798", "CWE-250", "CWE-327", "CWE-319"],
        "capec": ["CAPEC-141", "CAPEC-545"],
        "cpe": ["cpe:2.3:a:SDRDevice:*"],
        "tools": ["rtl_sdr", "hackrf_info"],
        "hardware": ["RTL-SDR", "HackRF"],
    },
}


def list_profiles():
    """IDs de perfil en orden estable."""
    return list(IOT_PROFILES)


def get_profile(profile_id):
    """Devuelve una copia del perfil, o ValueError si no existe."""
    try:
        profile = IOT_PROFILES[profile_id]
    except KeyError:
        raise ValueError(
            f"Perfil IoT desconocido: {profile_id!r}. "
            f"Perfiles: {', '.join(list_profiles())}"
        ) from None
    return {**profile, "id": profile_id, "source": dict(SOURCE)}


def check_profile(profile_id):
    """Comprueba qué binarios del perfil están disponibles.

    Devuelve un dict con el perfil (id, título, sección, CWE/CAPEC/CPE,
    hardware) más tools/missing/packages. No ejecuta nada, no pregunta
    nada, no instala nada y no activa radio.
    """
    profile = get_profile(profile_id)
    tools = profile["tools"]
    found = {name: shutil.which(name) for name in tools}
    missing = [name for name, path in found.items() if path is None]
    packages = packages_for_tools(missing)
    return {
        **profile,
        "tools_found": found,
        "missing": missing,
        "packages": packages,
        "missing_packages": packages,
        "ready": not missing and not profile.get("hardware_required", False),
    }


def all_tools_known():
    """True si cada binario de cada perfil tiene paquete apt o es hardware."""
    known = {**TOOL_PACKAGES, **IOT_TOOL_PACKAGES}
    for profile in IOT_PROFILES.values():
        for tool in profile["tools"]:
            if tool not in known:
                return False
    return True
