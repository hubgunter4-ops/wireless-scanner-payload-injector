# Autorización del wireless engagement

Este tool cambia el estado de una interfaz Wi-Fi, puede emitir tramas deauth, levantar un AP, modificar forwarding/NAT y observar tráfico de clientes. La autorización debe cubrir explícitamente cada una de esas técnicas; una autorización para escaneo no incluye deauth, rogue AP, MITM ni captura de credenciales.

Antes de la ejecución registra BSSID, clientes de laboratorio, canal, interfaz monitor, uplink, SSID de prueba, rango DHCP, puertos de proxy/callback y hora de finalización. Mantén el acceso físico o remoto al operador responsable para detener el experimento.

| Técnica | Alcance mínimo a registrar |
|---|---|
| Escaneo | Interfaz, canales, duración y ubicación RF. |
| Deauth/handshake | BSSID, clientes, número máximo de frames y ventana. |
| Rogue AP | SSID, canal, clientes de prueba y uplink. |
| MITM/DNS | Subred, puertos, dominios y certificado de laboratorio. |
| Callbacks | Host/puerto, datos permitidos y retención de logs. |

El repositorio no contiene una autorización real. Usa documentación contractual fuera de Git y publica solo evidencia anonimizada.
