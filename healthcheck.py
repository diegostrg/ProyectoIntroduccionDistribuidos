import zmq
import time
import json

DTI_IP = "localhost"
DTI_PORT = 6000
BACKUP_IP = "localhost"
BACKUP_PORT = 5999
BROKER_PUB_PORT = 7000  # Healthcheck → Broker

INTERVALO = 2  # segundos entre chequeos
TIMEOUT = 1.5  # timeout para respuestas

context = zmq.Context()

# Socket PUB para notificar al broker
notificador = context.socket(zmq.PUB)
notificador.bind(f"tcp://*:{BROKER_PUB_PORT}")

# Estado
servidor_activo = "dti"
dti_recuperado = False  # nuevo: indica si DTI volvió pero aún no se debe usar

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

def notificar_broker(nuevo_destino):
    mensaje = {"usar": nuevo_destino}
    notificador.send_string("switch " + json.dumps(mensaje))
    print(f"[HealthCheck] Notificado al broker: usar {nuevo_destino.upper()}")

# Loop principal
print("[HealthCheck] Iniciando monitor de servidores...")
while True:
    time.sleep(INTERVALO)

    print(f"[HealthCheck] Probar DTI: {DTI_IP}:{DTI_PORT}")
    ok_dti = probar_servidor(DTI_IP, DTI_PORT)
    print(f"[HealthCheck] Resultado DTI: {ok_dti}")

    print(f"[HealthCheck] Probar BACKUP: {BACKUP_IP}:{BACKUP_PORT}")
    ok_backup = probar_servidor(BACKUP_IP, BACKUP_PORT)
    print(f"[HealthCheck] Resultado BACKUP: {ok_backup}")

    if servidor_activo == "dti":
        if ok_dti:
            continue
        elif ok_backup:
            print("[HealthCheck] DTI caído. Cambiando a BACKUP.")
            servidor_activo = "backup"
            notificar_broker("backup")
    elif servidor_activo == "backup":
        if ok_dti and ok_backup:
            if not dti_recuperado:
                print("[HealthCheck] DTI disponible nuevamente. Esperando que BACKUP falle para volver.")
                dti_recuperado = True
        elif not ok_backup and ok_dti:
            print("[HealthCheck] BACKUP cayó. Reactivando DTI.")
            servidor_activo = "dti"
            dti_recuperado = False
            notificar_broker("dti")
        elif not ok_backup and not ok_dti:
            print("[HealthCheck] Ambos servidores están inactivos.")
