# Cleanup y rollback

El método `detener_todo()` marca el evento de parada, termina los procesos registrados, espera hasta cinco segundos, fuerza `kill` si es necesario y elimina las reglas firewall que la instancia guardó. `iniciar_mitmproxy()` también intenta ejecutar su propia regla de eliminación al finalizar.

Después de detener una operación, verifica manualmente el estado del sistema:

```bash
ip link show
nmcli device status
sudo iptables-save
sysctl net.ipv4.ip_forward
pgrep -a 'hostapd|dnsmasq|mitmproxy|airodump|aireplay'
```

Reinicia NetworkManager si el adaptador quedó en modo monitor y confirma que el uplink conserva su configuración. Inspecciona `wireless_captures/`, `rogue_ap/` y `payloads_web/`; elimina capturas, callbacks y payloads que no deban conservarse según el expediente del engagement.

La limpieza automática no revierte cambios realizados por herramientas externas, reglas previas o apagados abruptos. Por eso el procedimiento requiere snapshot, registro pre/post y verificación manual.
