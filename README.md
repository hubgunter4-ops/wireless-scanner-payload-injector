# WIRELESS INJECTOR — Scanner, Handshake, Rogue AP & MITM

![WIRELESS INJECTOR banner](assets/banner.png)

![WIRELESS INJECTOR cover](assets/cover.png)

![Estado](https://img.shields.io/badge/estado-red%20team%20autorizado-6f42c1)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab)
![Plataforma](https://img.shields.io/badge/plataforma-Linux-111827)

WIRELESS INJECTOR conserva el propósito ofensivo del script recibido: escaneo Wi-Fi con `airodump-ng`, captura de handshakes WPA/WPA2, deauth para forzar asociación, configuración de rogue AP con `hostapd`/`dnsmasq`, redirección DNS, MITM mediante mitmproxy, generación de payloads JavaScript y recepción de callbacks.

> **Este repositorio no es un simulador.** Las rutas operativas conservan sus efectos reales. Ejecuta cada acción únicamente sobre redes, clientes y dispositivos incluidos en una autorización escrita. La persona que opera el tool es responsable de la ventana de pruebas, el alcance, la restauración de NetworkManager, el rollback de firewall y la eliminación de capturas.

## Mejoras aplicadas

La versión reforzada mantiene el menú y las acciones originales, pero valida interfaces, BSSID, canales, puertos, SSID, hosts de callback, rutas de captura y wordlists. La configuración de interfaz wireless, uplink y directorios se puede pasar por CLI o variables de entorno. El banner de código tiene tres variantes y se selecciona con `--banner-style 0|1|2`, `BANNER_STYLE=0|1|2` o una elección aleatoria cuando no se fija el estilo.

También se añadió seguimiento de reglas `iptables`, rollback en orden inverso, terminación con timeout de procesos, limpieza ante interrupción, detección de herramientas mediante `shutil.which`, errores explícitos de instalación y salida de colores solo cuando stdout es una TTY.

| Área | Resultado |
|---|---|
| Escaneo | Conserva `airodump-ng`, procesa CSV y valida duración e interfaz. |
| Handshake | Conserva captura y deauth autorizada; valida BSSID, canal y ESSID. |
| Rogue AP | Conserva `hostapd`, `dnsmasq`, forwarding y NAT; usa uplink configurable. |
| Payloads | Conserva plantillas y JavaScript personalizado; valida callback y evita saltos de línea en valores de configuración. |
| MITM | Conserva mitmproxy e inyección HTTP; registra y revierte reglas PREROUTING. |
| Callbacks | Conserva receptor HTTP y liga por defecto al host indicado por `CAPTURE_BIND`. |
| Cleanup | Detiene procesos y elimina reglas creadas por la instancia. |

## Requisitos

Se requiere Linux, Python 3.9+, privilegios root para las funciones de radio y las herramientas `aircrack-ng`, `hostapd`, `dnsmasq`, `mitmproxy`, `iptables`, `ifconfig`/`net-tools` y `iwconfig`. Se necesita un adaptador Wi-Fi compatible con modo monitor y un laboratorio inalámbrico aislado.

Instala dependencias en una estación desechable o snapshot:

```bash
sudo apt update
sudo apt install -y python3 python3-pip aircrack-ng hostapd dnsmasq iptables net-tools wireless-tools
python3 -m pip install --user mitmproxy
```

## Instalación y configuración

```bash
git clone <URL_DEL_REPOSITORIO>
cd wireless-scanner-payload-injector
python3 -m py_compile src/wireless_injector.py
```

Configura las interfaces sin escribirlas dentro del código:

```bash
export WIRELESS_INTERFACE=wlan0
export UPLINK_INTERFACE=eth0
export WIRELESS_OUTPUT_DIR="$PWD/wireless_captures"
export ROGUE_AP_DIR="$PWD/rogue_ap"
export PAYLOADS_DIR="$PWD/payloads_web"
```

Antes de abrir el menú, muestra el banner y comprueba la CLI sin activar radio:

```bash
BANNER_STYLE=1 python3 src/wireless_injector.py --show-banner --banner-style 1
```

La operación real se inicia con:

```bash
sudo -E python3 src/wireless_injector.py --interface wlan0 --uplink eth0 --banner-style 0
```

## Flujo ofensivo autorizado

El menú mantiene las opciones originales: escaneo de redes, captura de handshake, cracking con wordlist, configuración e inicio de rogue AP, creación de payload JavaScript, generación de script mitmproxy, inicio de proxy transparente, servidor de captura y ataque completo. Cada una puede modificar el entorno inalámbrico o la tabla de firewall.

Para capturar un handshake, valida previamente BSSID y canal contra el alcance firmado. Para rogue AP y MITM, registra la interfaz uplink, el rango DHCP, el puerto del proxy y los clientes de laboratorio. Para callbacks, utiliza una dirección privada del laboratorio y elimina `payloads_web/capturas.log` después de conservar la evidencia autorizada.

## Sanitización y rollback

Las interfaces aceptan solo nombres de hasta 15 caracteres formados por letras, números, punto, guion o guion bajo. MAC/BSSID exige seis octetos hexadecimales; el canal se restringe a 1–196; el puerto a 1–65535; el SSID se limita a 32 caracteres sin saltos de línea; y el callback acepta una IP o hostname sintácticamente acotado.

Los subprocesses se ejecutan como listas de argumentos, sin `shell=True`. Las reglas añadidas durante NAT o redirect se guardan como comandos de eliminación y se ejecutan en orden inverso al detener la operación. Los procesos `dnsmasq`, `hostapd` y mitmproxy se terminan con timeout y, si es necesario, `kill`.

La limpieza no puede garantizar la recuperación de todos los cambios externos si el sistema se apaga o un proceso modifica estado fuera de esta instancia. Conserva un snapshot, registra la tabla `iptables` antes y después, y valida NetworkManager y la interfaz managed al finalizar.

## TTPs y perspectiva purple team

| TTP ofensiva | Acción del tool | Telemetría defensiva |
|---|---|---|
| Network Service Scanning | `airodump-ng` y listado de redes | WIDS/WIPS, eventos del AP, aparición de interfaces monitor. |
| Adversary-in-the-Middle | Rogue AP, DNS spoofing y proxy transparente | Detección de SSID duplicado, cambios ARP/DNS, certificados y proxy anómalo. |
| Network Denial of Service | Deauth durante captura de handshake | Alertas de frames deauth, pérdida de clientes y cambios de canal. |
| Input/Content Injection | Inyección JS en respuestas HTTP | WAF, proxy, CSP, integridad de contenido y logs de navegador. |
| Credential Access | Cracking autorizado de capturas | Custodia de wordlists, procesos aircrack y controles de acceso a `.cap`. |

## Pruebas

Las pruebas unitarias solo cubren validación, banner y cleanup con procesos falsos; no abren sockets de radio ni llaman a `airmon-ng`, `aireplay-ng`, `hostapd`, `dnsmasq`, mitmproxy o iptables reales:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
python3 -m py_compile src/wireless_injector.py
```

## Evidencia visual

Las imágenes de `evidence/` documentan las tres variantes del banner y la salida de comprobaciones locales. No se generaron capturas de tráfico real ni se activó un rogue AP desde este repositorio durante la preparación.

| Archivo | Descripción |
|---|---|
| `evidence/01-banner-variant-0.png` | Banner ASCII y validaciones de configuración. |
| `evidence/02-banner-variant-1.png` | Banner Unicode y validaciones de BSSID/puerto. |
| `evidence/03-banner-variant-2.png` | Banner compacto y resumen de cleanup. |

Regenera las evidencias:

```bash
python3 tools/render_evidence.py
```

## Estructura

```text
.
├── assets/
│   ├── banner.png
│   ├── cover.png
│   └── visual-review.md
├── docs/
│   ├── authorization.md
│   ├── cleanup.md
│   └── operator-checklist.md
├── evidence/
│   ├── 01-banner-variant-0.png
│   ├── 02-banner-variant-1.png
│   ├── 03-banner-variant-2.png
│   └── visual-review.md
├── src/
│   ├── wireless_injector.py
│   └── wireless_injector.py.original
├── tests/test_wireless.py
├── tools/render_evidence.py
└── README.md
```

## Referencias

[1]: https://www.aircrack-ng.org/ "Aircrack-ng official documentation"
[2]: https://www.mitmproxy.org/ "mitmproxy official documentation"
[3]: https://hostap.epitest.fi/hostapd/ "hostapd project documentation"
[4]: https://attack.mitre.org/techniques/T1557/ "MITRE ATT&CK — Adversary-in-the-Middle"
[5]: https://attack.mitre.org/techniques/T1498/ "MITRE ATT&CK — Network Denial of Service"
