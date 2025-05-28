import zmq
import threading
import json


context = zmq.Context()

# Conexiones a DTI y Backup
backend_dti = context.socket(zmq.DEALER)
backend_dti.connect("tcp://localhost:6000")  # DTI - PC1

backend_backup = context.socket(zmq.DEALER)
backend_backup.connect("tcp://localhost:5999")  # Backup - PC3

# Frontend para recibir solicitudes de facultades
frontend = context.socket(zmq.ROUTER)
frontend.bind("tcp://*:6001")  # Broker - PC2

# Subscripción al healthcheck (notificación de servidores activos)
subscriber = context.socket(zmq.SUB)
subscriber.connect("tcp://localhost:7000")  # HealthCheck local
subscriber.setsockopt_string(zmq.SUBSCRIBE, "switch")

# Diccionario para mapear servidor → socket DEALER
servidores = {
    "dti": backend_dti,
    "backup": backend_backup
}

# Lista de servidores activos (actualizada por el healthcheck)
servidores_activos = []  # CAMBIAR: Inicializar vacío, se actualiza por healthcheck
indice_actual = 0
lock = threading.Lock()
mapa_respuestas = {}

def recibir_notificaciones():
    global servidores_activos
    while True:
        try:
            msg = subscriber.recv_string()
            print(f"[DEBUG] Mensaje recibido del healthcheck: {msg}")
            _, payload = msg.split(" ", 1)
            data = json.loads(payload)
            nuevos = data.get("activos")
            
            with lock:
                # ACTIVAR: Esta línea debe estar habilitada para usar healthcheck
                servidores_activos = nuevos if nuevos else []
                print(f"[Broker] Servidores activos actualizados: {servidores_activos}")
        except Exception as e:
            print(f"[Broker] Error en notificación: {e}")

def reenviar_mensajes():
    global indice_actual
    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)
    poller.register(backend_dti, zmq.POLLIN)
    poller.register(backend_backup, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())

        # Solicitud de facultad
        if frontend in socks:
            identidad, _, mensaje = frontend.recv_multipart()
            try:
                solicitud = json.loads(mensaje.decode())
                facultad = solicitud.get("facultad", "Desconocida")
            except:
                facultad = "Desconocida"

            with lock:
                if not servidores_activos:
                    print("[Broker] ❌ No hay servidores activos para responder.")
                    continue

                print(f"[DEBUG] Servidores disponibles: {servidores_activos}")
                servidor = servidores_activos[indice_actual % len(servidores_activos)]
                print(f"[Broker] 📤 Solicitud #{indice_actual + 1} → {servidor}")
                indice_actual += 1
                socket_destino = servidores[servidor]

                socket_destino.send_multipart([identidad, b'', mensaje])
                mapa_respuestas[identidad] = frontend
                print(f"[Broker] Solicitud de '{facultad}' → enviada a {servidor.upper()}")

        # Respuesta de DTI o Backup
        for servidor, socket_origen in servidores.items():
            if socket_origen in socks:
                identidad, _, respuesta = socket_origen.recv_multipart()
                if identidad in mapa_respuestas:
                    mapa_respuestas[identidad].send_multipart([identidad, b'', respuesta])
                    del mapa_respuestas[identidad]

if __name__ == "__main__":
    print("[Broker] En funcionamiento con balanceo Round-Robin...")
    threading.Thread(target=recibir_notificaciones, daemon=True).start()
    reenviar_mensajes()
