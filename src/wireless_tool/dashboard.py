"""Dashboard visual de solo lectura para diagnósticos locales.

Este módulo solo formatea resultados de ``shutil.which``. No activa radio,
no instala paquetes y no ejecuta herramientas de terceros.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable
from typing import TextIO

from .dependencies import IOT_TOOL_PACKAGES, REQUIRED_TOOLS
from .iot_profiles import get_profile, list_profiles

TABS = ("RESUMEN", "EJECUTORES", "PERFILES", "MONITOR")
TAB_KEYS = {"1": 0, "2": 1, "3": 2, "4": 3}

# Grupos cortos y estables; la TUI muestra disponibilidad, nunca ejecuta estos nombres.
EXECUTOR_GROUPS = (
    ("WIRELESS", ("airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng")),
    ("LAB", ("hostapd", "dnsmasq", "mitmproxy", "iptables")),
    ("IOT / ANALISIS", tuple(IOT_TOOL_PACKAGES)),
)
PROFILE_KEYS = tuple(list_profiles())
NEON_MAGENTA = "38;2;255;48;220"
NEON_RED = "38;2;255;42;78"
DIM_RED = "38;2;112;35;54"
DARK_BACKGROUND = "48;2;7;3;9"


def _supports_color(stream: TextIO) -> bool:
    return bool(
        getattr(stream, "isatty", lambda: False)()
        and os.getenv("TERM", "") != "dumb"
        and not os.getenv("NO_COLOR")
    )


def _paint(text: str, code: str, enabled: bool) -> str:
    # Return to the neon-magenta base foreground while preserving the screen background.
    return f"\033[{code}m{text}\033[22;{NEON_MAGENTA}m" if enabled else text


def _available(tool_map: dict, name: str) -> bool:
    return bool(tool_map.get(name))


def _status(tool_map: dict, name: str, color: bool) -> str:
    if _available(tool_map, name):
        return _paint("● DISPONIBLE", "32", color)
    return _paint("○ AUSENTE", NEON_RED, color)


def _tabs(active: int, color: bool) -> str:
    labels = []
    for index, name in enumerate(TABS):
        label = f" {index + 1} {name} "
        labels.append(_paint(label, f"1;{NEON_MAGENTA}" if index == active else DIM_RED, color))
    return "  ".join(labels)


def _base_tools(payload: dict) -> dict:
    tools = payload.get("required_tools", payload.get("tools", {}))
    return tools if isinstance(tools, dict) else {}


def _all_tool_paths(payload: dict) -> dict:
    tools = dict(_base_tools(payload))
    for profile_tools in payload.get("profile_tools", {}).values():
        if isinstance(profile_tools, dict):
            tools.update(profile_tools)
    return tools


def _render_summary(payload: dict, profile_checks: dict, color: bool) -> list[str]:
    tools = _base_tools(payload)
    total = len(REQUIRED_TOOLS)
    ready = sum(_available(tools, name) for name in REQUIRED_TOOLS)
    missing = total - ready
    ratio = ready / total if total else 0
    filled = round(ratio * 18)
    bar = "█" * filled + "░" * (18 - filled)
    percent = round(ratio * 100)
    monitor_tools = _all_tool_paths(payload)
    monitored_names = tuple(name for _, names in EXECUTOR_GROUPS for name in names)
    monitor_ready = sum(bool(monitor_tools.get(name)) for name in monitored_names)
    monitor_total = len(monitored_names)
    monitor_filled = round((monitor_ready / monitor_total) * 12) if monitor_total else 0
    monitor_bar = "█" * monitor_filled + "░" * (12 - monitor_filled)
    lines = [
        _paint("W I R E L E S S   L A B   ·   DIAGNOSTICO LOCAL", NEON_MAGENTA, color),
        "",
        f"  Interfaz: {payload.get('interface', '—')}    Uplink: {payload.get('uplink_interface', '—')}",
        f"  Monitor:  {payload.get('monitor_interface', '—')}",
        "",
        f"  EJECUTORES BASE     {ready}/{total} disponibles     {_paint(bar, NEON_MAGENTA, color)} {percent}%",
        f"  PENDIENTES          {missing}     PERFILES IoT     {len(profile_checks)}",
        "",
        f"  MINI MONITOR PATH   {monitor_ready}/{monitor_total}     {_paint(monitor_bar, NEON_RED, color)}  →  4 MONITOR",
        "  Pulsa r en Monitor para repetir estas comprobaciones locales.",
        "",
        "  Presencia local en PATH; no se lanzan ejecutables ni se instalan paquetes.",
    ]
    if payload.get("note"):
        lines.extend(["", f"  Nota: {payload['note']}"])
    return lines


def _render_executors(payload: dict, color: bool) -> list[str]:
    tools = _all_tool_paths(payload)
    lines = [_paint("DISTRIBUCION DE EJECUTORES · ESTADO DETECTADO, NO EJECUTADO", NEON_MAGENTA, color), ""]
    for group, names in EXECUTOR_GROUPS:
        lines.append(_paint(f"  {group}", NEON_RED, color))
        for name in names:
            lines.append(f"    {name:<18} {_status(tools, name, color)}")
        lines.append("")
    lines.append("  Revisión local de presencia; las herramientas no se invocan desde esta vista.")
    return lines


def _render_profiles(profile_checks: dict, color: bool) -> list[str]:
    lines = [_paint("PERFILES IoT · DEPENDENCIAS Y HARDWARE", NEON_MAGENTA, color), ""]
    for profile_id in PROFILE_KEYS:
        check = profile_checks.get(profile_id, {})
        profile = get_profile(profile_id)
        if check.get("ready"):
            state = _paint("LISTO", "32", color)
        elif profile.get("hardware_required"):
            state = _paint("HARDWARE", NEON_RED, color)
        elif check:
            state = _paint("REVISAR", NEON_RED, color)
        else:
            state = _paint("SIN DATOS", DIM_RED, color)
        title = profile["title"]
        lines.append(f"  {profile_id:<10} {state}  {title}")
    lines.extend([
        "",
        "  Perfiles informativos; no ejecutan pruebas ni interactúan con dispositivos.",
    ])
    return lines


def _render_monitor(payload: dict, color: bool) -> list[str]:
    tools = _all_tool_paths(payload)
    lines = [
        _paint("MONITOR LOCAL · REPETICION DEL DIAGNOSTICO", NEON_MAGENTA, color),
        "",
        "  Método: shutil.which    Alcance: presencia de binarios en PATH",
        "  Radio: inactiva         Subprocesos: ninguno",
        "",
    ]
    for group, names in EXECUTOR_GROUPS:
        lines.append(_paint(f"  {group}", NEON_RED, color))
        for name in names:
            path = tools.get(name)
            result = str(path) if path else "AUSENTE"
            if len(result) > 44:
                result = "…" + result[-43:]
            lines.append(f"    {name:<18} → {result}")
        lines.append("")
    lines.append("  Pulsa r para repetir el mismo chequeo de solo lectura.")
    return lines


def render_dashboard(
    payload: dict,
    profile_checks: dict,
    active: int = 0,
    color: bool = False,
) -> str:
    """Devuelve una pestaña legible; no realiza comprobaciones ni efectos."""
    if active not in range(len(TABS)):
        raise ValueError("Pestaña desconocida")
    width = 74
    rule = _paint("─" * width, NEON_RED, color)
    logo = (
        _paint("◆", NEON_MAGENTA, color)
        + _paint("◇", NEON_RED, color)
        + _paint("◆", NEON_MAGENTA, color)
        + "  "
        + _paint(")))", NEON_RED, color)
    )
    content = (
        _render_summary(payload, profile_checks, color)
        if active == 0
        else _render_executors(payload, color)
        if active == 1
        else _render_profiles(profile_checks, color)
        if active == 2
        else _render_monitor(payload, color)
    )
    return "\n".join([
        rule,
        f"  {logo}  WIRELESS INJECTOR  /  DIAGNOSTICO SEGURO  v2.2.0",
        "  " + _tabs(active, color),
        rule,
        *content,
        _paint("  DASHBOARD: SOLO LECTURA · RADIO INACTIVA · SIN CAMBIOS", NEON_MAGENTA, color),
        _paint("  MODO OPERACIONAL: puede invocar herramientas externas y modificar", NEON_RED, color),
        _paint("  el sistema según la acción (radio, procesos, archivos, red o firewall).", NEON_RED, color),
        rule,
        "  Navegar: 1/2/3/4   ·   r Actualizar monitor   ·   q Salir"
        if sys.stdin.isatty()
        else "  Navegación estática · modo no interactivo",
        "",
    ])


def run_check_with_spinner(
    check: Callable[[], dict],
    stream: TextIO | None = None,
    enabled: bool = True,
) -> dict:
    """Ejecuta un chequeo local con un spinner magenta/rojo solo en TTY."""
    stream = stream or sys.stderr
    if not enabled or not getattr(stream, "isatty", lambda: False)():
        return check()

    result: dict = {}
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            result.update(check())
        except BaseException as exc:  # volver a elevar en el hilo principal
            errors.append(exc)

    thread = threading.Thread(target=worker, name="diagnostic-check", daemon=True)
    thread.start()
    frames = ("◆", "◇", "◈", "◇")
    frame = 0
    color = _supports_color(stream)
    while thread.is_alive():
        tint = NEON_MAGENTA if frame % 2 == 0 else NEON_RED
        glyph = _paint(frames[frame % len(frames)], tint, color)
        label = _paint("Comprobando entorno (solo lectura)…", NEON_MAGENTA, color)
        stream.write(f"\r{glyph} {label}")
        stream.flush()
        frame += 1
        time.sleep(0.08)
    thread.join()
    stream.write("\r" + " " * 64 + "\r")
    stream.flush()
    if errors:
        raise errors[0]
    return result


def display_dashboard(
    payload: dict,
    profile_checks: dict,
    stream: TextIO | None = None,
    input_fn: Callable[[str], str] = input,
    refresh_fn: Callable[[], dict] | None = None,
) -> None:
    """Muestra las pestañas; refrescar solo repite el diagnóstico de PATH."""
    stream = stream or sys.stdout
    color = _supports_color(stream)
    interactive = bool(getattr(stream, "isatty", lambda: False)())
    if not interactive:
        for index in range(len(TABS)):
            stream.write(render_dashboard(payload, profile_checks, index, color))
        return

    selected = 0
    cursor_hidden = False
    background = f"\033[{DARK_BACKGROUND}m" if color else ""
    if color:
        stream.write("\033[?25l")
        cursor_hidden = True
    try:
        while True:
            stream.write(f"{background}\033[2J\033[H")
            stream.write(render_dashboard(payload, profile_checks, selected, color))
            stream.write("\033[0m")
            choice = input_fn("Selecciona pestaña [1/2/3/4], r actualizar o q salir: ").strip().lower()
            if choice == "q":
                break
            if choice in TAB_KEYS:
                selected = TAB_KEYS[choice]
            elif choice == "r" and refresh_fn is not None:
                refreshed = refresh_fn()
                payload = refreshed["payload"]
                profile_checks = refreshed["profiles"]
    finally:
        if cursor_hidden:
            stream.write("\033[0m\033[?25h")
        stream.flush()
