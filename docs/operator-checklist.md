# Checklist del operador

## Antes

Confirma autorización escrita para cada técnica, snapshot de la estación, interfaz y uplink correctos, BSSID/SSID de laboratorio, ventana de trabajo y contacto de parada. Registra la salida de `ip link`, `nmcli` e `iptables-save` antes de modificar el entorno.

## Durante

Anota la hora de inicio, opción elegida, parámetros, procesos y artefactos producidos. Comprueba que los clientes observados pertenecen al laboratorio y detén la operación si aparece tráfico o un dispositivo fuera del alcance. No publiques `.cap`, logs de callbacks, cookies, credenciales ni payloads con datos reales.

## Después

Usa Ctrl+C para ejecutar cleanup, confirma que no quedan procesos, elimina reglas añadidas, restaura modo managed, verifica forwarding/NAT y conserva solo evidencia aprobada. Registra cualquier desviación o fallo de rollback como hallazgo operativo del engagement.
