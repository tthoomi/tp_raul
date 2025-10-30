# Proyecto de Red - Infraestructura, VLANs y Automatización (Netmiko)

## Resumen
Documento técnico que describe la implementación de una red de laboratorio segmentada por VLANs, con una red de gestión separada, direccionamiento VLSM para los segmentos de usuarios, y automatización de la configuración mediante un script en Python usando **Netmiko**. Incluye la topología lógica, IDs de VLAN, rangos IP, DHCP, NAT y pautas de verificación.

---

## Datos generales del proyecto
- **Red base (bloque asignado):** `10.10.6.0/24`
- **Red de gestión (reservada):** `10.10.6.0/29` → `10.10.6.1 – 10.10.6.6` (5 hosts útiles)
- **Puerta de enlace principal (R1):** `10.10.6.1`
- **PC Sysadmin:** `10.10.6.5` (IP estática en `ens3`)

---

## VLANs (IDs y propósito)
| VLAN ID | Nombre       | Propósito / Comentarios |
|---------|--------------|--------------------------|
| 160     | VENTAS       | Red de los puestos administrativos (≈ 25 hosts) |
| 161     | TECNICA      | Red de desarrolladores / técnicos (≈ 14 hosts) |
| 162     | VISITANTES   | Red para invitados/visitantes (≈ 6 hosts) |
| 169     | NATIVA       | VLAN nativa en trunks (uso en enlaces troncales) |
| 699     | GESTION      | VLAN de administración (R1, R2, SW1, SW2, Sysadmin) |

> Nota: la VLAN de **GESTIÓN** está aislada y usa direcciones fijas para todos los dispositivos de infraestructura.

---

## Subnetting (VLSM aplicado)
A partir del /24 asignado (`10.10.6.0/24`) se definieron subredes con tamaños ajustados a cada necesidad (VLSM):

- **VLAN Gestión (699)**  
  - Subred: `10.10.6.0/29` → Hosts: `10.10.6.1` a `10.10.6.6`  
  - Asignaciones:
    - R1 (gateway): `10.10.6.1`
    - SW1: `10.10.6.2`
    - SW2: `10.10.6.3`
    - R2: `10.10.6.4`
    - PC Sysadmin: `10.10.6.5`
    - (Reserva) `10.10.6.6`

- **VLAN Ventas (160)**  
  - Subred: `10.10.6.32/27` → Rango hosts `10.10.6.33 - 10.10.6.62` (25 hosts)  
  - Gateway sugerido: `10.10.6.33`

- **VLAN Técnica (161)**  
  - Subred: `10.10.6.64/28` → Rango hosts `10.10.6.65 - 10.10.6.78` (14 hosts)  
  - Gateway sugerido: `10.10.6.65`

- **VLAN Visitantes (162)**  
  - Subred: `10.10.6.80/29` → Rango hosts `10.10.6.81 - 10.10.6.86` (6 hosts)  
  - Gateway sugerido: `10.10.6.81`

> Los offsets (`.32`, `.64`, `.80`) vienen de la división VLSM para evitar superposición y reservar espacio.

---

## DHCP (recomendaciones y configuración)
- **Dónde correr el DHCP:** en R1 (MikroTik) o en un servidor DHCP dedicado en la VLAN de usuarios.
- **Rangos sugeridos (DHCP pools):**
  - VLAN Ventas (160): `10.10.6.34 - 10.10.6.62` (pool excluye gateway)
  - VLAN Técnica (161): `10.10.6.66 - 10.10.6.78`
  - VLAN Visitantes (162): podría ser dinámico o con IPs limitadas según política (ej. `10.10.6.82 - 10.10.6.86`)
- **Reservas / IPs estáticas:** routers, switches, servidores, impresoras de red, etc. deben estar fuera del pool DHCP o tener reservas.
- **Opciones DHCP importantes:** `gateway`, `dns-server` (ej. `8.8.8.8` o DNS local), `lease-time` según política (ej. `1h` para invitados).

---

## NAT y salida a Internet
- NAT configurado en R1 para las VLANs que deban acceder a Internet:
  - `srcnat` / masquerade sobre la interfaz de salida (ej. `ether1`) para:
    - `10.10.6.32/27` (Ventas)
    - `10.10.6.64/28` (Técnica)
- VLAN Visitantes puede tener NAT + políticas de firewall adicionales (captive portal / QoS) si se quiere controlar ancho de banda o accesos.

---

## Configuración de switches (resumen)
- **SW1 (principal):**
  - Crear VLANs 160, 161, 162, 169 (nativa), 699 (gestión)
  - Puerto a R1: trunk dot1q, `native vlan 169`, allowed vlans `169,160,161,162,699`
  - Puertos de usuarios: access a su VLAN correspondiente
  - Puerto PC Sysadmin: access a VLAN 699

- **SW2 (remoto):**
  - Mismas VLANs creadas
  - Puerto a R2 / R1: trunk con `native 169`
  - Puerto usuario remoto de administración: access VLAN 699 (gestión)

---

## Configuración de routers MikroTik (resumen)
- Se usa **bridge + vlan-filtering** para manejar tags en puertos (modo bridge + VLANs).
- R1:
  - Bridge `br-core` con `vlan-filtering=yes`.
  - Puertos añadidos al bridge (p. ej. `ether2` hacia SW1).
  - Bridge VLAN entries:
    - VLAN 169 → untagged en links troncales hacia switches (si se definió así)
    - VLAN 699 → tagged en `br-core` y enlaces hacia switches
  - Crear interfaces VLAN lógicas (ej. `interface vlan add name=VLAN160 vlan-id=160 interface=br-core`)
  - Asignar IPs a las interfaces VLAN correspondientes y pools DHCP
  - Configurar NAT (masquerade) para las subredes que salgan a Internet

- R2:
  - Bridge `br-remote` con filtrado VLAN similar a R1 para ser un puente transparente si así se desea.

---

## Automatización con Netmiko — técnica y flujo
**Librería:** `netmiko` (Python) — SSH multi-vendor (Cisco IOS y MikroTik RouterOS en este caso).

### Flujo del script
1. **Devices dictionary:** contiene `device_type`, `host`, `username`, `password` para SW1, SW2, R1, R2.
2. **Separación de configuraciones por dispositivo:**
   - `cfg_sw1`, `cfg_sw2` → listas con comandos IOS para usar `send_config_set()` (aplica cambios en modo config).
   - `cfg_r1`, `cfg_r2` → listas con comandos RouterOS (se envían con `send_command()`/`send_command_timing()` según implementación).
3. **Conexión por SSH:** `with ConnectHandler(**device)` por dispositivo.
4. **Aplicación de comandos:**
   - Para switches: `conn.send_config_set(cfg_sw1)` (aplica bloques de comandos de configuración).
   - Para MikroTik: iteración por comandos y ejecución (se recomienda `conn.send_command()` si el channel soporta RouterOS).
5. **Verificación:** después de aplicar config, ejecutar comandos de verificación:
   - Cisco: `show vlan brief`, `show ip interface brief`
   - MikroTik: `/ip address print`, `/ip dhcp-server print`, `/interface vlan print`, `/ip route print`
6. **Manejo de errores:** capturar `NetmikoTimeoutException`, `NetmikoAuthenticationException`, y excepciones generales para logging y troubleshooting.
7. **Prerequisitos del script:** la **red de gestión debe ser funcional** (R1, SW1, SW2, R2 y PC Sysadmin deben tener conectividad IP & SSH) antes de ejecutar el script.

### Buenas prácticas en el uso del script
- Primero probar el script en lab aislado o con `--dry-run` (imprimir comandos en vez de ejecutarlos).
- Usar entornos virtuales para instalar `netmiko` (`python3 -m venv venv`).
- Hacer backups de la configuración actual antes de aplicar cambios (`write memory`, `/system backup save`).
- Implementar logging en el script (archivos con timestamps por dispositivo).

---

## Comandos críticos y ejemplos
- **Config IP estática en PC Sysadmin (Debian):**
```bash
sudo ip addr flush dev ens3
sudo ip addr add 10.10.6.5/29 dev ens3
sudo ip link set ens3 up
sudo ip route add default via 10.10.6.1
