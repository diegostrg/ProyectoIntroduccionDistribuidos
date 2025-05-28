import zmq
import json
import os
import threading
import time

# ESTE ES EL DTIBACKUP
# Es el servidor de RESPALDO del DTI. PERO DEBE FUNCIONAR COMO UN SERVIDOR INDEPENDIENTE.
# Es decir, no depende del DTI principal, pero se sincroniza con él.
# SI EL DTI PRINCIPAL FALLA, ESTE DEBE PODER SEGUIR ATENDIENDO SOLICITUDES.
# Debe funcionar en cualquier computadora de la red, y debe poder recibir solicitudes de facultades en su puerto 5999.
# No necesita que este el DTI en la misma computadora, pero debe poder conectarse a él para sincronizar recursos.
class DTIBackup:
    def __init__(self, puerto_rep=5999, sync_port=6006, dti_ip="localhost", dti_sync_port=6007):
        self.context = zmq.Context()
        self.receptor = self.context.socket(zmq.REP)
        self.receptor.bind(f"tcp://*:{puerto_rep}")

        # Socket PULL para recibir sincronización del DTI principal
        self.pull_sync = self.context.socket(zmq.PULL)
        self.pull_sync.bind(f"tcp://*:{sync_port}")

        # Socket PUSH para enviar sincronización al DTI principal (opcional)
        self.push_dti = self.context.socket(zmq.PUSH)
        self.push_dti.connect(f"tcp://{dti_ip}:{dti_sync_port}")

        self.RUTA_JSON = "recursos_backup.json"
        self.lock = threading.Lock()

        print(f"[DTIBackup] Servidor de respaldo iniciado en puerto {puerto_rep}")
        print(f"[DTIBackup] Escuchando sincronización en puerto {sync_port}")
        print(f"[DTIBackup] Conectando a DTI principal en {dti_ip}:{dti_sync_port}")

        self._inicializar_recursos()

        # Hilo para recibir sincronización del DTI principal
        threading.Thread(target=self.recibir_sincronizacion, daemon=True).start()

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

    def sincronizar_dti(self, data):
        try:
            self.push_dti.send_json(data)
            print("[DTIBackup] Sincronización enviada al DTI principal.")
        except Exception as e:
            print(f"[DTIBackup] Error al sincronizar con DTI principal: {e}")

    def recibir_sincronizacion(self):
        while True:
            try:
                data = self.pull_sync.recv_json()
                with self.lock:
                    self.guardar_recursos(data)
                print("[DTIBackup] Recursos sincronizados desde DTI principal.")
            except Exception as e:
                print(f"[DTIBackup] Error recibiendo sincronización: {e}")
                time.sleep(1)

    def procesar_solicitud(self, solicitud):
        if solicitud.get("tipo") == "conexion":
            print(f"[DTIBackup] Facultad conectada: {solicitud['facultad']}")
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
            # Si procesamos exitosamente, sincronizar al DTI principal
            if estado == "Aceptado":
                self.sincronizar_dti(recursos)

        respuesta = {
            "facultad": solicitud["facultad"],
            "programa": solicitud["programa"],
            "estado": estado,
            "salones": salones,
            "laboratorios": laboratorios
        }

        print(f"[DTIBackup] Solicitud procesada: {respuesta}")
        print(f"[DTIBackup] Recursos restantes: Salones={recursos['salones_disponibles']}, Labs={recursos['laboratorios_disponibles']}\n")
        return respuesta

    def ejecutar(self):
        try:
            while True:
                solicitud = self.receptor.recv_json()
                print(f"[DTIBackup] Nueva solicitud recibida: {solicitud}")

                inicio = time.time()
                respuesta = self.procesar_solicitud(solicitud)
                fin = time.time()

                print(f"[DTIBackup] Tiempo de procesamiento de la solicitud: {fin - inicio:.4f} segundos")
                self.receptor.send_json(respuesta)
        except KeyboardInterrupt:
            print("\n[DTIBackup] Servidor de respaldo detenido.")
        finally:
            self.receptor.close()
            self.pull_sync.close()
            self.push_dti.close()
            self.context.term()

if __name__ == "__main__":
    dti_backup = DTIBackup()
    dti_backup.ejecutar()