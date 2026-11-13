#!/usr/bin/env python3
"""Tests de dependencias del sistema: mapa, deduplicación, dry-run,
fallos y verificación posterior. Todo con mocks: nunca se ejecuta
apt-get, airmon-ng ni ninguna herramienta inalámbrica, y nunca se
activa radio.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wireless_tool import dependencies  # noqa: E402
from wireless_tool.dependencies import (  # noqa: E402
    TOOL_PACKAGES,
    build_install_commands,
    check_dependencies,
    install_missing,
    packages_for_tools,
)


def _ok_run(*args, **kwargs):
    return MagicMock(returncode=0)


def _fail_run(*args, **kwargs):
    return MagicMock(returncode=1)


class MapTests(unittest.TestCase):
    def test_airmon_no_es_paquete(self):
        # El defecto original: apt-get install -y airmon-ng ...
        self.assertEqual(TOOL_PACKAGES["airmon-ng"], "aircrack-ng")
        self.assertEqual(TOOL_PACKAGES["airodump-ng"], "aircrack-ng")
        self.assertEqual(TOOL_PACKAGES["aireplay-ng"], "aircrack-ng")
        self.assertEqual(TOOL_PACKAGES["aircrack-ng"], "aircrack-ng")
        self.assertNotIn("airmon-ng", set(TOOL_PACKAGES.values()))
        self.assertNotIn("airodump-ng", set(TOOL_PACKAGES.values()))
        self.assertNotIn("aireplay-ng", set(TOOL_PACKAGES.values()))

    def test_mapa_completo(self):
        self.assertEqual(TOOL_PACKAGES["hostapd"], "hostapd")
        self.assertEqual(TOOL_PACKAGES["dnsmasq"], "dnsmasq")
        self.assertEqual(TOOL_PACKAGES["mitmproxy"], "mitmproxy")
        self.assertEqual(TOOL_PACKAGES["iptables"], "iptables")

    def test_deduplicacion(self):
        self.assertEqual(
            packages_for_tools(["airmon-ng", "airodump-ng", "aireplay-ng"]),
            ["aircrack-ng"],
        )
        self.assertEqual(
            packages_for_tools(
                ["airmon-ng", "hostapd", "airodump-ng", "dnsmasq", "hostapd"]
            ),
            ["aircrack-ng", "hostapd", "dnsmasq"],
        )

    def test_herramienta_desconocida(self):
        with self.assertRaises(ValueError):
            packages_for_tools(["no-existe-ng"])


class CheckTests(unittest.TestCase):
    def test_check_dependencies_devuelve_missing_y_paquetes(self):
        def which(name):
            return "/usr/bin/" + name if name in ("iptables", "hostapd") else None

        with patch("wireless_tool.dependencies.shutil.which", side_effect=which):
            result = check_dependencies()
        self.assertEqual(result["tools"]["iptables"], "/usr/bin/iptables")
        self.assertIsNone(result["tools"]["airmon-ng"])
        self.assertIn("airmon-ng", result["missing"])
        self.assertIn("airodump-ng", result["missing"])
        # aircrack-ng cubre los 4 binarios aircrack en un solo paquete.
        self.assertEqual(
            result["packages"],
            ["aircrack-ng", "dnsmasq", "mitmproxy"],
        )
        self.assertEqual(result["missing_packages"], result["packages"])

    def test_check_sin_faltantes(self):
        with patch(
            "wireless_tool.dependencies.shutil.which",
            return_value="/usr/bin/tool",
        ):
            result = check_dependencies()
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["packages"], [])


class InstallTests(unittest.TestCase):
    def test_dry_run_no_ejecuta_subprocess(self):
        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=0),
            patch(
                "wireless_tool.dependencies.subprocess.run"
            ) as run,
            patch("wireless_tool.dependencies.shutil.which") as which,
        ):
            which.return_value = "/usr/bin/apt-get"
            self.assertTrue(
                install_missing(["airmon-ng", "hostapd"], dry_run=True)
            )
        run.assert_not_called()

    def test_dry_run_imprime_apt_update_e_install(self):
        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=0),
            patch("wireless_tool.dependencies.subprocess.run") as run,
            patch("builtins.print") as printed,
        ):
            install_missing(["airmon-ng", "airodump-ng"], dry_run=True)
        run.assert_not_called()
        text = " ".join(str(c) for c in printed.call_args_list)
        self.assertIn("apt-get update", text)
        self.assertIn("apt-get install -y aircrack-ng", text)
        # Un solo paquete, no los nombres de los binarios.
        self.assertNotIn("airmon-ng", text)
        self.assertNotIn("airodump-ng", text)

    def test_build_commands_usa_apt_update_primero(self):
        with patch("wireless_tool.dependencies.os.geteuid", return_value=0):
            commands = build_install_commands(["airmon-ng", "hostapd"])
        self.assertEqual(commands[0], ["apt-get", "update"])
        self.assertEqual(
            commands[1], ["apt-get", "install", "-y", "aircrack-ng", "hostapd"]
        )

    def test_build_commands_usa_sudo_si_no_es_root(self):
        def which(name):
            return "/usr/bin/sudo" if name == "sudo" else None

        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=1000),
            patch("wireless_tool.dependencies.shutil.which", side_effect=which),
        ):
            commands = build_install_commands(["hostapd"])
        self.assertEqual(commands[0], ["sudo", "apt-get", "update"])
        self.assertEqual(
            commands[1], ["sudo", "apt-get", "install", "-y", "hostapd"]
        )

    def test_install_fallido_lanza_runtimeerror(self):
        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=0),
            patch(
                "wireless_tool.dependencies.shutil.which",
                return_value="/usr/bin/apt-get",
            ),
            patch(
                "wireless_tool.dependencies.subprocess.run",
                side_effect=_fail_run,
            ),
        ):
            with self.assertRaises(RuntimeError):
                install_missing(["hostapd"])

    def test_sin_apt_get_lanza_runtimeerror(self):
        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=0),
            patch(
                "wireless_tool.dependencies.shutil.which", return_value=None
            ),
            patch(
                "wireless_tool.dependencies.subprocess.run"
            ) as run,
        ):
            with self.assertRaises(RuntimeError):
                install_missing(["hostapd"])
        run.assert_not_called()

    def test_sin_root_ni_sudo_lanza_runtimeerror(self):
        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=1000),
            patch(
                "wireless_tool.dependencies.shutil.which", return_value=None
            ),
            patch(
                "wireless_tool.dependencies.subprocess.run"
            ) as run,
        ):
            with self.assertRaises(RuntimeError):
                install_missing(["hostapd"])
        run.assert_not_called()

    def test_verificacion_posterior_falla_si_sigue_faltando(self):
        # apt-get "tiene éxito" pero la herramienta sigue sin estar en PATH.
        def which(name):
            return "/usr/bin/apt-get" if name == "apt-get" else None

        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=0),
            patch(
                "wireless_tool.dependencies.shutil.which", side_effect=which
            ),
            patch(
                "wireless_tool.dependencies.subprocess.run",
                side_effect=_ok_run,
            ),
        ):
            with self.assertRaises(RuntimeError):
                install_missing(["hostapd"])

    def test_verificacion_posterior_ok(self):
        # Tras instalar, which ya encuentra la herramienta.
        state = {"installed": False}

        def which(name):
            if name == "apt-get":
                return "/usr/bin/apt-get"
            if name == "hostapd" and state["installed"]:
                return "/usr/sbin/hostapd"
            return None

        def run(cmd, check=False):
            state["installed"] = True
            return MagicMock(returncode=0)

        with (
            patch("wireless_tool.dependencies.os.geteuid", return_value=0),
            patch(
                "wireless_tool.dependencies.shutil.which", side_effect=which
            ),
            patch(
                "wireless_tool.dependencies.subprocess.run", side_effect=run
            ) as run_mock,
        ):
            self.assertTrue(install_missing(["hostapd"]))
        # update + install, nada más.
        self.assertEqual(run_mock.call_count, 2)
        self.assertEqual(
            run_mock.call_args_list[1].args[0],
            ["apt-get", "install", "-y", "hostapd"],
        )

    def test_sin_faltantes_no_ejecuta_nada(self):
        with patch(
            "wireless_tool.dependencies.subprocess.run"
        ) as run:
            self.assertTrue(install_missing([]))
        run.assert_not_called()


class EngineInstallTests(unittest.TestCase):
    def test_instalar_herramientas_usa_mapa_no_binarios(self):
        from wireless_tool.engine import WirelessTool

        tool = WirelessTool(
            interface="wlan0", banner_style=0, create_dirs=False
        )
        with patch(
            "wireless_tool.engine.install_missing", return_value=True
        ) as install:
            self.assertTrue(
                tool.instalar_herramientas(["airmon-ng", "airodump-ng"])
            )
        # install_missing recibe los binarios; es dependencies quien
        # los traduce a paquetes. Se comprueba que engine no construye
        # por su cuenta "apt-get install -y airmon-ng".
        install.assert_called_once_with(
            ["airmon-ng", "airodump-ng"], dry_run=False, use_sudo=None
        )

    def test_check_tools_no_pregunta_por_defecto(self):
        from wireless_tool.engine import WirelessTool

        tool = WirelessTool(
            interface="wlan0", banner_style=0, create_dirs=False
        )
        with (
            patch(
                "wireless_tool.engine.check_dependencies",
                return_value={
                    "tools": {"airmon-ng": None},
                    "missing": ["airmon-ng"],
                    "packages": ["aircrack-ng"],
                    "missing_packages": ["aircrack-ng"],
                },
            ),
            patch("builtins.input") as input_mock,
        ):
            missing = tool.check_tools()
        input_mock.assert_not_called()
        self.assertEqual(missing, ["airmon-ng"])


class CliDryRunTests(unittest.TestCase):
    def test_cli_check_only_dry_run_no_ejecuta_subprocess(self):
        from wireless_tool.cli import main

        with (
            patch("wireless_tool.dependencies.shutil.which") as which,
            patch(
                "wireless_tool.dependencies.subprocess.run"
            ) as run,
            patch("wireless_tool.dependencies.os.geteuid", return_value=0),
        ):
            which.return_value = None
            rc = main(
                [
                    "--check-only",
                    "--json",
                    "--dry-run",
                    "--install-missing",
                ]
            )
        self.assertEqual(rc, 0)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
