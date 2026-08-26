"""CLI de operación y diagnóstico del Wireless Tool."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

from .engine import BANNER_VARIANTS, WirelessTool

REQUIRED_TOOLS = ("airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng", "hostapd", "dnsmasq", "mitmproxy", "iptables")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wireless scanner, handshake, rogue AP, MITM y payload workflow autorizado")
    parser.add_argument("--interface", help="interfaz Wi-Fi; por defecto WIRELESS_INTERFACE o wlan0")
    parser.add_argument("--uplink", help="interfaz uplink; por defecto UPLINK_INTERFACE o eth0")
    parser.add_argument("--banner-style", type=int, choices=range(len(BANNER_VARIANTS)))
    parser.add_argument("--show-banner", action="store_true", help="muestra el banner y termina")
    parser.add_argument("--check-only", action="store_true", help="valida configuración y dependencias sin crear archivos ni activar radio")
    parser.add_argument("--json", action="store_true", help="emite el diagnóstico en JSON")
    parser.add_argument("--no-menu", action="store_true", help="reservado para integraciones no interactivas")
    parser.add_argument("--interactive", action="store_true", help="selector operacional diagnóstico/flujo wireless")
    parser.add_argument("--guided", action="store_true", help="muestra etapas y termina sin activar radio")
    return parser


def guided_flow() -> str:
    return "\n".join([
        "Flujo WIRELESS INJECTOR: scope -> diagnóstico -> scan -> captura -> payload/callback -> cleanup.",
        "El modo diagnóstico no crea directorios ni activa radio; el flujo operacional exige laboratorio y privilegios aprobados.",
        "Verifica interfaz monitor, uplink, dependencias y procedimiento de restauración antes de continuar.",
    ])


def _interactive_select(args: argparse.Namespace) -> None:
    if not sys.stdin.isatty():
        raise ValueError("--interactive requiere una terminal interactiva")
    print(guided_flow())
    choice = input("Selecciona [1] diagnóstico [2] operación [q] cancelar: ").strip().lower()
    if choice == "1":
        args.check_only = True
        args.no_menu = False
    elif choice == "2":
        args.check_only = False
        args.no_menu = False
    else:
        raise ValueError("operación cancelada por el operador")


def _banner_style(style: int | None) -> int:
    if style is None:
        return random.SystemRandom().randrange(len(BANNER_VARIANTS))
    return style


def check_environment(tool: WirelessTool) -> dict:
    tools = {name: shutil.which(name) for name in REQUIRED_TOOLS}
    return {
        "interface": tool.interface,
        "monitor_interface": tool.mon_interface,
        "uplink_interface": tool.uplink_interface,
        "required_tools": tools,
        "missing_tools": [name for name, path in tools.items() if path is None],
        "root": False,
        "radio_started": False,
        "note": "diagnóstico únicamente; no se crearon directorios ni se transmitieron frames",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        style = _banner_style(args.banner_style)
        if args.guided:
            print(BANNER_VARIANTS[style])
            print(guided_flow())
            return 0
        if args.interactive:
            _interactive_select(args)
        tool = WirelessTool(interface=args.interface, uplink_interface=args.uplink, banner_style=style, create_dirs=not args.check_only and not args.show_banner)
        if args.show_banner:
            tool.banner()
            return 0
        if args.check_only:
            payload = check_environment(tool)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                tool.banner()
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.no_menu:
            raise ValueError("--no-menu requiere una suborden operativa futura; no se inicia una acción implícita")
        print("[WIRELESS FLOW] scope -> validate -> diagnose -> scan/capture -> payload/callback -> cleanup")
        tool.run()
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"[!] Error de configuración: {exc}")
        return 2
