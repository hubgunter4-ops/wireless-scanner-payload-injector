#!/usr/bin/env python3
"""Tests de perfiles IoT: datos de la guía, mapa de dependencias,
chequeo con mocks y CLI. Nunca se ejecuta apt-get, airmon-ng ni
ninguna herramienta inalámbrica, y nunca se activa radio.
"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wireless_tool import cli, iot_profiles  # noqa: E402
from wireless_tool.dependencies import (  # noqa: E402
    IOT_TOOL_PACKAGES,
    REQUIRED_TOOLS,
    packages_for_tools,
)
from wireless_tool.iot_profiles import (  # noqa: E402
    IOT_PROFILES,
    all_tools_known,
    check_profile,
    get_profile,
    list_profiles,
)


class ProfilesTests(unittest.TestCase):
    def test_seis_perfiles(self):
        self.assertEqual(
            list_profiles(),
            ["web-api", "firmware", "wifi", "ble", "zigbee", "sdr"],
        )

    def test_cada_perfil_tiene_cwe_capec_y_fuente(self):
        for pid in list_profiles():
            profile = get_profile(pid)
            self.assertTrue(profile["cwe"], pid)
            self.assertTrue(profile["capec"], pid)
            self.assertTrue(profile["skills"], pid)
            self.assertTrue(profile["steps"], pid)
            self.assertEqual(profile["source"]["commit"][:7], "4f09668")
            self.assertEqual(
                profile["source"]["repo"], "uqbarun/uqbarun.github.io"
            )

    def test_cwe_por_seccion_de_la_guia(self):
        self.assertEqual(
            get_profile("web-api")["cwe"],
            ["CWE-200", "CWE-287", "CWE-89", "CWE-94"],
        )
        self.assertEqual(
            get_profile("firmware")["cwe"],
            ["CWE-327", "CWE-78", "CWE-494", "CWE-119"],
        )
        self.assertIn("CWE-798", get_profile("wifi")["cwe"])
        self.assertIn("CWE-798", get_profile("ble")["cwe"])
        self.assertIn("CWE-798", get_profile("zigbee")["cwe"])
        self.assertIn("CWE-798", get_profile("sdr")["cwe"])

    def test_perfil_desconocido(self):
        with self.assertRaises(ValueError):
            get_profile("no-existe")

    def test_todas_las_herramientas_tienen_paquete(self):
        self.assertTrue(all_tools_known())


class MapTests(unittest.TestCase):
    def test_mapa_iot(self):
        self.assertEqual(IOT_TOOL_PACKAGES["tshark"], "tshark")
        self.assertEqual(IOT_TOOL_PACKAGES["nmap"], "nmap")
        self.assertEqual(IOT_TOOL_PACKAGES["binwalk"], "binwalk")
        self.assertEqual(IOT_TOOL_PACKAGES["bluetoothctl"], "bluez")
        self.assertEqual(IOT_TOOL_PACKAGES["hcitool"], "bluez")
        self.assertEqual(IOT_TOOL_PACKAGES["gatttool"], "bluez")
        self.assertEqual(IOT_TOOL_PACKAGES["rtl_sdr"], "rtl-sdr")
        self.assertEqual(IOT_TOOL_PACKAGES["hackrf_info"], "hackrf")

    def test_deduplicacion_bluez(self):
        self.assertEqual(
            packages_for_tools(["bluetoothctl", "hcitool", "gatttool"]),
            ["bluez"],
        )

    def test_base_no_cambia(self):
        # El --check-only base sigue siendo solo Wi-Fi.
        self.assertEqual(
            list(REQUIRED_TOOLS),
            [
                "airmon-ng",
                "airodump-ng",
                "aireplay-ng",
                "aircrack-ng",
                "hostapd",
                "dnsmasq",
                "mitmproxy",
                "iptables",
            ],
        )
        self.assertNotIn("tshark", REQUIRED_TOOLS)
        self.assertNotIn("binwalk", REQUIRED_TOOLS)


class CheckTests(unittest.TestCase):
    def test_check_ble_todo_presente(self):
        with patch.object(
            iot_profiles.shutil, "which", return_value="/usr/bin/x"
        ):
            result = check_profile("ble")
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["packages"], [])
        self.assertTrue(result["ready"])

    def test_check_ble_todo_ausente(self):
        with patch.object(iot_profiles.shutil, "which", return_value=None):
            result = check_profile("ble")
        self.assertEqual(
            result["missing"], ["bluetoothctl", "hcitool", "gatttool"]
        )
        self.assertEqual(result["packages"], ["bluez"])
        self.assertFalse(result["ready"])

    def test_zigbee_sin_paquete_y_con_hardware(self):
        profile = get_profile("zigbee")
        self.assertEqual(profile["tools"], [])
        self.assertTrue(profile.get("hardware_required"))
        self.assertIn("CC2531", profile["hardware"])
        with patch.object(iot_profiles.shutil, "which", return_value=None):
            result = check_profile("zigbee")
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["packages"], [])
        # No se da por listo: exige hardware dedicado.
        self.assertFalse(result["ready"])

    def test_check_wifi_reutiliza_base(self):
        with patch.object(iot_profiles.shutil, "which", return_value=None):
            result = check_profile("wifi")
        self.assertEqual(
            result["missing"],
            ["airmon-ng", "airodump-ng", "aircrack-ng", "tshark"],
        )
        self.assertEqual(result["packages"], ["aircrack-ng", "tshark"])


class CliTests(unittest.TestCase):
    def test_list_iot_profiles(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["--list-iot-profiles", "--banner-style", "0"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        for pid in list_profiles():
            self.assertIn(pid, text)

    def test_iot_profile_sin_check_only_da_error(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["--iot-profile", "ble", "--banner-style", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--iot-profile", out.getvalue())

    def test_iot_profile_con_check_only_json(self):
        # which=None en todo: base + perfil faltan, pero no se ejecuta nada.
        with patch("wireless_tool.cli.check_dependencies") as mock_deps, patch(
            "wireless_tool.iot_profiles.shutil.which", return_value=None
        ):
            mock_deps.return_value = {
                "tools": {},
                "missing": [],
                "packages": [],
                "missing_packages": [],
            }
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(
                    [
                        "--check-only",
                        "--json",
                        "--iot-profile",
                        "ble",
                        "--banner-style",
                        "0",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertIn('"iot_profile"', out.getvalue())
        self.assertIn('"ble"', out.getvalue())
        self.assertIn('"bluez"', out.getvalue())

    def test_iot_profile_desconocido_da_error_argparse(self):
        with self.assertRaises(SystemExit):
            cli.main(["--check-only", "--iot-profile", "no-existe"])


if __name__ == "__main__":
    unittest.main()
