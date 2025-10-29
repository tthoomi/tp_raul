from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# Datos de conexión comunes
devices = {
    "SW1": {
        "device_type": "cisco_ios",
        "host": "10.10.6.2",
        "username": "admin",
        "password": "1234",
    },
    "SW2": {
        "device_type": "cisco_ios",
        "host": "10.10.6.3",
        "username": "admin",
        "password": "1234",
    },
    "R1": {
        "device_type": "mikrotik_routeros",
        "host": "10.10.6.1",
        "username": "admin",
        "password": "1234",
    },
    "R2": {
        "device_type": "mikrotik_routeros",
        "host": "10.10.6.4",
        "username": "admin",
        "password": "1234",
    }
}

# Configuración de SW1
cfg_sw1 = [
    "vlan 160", "name VENTAS",
    "vlan 161", "name TECNICA",
    "vlan 162", "name VISITANTES",
    # VLANs ya creadas: 699 (gestion), 169 (nativa trunk)
    # Puertos access
    "interface Ethernet0/1",
    " switchport mode access",
    " switchport access vlan 160",
    " no shutdown",
    "exit",
    "interface Ethernet0/2",
    " switchport mode access",
    " switchport access vlan 161",
    " no shutdown",
    "exit",
    "interface Ethernet0/3",
    " switchport mode access",
    " switchport access vlan 162",
    " no shutdown",
    "exit",
    # Trunk hacia R1
    "interface Ethernet0/0",
    " switchport trunk encapsulation dot1q",
    " switchport mode trunk",
    " switchport trunk native vlan 169",
    " switchport trunk allowed vlan 169,160,161,162,699",
    " no shutdown",
    "exit",
]

# Configuración de SW2 (trunk + puerto usuario remoto en gestión)
cfg_sw2 = [
    "vlan 160", "name VENTAS",
    "vlan 161", "name TECNICA",
    "vlan 162", "name VISITANTES",
    "interface Ethernet0/1",
    " switchport mode access",
    " switchport access vlan 699",   # PC remota ahora en VLAN Gestión
    " no shutdown",
    "exit",
    "interface Ethernet0/0",
    " switchport trunk encapsulation dot1q",
    " switchport mode trunk",
    " switchport trunk native vlan 169",
    " switchport trunk allowed vlan 169,160,161,162,699",
    " no shutdown",
    "exit",
]

# Configuración de R1 (Router-on-a-Stick + NAT + DHCP)
# VLAN de gestión 699 ya configurada con IP 10.10.6.1/29
cfg_r1 = [
    # Subinterfaces para VLANs de usuario
    "/interface vlan add name=VLAN160 vlan-id=160 interface=ether2",
    "/interface vlan add name=VLAN161 vlan-id=161 interface=ether2",
    "/interface vlan add name=VLAN162 vlan-id=162 interface=ether2",

    # Direccionamiento para las VLANs de usuario (VLSM aplicado)
    "/ip address add address=10.10.6.33/27 interface=VLAN160",  # Ventas
    "/ip address add address=10.10.6.65/28 interface=VLAN161",  # Técnica
    "/ip address add address=10.10.6.81/29 interface=VLAN162",  # Visitantes

    # NAT solo para Ventas y Técnica
    "/ip firewall nat add chain=srcnat src-address=10.10.6.32/27 action=masquerade out-interface=ether1",
    "/ip firewall nat add chain=srcnat src-address=10.10.6.64/28 action=masquerade out-interface=ether1",

    # DHCP para Ventas y Técnica
    "/ip pool add name=POOL_VLAN160 ranges=10.10.6.34-10.10.6.62",
    "/ip dhcp-server add name=DHCP160 interface=VLAN160 lease-time=1h address-pool=POOL_VLAN160",
    "/ip dhcp-server network add address=10.10.6.32/27 gateway=10.10.6.33 dns-server=8.8.8.8",

    "/ip pool add name=POOL_VLAN161 ranges=10.10.6.66-10.10.6.78",
    "/ip dhcp-server add name=DHCP161 interface=VLAN161 lease-time=1h address-pool=POOL_VLAN161",
    "/ip dhcp-server network add address=10.10.6.64/28 gateway=10.10.6.65 dns-server=8.8.8.8",
]

# Configuración de R2 (remoto, puente transparente para todas las VLANs)
cfg_r2 = [
    # VLANs en el bridge remoto
    "/interface bridge vlan add bridge=br-remote vlan-ids=169 untagged=ether1,ether2",
    "/interface bridge vlan add bridge=br-remote vlan-ids=699 tagged=br-remote,ether1,ether2",
    "/interface bridge vlan add bridge=br-remote vlan-ids=160 tagged=ether1,ether2",
    "/interface bridge vlan add bridge=br-remote vlan-ids=161 tagged=ether1,ether2",
    "/interface bridge vlan add bridge=br-remote vlan-ids=162 tagged=ether1,ether2",
]

# Comandos de verificación
verify_cmds = {
    "SW1": ["show vlan brief", "show ip interface brief"],
    "SW2": ["show vlan brief", "show ip interface brief"],
    "R1": ["/ip address print", "/ip route print", "/ip dhcp-server print", "/interface vlan print"],
    "R2": ["/ip address print", "/ip route print", "/interface vlan print"],
}

# Ejecución
for name, device in devices.items():
    print(f"\n###### Conectando a {name} ({device['host']}) ######")
    try:
        with ConnectHandler(**device) as conn:
            if name == "SW1":
                print(f"--- Aplicando configuración a {name} ---")
                output = conn.send_config_set(cfg_sw1)
                print(output)
            elif name == "SW2":
                print(f"--- Aplicando configuración a {name} ---")
                output = conn.send_config_set(cfg_sw2)
                print(output)
            elif name == "R1":
                print(f"--- Aplicando configuración a {name} ---")
                for cmd in cfg_r1:
                    print(f"Ejecutando: {cmd}")
                    output = conn.send_command(cmd)
                    if output:
                        print(f"Output: {output}")
            elif name == "R2":
                print(f"--- Aplicando configuración a {name} ---")
                for cmd in cfg_r2:
                    print(f"Ejecutando: {cmd}")
                    output = conn.send_command(cmd)
                    if output:
                        print(f"Output: {output}")

            print(f"\n-- Verificación en {name} --")
            for vcmd in verify_cmds[name]:
                print(f"\n{name}# {vcmd}")
                output = conn.send_command(vcmd)
                print(f"{output}\n")

    except NetmikoTimeoutException:
        print(f"ERROR: Timeout al conectar con {name} ({device['host']}). Verifique la conectividad y las credenciales.")
    except NetmikoAuthenticationException:
        print(f"ERROR: Autenticación fallida para {name} ({device['host']}). Verifique el usuario y la contraseña.")
    except Exception as e:
        print(f"ERROR: Ocurrió un error inesperado al conectar o configurar {name}: {e}")

print("\n##### Proceso de configuración completado #####")
