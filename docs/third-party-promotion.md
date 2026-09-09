# Guía para terceros

## Descripción recomendada

**Wireless Scanner & Payload Injector** es una herramienta Python para flujos de evaluación inalámbrica autorizada en Linux. Incluye diagnóstico de dependencias, escaneo, captura de handshakes, configuración de laboratorio, integración con herramientas inalámbricas y cleanup. Sus funciones operativas pueden transmitir frames, levantar un AP, interceptar tráfico y generar callbacks; debe utilizarse sólo contra activos y clientes de prueba autorizados.

Repositorio canónico: https://github.com/hubgunter4-ops/wireless-scanner-payload-injector

## Datos verificables

| Campo | Valor |
|---|---|
| Versión documentada | 2.1.0 |
| Licencia | MIT |
| Plataforma | Linux |
| Python | >= 3.10 |
| Estado | Experimental; requiere laboratorio y revisión de seguridad |
| Instalación | `./install.sh` |
| Diagnóstico | `wireless-injector --check-only --json` |

## Límites de redistribución

Mantén la licencia MIT, esta advertencia de uso autorizado, el enlace canónico y la política de seguridad. No incluyas credenciales, handshakes, capturas, cookies, tokens, logs de callbacks, certificados privados ni datos de clientes. No presentes la herramienta como segura por defecto, anónima, ilimitada o apta para producción.

No publiques anuncios masivos ni copies el material a foros, newsletters o comunidades sin respetar sus normas y sin utilizar sus canales oficiales. Este archivo es material preparado; no constituye un envío a terceros.
