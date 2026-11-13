"""CLI de operación y diagnóstico del Wireless Tool."""

from __future__ import annotations

import argparse
import json
import random
import sys

from .dependencies import (
    REQUIRED_TOOLS,
    build_install_commands,
    check_dependencies,
    install_missing,
)
from .engine import BANNER_VARIANTS, WirelessTool
from .iot_profiles import check_profile, get_profile, list_profiles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wireless scanner, handshake, rogue AP, MITM y payload workflow autorizado")
    parser.add_argument("--interface", help="interfaz Wi-Fi; por defecto WIRELESS_INTERFACE o wlan0")
    parser.add_argument("--uplink", help="interfaz uplink; por defecto UPLINK_INTERFACE o eth0")
    parser.add_argument("--banner-style", type=int, choices=range(len(BANNER_VARIANTS)))
    parser.add_argument("--show-banner", action="store_true", help="muestra el banner y termina")
    parser.add_argument("--check-only", action="store_true", help="valida configuración y dependencias sin crear archivos ni activar radio")
    parser.add_argument("--install-missing", action="store_true", help="con --check-only, instala las dependencias del sistema que falten (apt-get)")
    parser.add_argument("--dry-run", action="store_true", help="con --check-only, solo imprime los comandos apt que se ejecutarían, sin ejecutar nada")
    parser.add_argument("--json", action="store_true", help="emite el diagnóstico en JSON")
    parser.add_argument("--no-menu", action="store_true", help="reservado para integraciones no interactivas")
    parser.add_argument("--interactive", action="store_true", help="selector operacional diagnóstico/flujo wireless")
    parser.add_argument("--guided", action="store_true", help="muestra etapas y termina sin activar radio")
    parser.add_argument("--list-iot-profiles", action="store_true", help="lista los perfiles IoT (guía uqbarun 4f09668) y termina, sin activar radio")
    parser.add_argument("--iot-profile", choices=list_profiles(), help="con --check-only, comprueba además las dependencias del perfil IoT indicado")
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
    deps = check_dependencies()
    return {
        "interface": tool.interface,
        "monitor_interface": tool.mon_interface,
        "uplink_interface": tool.uplink_interface,
        "required_tools": deps["tools"],
        "missing_tools": deps["missing"],
        "missing_packages": deps["packages"],
        "packages": deps["packages"],
        "root": False,
        "radio_started": False,
        "note": "diagnóstico únicamente; no se crearon directorios ni se transmitieron frames",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        style = _banner_style(args.banner_style)
        if args.list_iot_profiles:
            profiles = [get_profile(pid) for pid in list_profiles()]
            if args.json:
                print(json.dumps(profiles, ensure_ascii=False, indent=2))
            else:
                for profile in profiles:
                    print(f"{profile['id']}: {profile['title']} ({profile['source_section']})")
                    print(f"  Herramientas: {', '.join(profile['tools']) or 'ninguna por apt; hardware dedicado'}")
                    print(f"  CWE: {', '.join(profile['cwe'])}")
            return 0
        if args.iot_profile and not args.check_only:
            raise ValueError("--iot-profile solo funciona con --check-only; es diagnóstico, no ejecuta el perfil")
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
            if args.iot_profile:
                iot = check_profile(args.iot_profile)
                payload["iot_profile"] = iot
                # --dry-run / --install-missing usan la lista combinada.
                combined = list(payload["missing_tools"])
                for name in iot["missing"]:
                    if name not in combined:
                        combined.append(name)
                payload["missing_tools"] = combined
                payload["missing_packages"] = payload["packages"] = list(
                    dict.fromkeys(payload["missing_packages"] + iot["packages"])
                )
            # --dry-run: solo imprimir los comandos apt, sin ejecutar nada.
            # No instala, aunque se pase --install-missing.
            if args.dry_run:
                commands = build_install_commands(payload["missing_tools"])
                payload["dry_run"] = True
                payload["dry_run_commands"] = [" ".join(c) for c in commands]
                payload["installed"] = False
                if args.json:
                    print(json.dumps(payload, ensure_ascii=False, indent=2))
                else:
                    tool.banner()
                    for command in commands:
                        print("[DRY-RUN] " + " ".join(command))
                    if not commands:
                        print("[DRY-RUN] No falta ninguna dependencia.")
                    print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 0
            # --install-missing: instalar solo con --check-only y solo
            # si el operador lo pidió explícitamente.
            if args.install_missing:
                if payload["missing_tools"]:
                    install_missing(payload["missing_tools"])
                    payload = check_environment(tool)
                    payload["installed"] = True
                    if payload["missing_tools"]:
                        print(
                            "[!] Tras instalar, siguen faltando: "
                            + ", ".join(payload["missing_tools"])
                        )
                        return 2
                else:
                    payload["installed"] = False
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                tool.banner()
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.install_missing or args.dry_run:
            raise ValueError("--install-missing y --dry-run solo funcionan con --check-only; no instalan nada en modo operacional")
        if args.no_menu:
            raise ValueError("--no-menu requiere una suborden operativa futura; no se inicia una acción implícita")
        print("[WIRELESS FLOW] scope -> validate -> diagnose -> scan/capture -> payload/callback -> cleanup")
        tool.run()
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"[!] Error de configuración: {exc}")
        return 2
