import zmq
import threading
import json

# Configuración de puertos e IPs
BROKER_FRONTEND_PORT = 7001  # Facultad → Broker (ROUTER)
BROKER_BACKEND_DTI = "tcp://localhost:6000"
BROKER_BACKEND_BACKUP = "tcp://localhost:5999"
BROKER_SUB_HEALTHCHECK_PORT = 7000  # HealthCheck → Broker (PUB/SUB)

context = zmq.Context()

# Sockets
frontend = context.socket(zmq.ROUTER)
frontend.bind(f"tcp://*:{BROKER_FRONTEND_PORT}")

backend_dti = context.socket(zmq.DEALER)
backend_dti.connect(BROKER_BACKEND_DTI)

backend_backup = context.socket(zmq.DEALER)
backend_backup.connect(BROKER_BACKEND_BACKUP)

health_sub = context.socket(zmq.SUB)
health_sub.connect(f"tcp://localhost:{BROKER_SUB_HEALTHCHECK_PORT}")
health_sub.setsockopt_string(zmq.SUBSCRIBE, "switch")

# Estado actual del servidor activo
servidor_actual = "dti"  # Inicialmente se usa el DTI principal
backend_activo = backend_dti

# Lock para proteger el cambio de estado
lock = threading.Lock()

def escuchar_healthcheck():
    global servidor_actual, backend_activo
    while True:
        mensaje = health_sub.recv_string()
        _, payload = mensaje.split(" ", 1)
        datos = json.loads(payload)

        nuevo = datos.get("usar")
        with lock:
            if nuevo == "backup":
                backend_activo = backend_backup
                servidor_actual = "backup"
                print("[Broker] Cambiado a servidor de respaldo.")
            elif nuevo == "dti":
                backend_activo = backend_dti
                servidor_actual = "dti"
                print("[Broker] Cambiado a servidor principal.")

def reenviar_mensajes():
    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)
    poller.register(backend_dti, zmq.POLLIN)
    poller.register(backend_backup, zmq.POLLIN)

    # Mapas para emparejar identidades
    mapa_respuestas = {}

    while True:
        socks = dict(poller.poll())

        # Solicitud entrante de alguna Facultad
        if frontend in socks:
            identidad, _, mensaje = frontend.recv_multipart()
            try:
                solicitud = json.loads(mensaje.decode())
                facultad = solicitud.get("facultad", "Desconocida")
            except:
                facultad = "Desconocida"

            with lock:
                backend_activo.send_multipart([identidad, b'', mensaje])
                mapa_respuestas[identidad] = frontend
                print(f"[Broker] Solicitud de '{facultad}' → enviada a {servidor_actual.upper()}")


        # Respuesta desde DTI
        if backend_dti in socks:
            identidad, _, respuesta = backend_dti.recv_multipart()
            if identidad in mapa_respuestas:
                mapa_respuestas[identidad].send_multipart([identidad, b'', respuesta])
                del mapa_respuestas[identidad]

        # Respuesta desde Backup
        if backend_backup in socks:
            identidad, _, respuesta = backend_backup.recv_multipart()
            if identidad in mapa_respuestas:
                mapa_respuestas[identidad].send_multipart([identidad, b'', respuesta])
                del mapa_respuestas[identidad]

# Hilo para escuchar mensajes del healthcheck
threading.Thread(target=escuchar_healthcheck, daemon=True).start()

print("[Broker] En funcionamiento. Esperando solicitudes...")
reenviar_mensajes()
