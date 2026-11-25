#!/usr/bin/env python3
"""Pruebas de UI del dashboard; nunca invocan herramientas inalámbricas."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wireless_tool import cli  # noqa: E402
from wireless_tool.dashboard import (  # noqa: E402
    EXECUTOR_GROUPS,
    PROFILE_KEYS,
    TABS,
    display_dashboard,
    render_dashboard,
    run_check_with_spinner,
)
from wireless_tool.dependencies import IOT_TOOL_PACKAGES, REQUIRED_TOOLS  # noqa: E402


class DashboardRenderingTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "interface": "wlan0",
            "monitor_interface": "wlan0mon",
            "uplink_interface": "eth0",
            "required_tools": {name: None for name in REQUIRED_TOOLS},
            "profile_tools": {},
            "note": "solo diagnóstico",
        }
        self.profiles = {
            profile_id: {"ready": False}
            for profile_id in PROFILE_KEYS
        }

    def test_cuatro_pestanas_explicitas(self):
        self.assertEqual(TABS, ("RESUMEN", "EJECUTORES", "PERFILES", "MONITOR"))
        for index, name in enumerate(TABS):
            page = render_dashboard(self.payload, self.profiles, active=index)
            self.assertIn(name, page)
            self.assertIn("SOLO LECTURA", page)
            self.assertIn("RADIO INACTIVA", page)
            self.assertIn("MODO OPERACIONAL", page)
        summary = render_dashboard(self.payload, self.profiles, active=0)
        self.assertIn("MINI MONITOR PATH", summary)
        self.assertIn("4 MONITOR", summary)
        self.assertIn("0/16", summary)

    def test_distribucion_cubre_ejecutores_base_e_iot_sin_duplicados(self):
        grouped = [name for _, names in EXECUTOR_GROUPS for name in names]
        self.assertEqual(len(grouped), len(set(grouped)))
        self.assertEqual(set(grouped), set(REQUIRED_TOOLS) | set(IOT_TOOL_PACKAGES))
        self.assertEqual(len(EXECUTOR_GROUPS), 3)

    def test_modo_no_interactivo_imprime_todas_las_pestanas(self):
        output = io.StringIO()
        display_dashboard(self.payload, self.profiles, stream=output)
        text = output.getvalue()
        self.assertTrue(all(name in text for name in TABS))
        self.assertIn("airmon-ng", text)
        self.assertIn("BLE", text)
        self.assertIn("Método: shutil.which", text)
        self.assertIn("Subprocesos: ninguno", text)

    def test_monitor_actualiza_snapshot_sin_salir_de_la_pestana(self):
        class TtyBuffer(io.StringIO):
            def isatty(self):
                return True

        updated = dict(self.payload)
        updated["required_tools"] = {
            name: ("/usr/local/bin/airmon-ng" if name == "airmon-ng" else None)
            for name in REQUIRED_TOOLS
        }
        choices = iter(["4", "r", "q"])
        refresh_calls = []
        output = TtyBuffer()

        def refresh():
            refresh_calls.append(True)
            return {"payload": updated, "profiles": self.profiles}

        display_dashboard(
            self.payload,
            self.profiles,
            stream=output,
            input_fn=lambda _prompt: next(choices),
            refresh_fn=refresh,
        )
        self.assertEqual(refresh_calls, [True])
        self.assertIn("/usr/local/bin/airmon-ng", output.getvalue())
        self.assertIn("\033[?25h", output.getvalue())

    def test_spinner_no_tty_llama_chequeo_sin_animar(self):
        calls = []

        def check():
            calls.append(True)
            return {"ok": True}

        output = io.StringIO()
        self.assertEqual(run_check_with_spinner(check, stream=output), {"ok": True})
        self.assertEqual(calls, [True])
        self.assertEqual(output.getvalue(), "")


class DashboardSafetyTests(unittest.TestCase):
    def test_cli_dashboard_no_crea_carpetas_ni_llama_motor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "captures"
            rogue_dir = Path(temp_dir) / "rogue"
            payload_dir = Path(temp_dir) / "payloads"
            env = {
                "WIRELESS_OUTPUT_DIR": str(output_dir),
                "ROGUE_AP_DIR": str(rogue_dir),
                "PAYLOADS_DIR": str(payload_dir),
            }
            with patch.dict(os.environ, env), patch.object(
                cli, "check_environment", return_value={
                    "interface": "wlan0",
                    "monitor_interface": "wlan0mon",
                    "uplink_interface": "eth0",
                    "required_tools": {name: None for name in REQUIRED_TOOLS},
                    "note": "solo diagnóstico",
                }
            ), patch.object(
                cli, "check_profile", return_value={"ready": False, "tools_found": {}}
            ), patch.object(
                cli.WirelessTool, "run", side_effect=AssertionError("No debe arrancar el motor")
            ), redirect_stdout(io.StringIO()):
                result = cli.main([
                    "--dashboard",
                    "--no-animation",
                    "--interface", "wlan0",
                    "--uplink", "eth0",
                ])

            self.assertEqual(result, 0)
            self.assertFalse(output_dir.exists())
            self.assertFalse(rogue_dir.exists())
            self.assertFalse(payload_dir.exists())

    def test_dashboard_rechaza_instalacion_o_salida_json(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = cli.main(["--dashboard", "--install-missing"])
        self.assertEqual(result, 2)
        self.assertIn("--dashboard", output.getvalue())


if __name__ == "__main__":
    unittest.main()
