import zmq
import json
import os
import threading
import time

class DTI:
    def __init__(self, puerto_rep=6000, backup_ip="localhost", backup_port=6006):
        self.context = zmq.Context()
        self.receptor = self.context.socket(zmq.REP)
        self.receptor.bind(f"tcp://*:{puerto_rep}")

        # Socket PUSH para sincronizar con el backup
        self.push_backup = self.context.socket(zmq.PUSH)
        self.push_backup.connect(f"tcp://{backup_ip}:{backup_port}")

        # Socket PULL para recibir sincronización desde backup
        self.pull_backup_sync = self.context.socket(zmq.PULL)
        self.pull_backup_sync.bind("tcp://*:6007")
        threading.Thread(target=self.recibir_sincronizacion_del_backup, daemon=True).start()

        self.RUTA_JSON = "recursos_dti.json"
        self.lock = threading.Lock()

        print(f"[DTI] Servidor iniciado en puerto {puerto_rep} y esperando solicitudes...")
        self._inicializar_recursos()

    def _inicializar_recursos(self):
        if not os.path.exists(self.RUTA_JSON):
            with open(self.RUTA_JSON, 'w') as f:
                json.dump({
                    "salones_disponibles": 380,
                    "laboratorios_disponibles": 60
                }, f)

    def cargar_recursos(self):
        with open(self.RUTA_JSON, 'r') as f:
            return json.load(f)

    def guardar_recursos(self, data):
        with open(self.RUTA_JSON, 'w') as f:
            json.dump(data, f, indent=4)
        self.sincronizar_backup(data)

    def sincronizar_backup(self, data):
        try:
            self.push_backup.send_json(data)
            print("[DTI] Sincronización enviada al backup.")
        except Exception as e:
            print(f"[DTI] Error al sincronizar con backup: {e}")

    def recibir_sincronizacion_del_backup(self):
        while True:
            try:
                data = self.pull_backup_sync.recv_json()
                with self.lock:
                    self.guardar_recursos(data)
                print("[DTI] Recursos sincronizados desde BACKUP.")
            except Exception as e:
                print(f"[DTI] Error recibiendo sincronización desde backup: {e}")
                time.sleep(1)

    def procesar_solicitud(self, solicitud):
        if solicitud.get("tipo") == "healthcheck":
            print("[DTI] Healthcheck recibido.")
            return {"estado": "OK"}

        if solicitud.get("tipo") == "conexion":
            print(f"[DTI] Facultad conectada: {solicitud['facultad']}")
            return {"estado": "Conexión aceptada"}

        with self.lock:
            recursos = self.cargar_recursos()
            salones = solicitud["salones"]
            laboratorios = solicitud["laboratorios"]

            if recursos["salones_disponibles"] >= salones and recursos["laboratorios_disponibles"] >= laboratorios:
                recursos["salones_disponibles"] -= salones
                recursos["laboratorios_disponibles"] -= laboratorios
                estado = "Aceptado"
            else:
                estado = "Rechazado"

            self.guardar_recursos(recursos)

        respuesta = {
            "facultad": solicitud["facultad"],
            "programa": solicitud["programa"],
            "estado": estado,
            "salones": salones,
            "laboratorios": laboratorios
        }

        print(f"[DTI] Solicitud procesada: {respuesta}")
        print(f"[DTI] Recursos restantes: Salones={recursos['salones_disponibles']}, Labs={recursos['laboratorios_disponibles']}\n")
        return respuesta

    def ejecutar(self):
        try:
            while True:
                solicitud = self.receptor.recv_json()
                print(f"[DTI] Nueva solicitud recibida: {solicitud}")

                inicio = time.time()
                respuesta = self.procesar_solicitud(solicitud)
                fin = time.time()

                print(f"[DTI] Tiempo de procesamiento de la solicitud: {fin - inicio:.4f} segundos")
                self.receptor.send_json(respuesta)
        except KeyboardInterrupt:
            print("\n[DTI] Servidor detenido.")
        finally:
            self.receptor.close()
            self.push_backup.close()
            self.pull_backup_sync.close()
            self.context.term()

if __name__ == "__main__":
    dti = DTI()
    dti.ejecutar()
