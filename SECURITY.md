# Política de seguridad

## Alcance

Este repositorio contiene una herramienta de evaluación inalámbrica que puede cambiar el estado de interfaces Wi-Fi, transmitir tramas, levantar un punto de acceso, modificar forwarding/NAT, interceptar tráfico y generar callbacks. Estas capacidades pueden afectar a terceros y deben utilizarse únicamente en equipos, redes y clientes de laboratorio bajo autorización escrita.

## Uso autorizado

La autorización para escanear no incluye deauth, captura de handshakes, cracking, rogue AP, MITM, DNS spoofing, inyección de JavaScript ni recepción de callbacks. El alcance debe identificar como mínimo la interfaz, BSSID/SSID, clientes de prueba, canales, uplink, subred, puertos, dominios, ventana de ejecución y procedimiento de limpieza.

No ejecutes el flujo operacional contra redes públicas, dispositivos de terceros, credenciales reales o servicios de producción. El modo `--check-only` y las pruebas locales son los modos recomendados para validar la instalación sin transmitir frames.

## Datos que no deben entrar en Git

No publiques capturas, handshakes, credenciales, cookies, tokens, logs de callbacks, direcciones de clientes, configuraciones de engagement, certificados privados ni artefactos generados. Usa fixtures sintéticos y anonimiza cualquier evidencia.

## Capacidades de alto riesgo

Las plantillas de payload pueden producir keylogging, extracción de cookies, redirecciones, hooks, minería y callbacks. No las uses fuera de un laboratorio controlado. El operador es responsable de verificar el contenido antes de guardarlo o ejecutarlo.

## Reporte responsable

Para reportar una vulnerabilidad del proyecto, abre un issue privado o contacta al mantenedor mediante los canales configurados en GitHub. Incluye versión o commit, pasos de reproducción no destructivos, impacto, entorno y una mitigación propuesta. No adjuntes datos personales, credenciales ni capturas de redes reales.

## Limitaciones

Esta política no convierte la herramienta en segura por defecto ni constituye autorización legal. La licencia MIT no amplía el alcance de un engagement ni sustituye las normas aplicables, la autorización del propietario o la supervisión del operador.
