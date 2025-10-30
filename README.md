# 🧠 Proyecto de Red - Infraestructura y Configuración

## 📋 Descripción General
Este proyecto documenta la estructura, configuración y segmentación de una red de laboratorio implementada en Debian, con enfoque en administración, seguridad y escalabilidad.  
La red está organizada en múltiples VLANs y subredes, separando la **red de gestión** de la **red de usuarios**, y estableciendo un esquema de direccionamiento IP fijo y dinámico según la función de cada dispositivo.

---

## 🗺️ Estructura de la Red

La topología general se basa en los siguientes componentes:

- **R1** → Router principal (gateway de toda la red)  
- **R2** → Router secundario o enlace redundante  
- **SW1** → Switch de administración y conexión troncal  
- **Servidor** → DHCP/DNS o administración centralizada  
- **PC Sysadmin** → Equipo de administración y monitoreo  
- **Clientes LAN** → PCs y notebooks de usuarios finales

### 🌐 Segmentación por VLANs

| VLAN | Nombre | Propósito | Rango IP | Máscara | Gateway |
|------|---------|------------|-----------|----------|----------|
| 10 | Gestión | Administración de red (routers, switches, servidores, sysadmin) | 10.10.6.0/29 | 255.255.255.248 | 10.10.6.1 |
| 20 | Usuarios | Red de trabajo de usuarios finales | 10.10.12.0/24 | 255.255.255.0 | 10.10.12.1 |

---

## 🧩 Red de Gestión (VLAN 10)
**Rango:** `10.10.6.0 – 10.10.6.7`  
**Máscara:** `255.255.255.248`

| Dispositivo | IP asignada | Tipo | Descripción |
|--------------|--------------|------|--------------|
| R1 | 10.10.6.1 | Fija | Router principal / gateway |
| R2 | 10.10.6.2 | Fija | Router secundario |
| SW1 | 10.10.6.3 | Fija | Switch administrable |
| Servidor | 10.10.6.4 | Fija | DHCP, DNS o servicios |
| PC Sysadmin | 10.10.6.5 | Fija | Administración (Debian) |
| Reserva | 10.10.6.6 | — | IP libre para pruebas |

📌 Todas las IPs de esta VLAN son **fijas**, ya que se utilizan para administración, monitoreo y acceso remoto.

---

## 💻 Red de Usuarios (VLAN 20)
**Rango:** `10.10.12.0 – 10.10.12.255`  
**Máscara:** `255.255.255.0`  
**Gateway:** `10.10.12.1`

| Tipo de Dispositivo | Método de Asignación | Rango sugerido |
|----------------------|----------------------|----------------|
| Router R1 | Fija | 10.10.12.1 |
| Equipos de red o servidores internos | Fija (si aplica) | 10.10.12.2 – 10.10.12.49 |
| Equipos de usuarios | DHCP | 10.10.12.50 – 10.10.12.200 |
| Reserva o pruebas | DHCP / Manual | 10.10.12.201 – 10.10.12.254 |

🔹 El servidor DHCP asigna IPs automáticamente dentro del rango `10.10.12.50 – 10.10.12.200`.  
🔹 Los equipos críticos (como routers y servidores) usan IP fija fuera de ese rango.

---

## ⚙️ Configuración de la PC Sysadmin (Debian)

Configuración manual de la interfaz de red (`ens3`):

```bash
sudo ip addr flush dev ens3
sudo ip addr add 10.10.6.5/29 dev ens3
sudo ip link set ens3 up
sudo ip route add default via 10.10.6.1
