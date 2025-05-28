import zmq
import time
import json

# IPs reales en tu red
DTI_IP = "localhost"       # PC1
DTI_PORT = 6000
BACKUP_IP = "localhost"    # PC3
BACKUP_PORT = 5999
BROKER_PUB_PORT = 7000         # se queda local en PC2

INTERVALO = 2   # segundos entre chequeos
TIMEOUT = 1.5   # timeout de espera

context = zmq.Context()

# Socket para notificar al broker
notificador = context.socket(zmq.PUB)
notificador.bind(f"tcp://*:{BROKER_PUB_PORT}")

# Estado inicial
servidores_disponibles = []
servidores_anteriores = []

def probar_servidor(ip, puerto):
    try:
        ctx = zmq.Context.instance()
        temp_socket = ctx.socket(zmq.REQ)
        temp_socket.RCVTIMEO = int(TIMEOUT * 1000)
        temp_socket.LINGER = 0
        temp_socket.connect(f"tcp://{ip}:{puerto}")
        temp_socket.send_json({"tipo": "healthcheck"})
        respuesta = temp_socket.recv_json()
        temp_socket.close()
        return respuesta.get("estado") == "OK"
    except:
        try:
            temp_socket.close()
        except:
            pass
        return False

def notificar_broker(lista):
    mensaje = {"activos": lista}
    notificador.send_string("switch " + json.dumps(mensaje))
    print(f"[HealthCheck] Notificado al broker: activos = {lista}")

print("[HealthCheck] Iniciando monitor de servidores (modo balanceo)...")
while True:
    time.sleep(INTERVALO)

    disponibles = []
    
    # Verifica DTI
    print(f"[HealthCheck] Probando DTI: {DTI_IP}:{DTI_PORT}")
    if probar_servidor(DTI_IP, DTI_PORT):
        print("[HealthCheck] ✅ DTI activo")
        disponibles.append("dti")
    else:
        print("[HealthCheck] ❌ DTI no responde")

    # Verifica BACKUP
    print(f"[HealthCheck] Probando BACKUP: {BACKUP_IP}:{BACKUP_PORT}")
    if probar_servidor(BACKUP_IP, BACKUP_PORT):
        print("[HealthCheck] ✅ Backup activo")
        disponibles.append("backup")
    else:
        print("[HealthCheck] ❌ Backup no responde")

    # Solo notifica si hay cambio respecto a la lista anterior
    if disponibles != servidores_anteriores:
        servidores_anteriores = disponibles.copy()
        notificar_broker(disponibles)

    if not disponibles:
        print("[HealthCheck] ⚠️ Ningún servidor está disponible.")
