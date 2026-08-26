#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wireless_tool.engine import BANNER_VARIANTS, WirelessTool  # noqa: E402


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if not self.terminated else 0

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


class WirelessProductionTests(unittest.TestCase):
    def make_tool(self, create_dirs=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        os.environ["WIRELESS_OUTPUT_DIR"] = str(Path(directory.name) / "captures")
        os.environ["ROGUE_AP_DIR"] = str(Path(directory.name) / "rogue")
        os.environ["PAYLOADS_DIR"] = str(Path(directory.name) / "payloads")
        self.addCleanup(lambda: [os.environ.pop(key, None) for key in ("WIRELESS_OUTPUT_DIR", "ROGUE_AP_DIR", "PAYLOADS_DIR")])
        return WirelessTool(interface="wlan0", uplink_interface="eth0", banner_style=0, create_dirs=create_dirs)

    def test_valid_values_are_normalized(self):
        self.assertEqual(WirelessTool._validate_mac("aa:bb:cc:dd:ee:ff"), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(WirelessTool._validate_channel("6"), 6)
        self.assertEqual(WirelessTool._validate_port("8080"), 8080)
        self.assertEqual(WirelessTool._validate_ssid("Lab-AP"), "Lab-AP")
        self.assertEqual(WirelessTool._validate_interface("wlan0"), "wlan0")

    def test_invalid_values_are_rejected(self):
        invalid = (
            (WirelessTool._validate_mac, "not-a-mac"),
            (WirelessTool._validate_channel, "0"),
            (WirelessTool._validate_port, "70000"),
            (WirelessTool._validate_ssid, "lab\nssid"),
            (WirelessTool._validate_interface, "../../tmp"),
            (WirelessTool._validate_callback_host, "bad host"),
        )
        for validator, value in invalid:
            with self.subTest(validator=validator.__name__):
                with self.assertRaises(ValueError):
                    validator(value)

    def test_banner_variants_are_unique(self):
        self.assertEqual(len(BANNER_VARIANTS), 3)
        self.assertEqual(len(set(BANNER_VARIANTS)), 3)
        self.make_tool()

    def test_constructor_can_be_side_effect_free(self):
        tool = self.make_tool(create_dirs=False)
        self.assertFalse(Path(tool.output_dir).exists())

    def test_process_cleanup_and_firewall_rollback(self):
        tool = self.make_tool()
        process = FakeProcess()
        tool.procesos["test"] = process
        with patch("wireless_tool.engine.subprocess.run") as run:
            tool.firewall_rules.append(["iptables", "-D", "FORWARD"])
            tool.detener_todo()
            run.assert_called_once_with(["iptables", "-D", "FORWARD"], check=False, capture_output=True)
        self.assertTrue(process.terminated)
        self.assertEqual(tool.procesos, {})

    def test_check_only_does_not_require_root_or_radio(self):
        result = subprocess.run(
            [sys.executable, "src/wireless_injector.py", "--check-only", "--json", "--interface", "wlan0", "--uplink", "eth0"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["interface"], "wlan0")
        self.assertFalse(payload["radio_started"])


if __name__ == "__main__":
    unittest.main()
