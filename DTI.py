import zmq
import json
import os
import threading
import time

class DTI:
    def __init__(self, puerto_rep=6000):
        self.context = zmq.Context()
        self.receptor = self.context.socket(zmq.REP)
        self.receptor.bind(f"tcp://*:{puerto_rep}")

        # Define la ruta del archivo JSON
        self.RUTA_JSON = "recursos.json"

        # Inicializa un lock para manejar concurrencia
        self.lock = threading.Lock()

        print("[DTI] Servidor iniciado y esperando solicitudes...")

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

    def procesar_solicitud(self, solicitud):
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

                inicio = time.time()  # Inicia el cronómetro
                respuesta = self.procesar_solicitud(solicitud)
                fin = time.time()  # Finaliza el cronómetro

                print(f"[DTI] Tiempo de procesamiento de la solicitud: {fin - inicio:.4f} segundos")
                self.receptor.send_json(respuesta)  # Enviar respuesta al solicitante
        except KeyboardInterrupt:
            print("\n[DTI] Servidor detenido.")
        finally:
            self.receptor.close()
            self.context.term()

if __name__ == "__main__":
    dti = DTI()
    dti.ejecutar()