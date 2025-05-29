import zmq
import json
import os
import threading
import time
from AutenticacionDTI import AutenticacionDTI

class DTIBackup:
    def __init__(self, puerto_rep=5999, sync_port=6006, dti_ip="localhost", dti_sync_port=6007):
        self.context = zmq.Context()
        self.receptor = self.context.socket(zmq.REP)
        self.receptor.bind(f"tcp://*:{puerto_rep}")

        # Socket PULL para recibir sincronización del DTI principal
        self.pull_sync = self.context.socket(zmq.PULL)
        self.pull_sync.bind(f"tcp://*:{sync_port}")

        # Socket PUSH para enviar sincronización al DTI principal
        self.push_dti = self.context.socket(zmq.PUSH)
        self.push_dti.connect(f"tcp://{dti_ip}:{dti_sync_port}")

        # Socket SUB para escuchar notificaciones del HealthCheck
        self.subscriber_healthcheck = self.context.socket(zmq.SUB)
        self.subscriber_healthcheck.connect("tcp://localhost:5998")  # Puerto de notificaciones para Backup
        self.subscriber_healthcheck.setsockopt_string(zmq.SUBSCRIBE, "peer_status")
        # Configurar timeout para evitar bloqueos
        self.subscriber_healthcheck.setsockopt(zmq.RCVTIMEO, 1000)  # 1 segundo timeout
        
        print(f"[DTIBackup] 📡 Suscrito a notificaciones HealthCheck en puerto 5998")
        threading.Thread(target=self.escuchar_notificaciones_healthcheck, daemon=True).start()

        self.RUTA_JSON = "recursos_backup.json"
        self.lock = threading.Lock()
        self.dti_online = False  # Estado del DTI principal
        
        # Sistema de autenticación (usa el mismo archivo que DTI)
        self.auth = AutenticacionDTI()
        #self.auth.mostrar_credenciales_iniciales()

        print(f"[DTIBackup] Servidor de respaldo iniciado en puerto {puerto_rep}")
        print(f"[DTIBackup] Escuchando sincronización en puerto {sync_port}")
        print(f"[DTIBackup] Conectando a DTI principal en {dti_ip}:{dti_sync_port}")
        print(f"[DTIBackup] Escuchando notificaciones de HealthCheck en puerto 5998")

        self._inicializar_recursos()

        # Hilo para recibir sincronización del DTI principal
        threading.Thread(target=self.recibir_sincronizacion, daemon=True).start()


    def escuchar_notificaciones_healthcheck(self):
        """Escucha notificaciones del HealthCheck sobre el estado del DTI"""
        
        time.sleep(1)
        
        while True:
            try:
                mensaje_completo = self.subscriber_healthcheck.recv_string(zmq.NOBLOCK)
                
                if mensaje_completo.startswith("peer_status "):
                    payload = mensaje_completo[12:]
                    data = json.loads(payload)
                    
                    if data.get("peer") == "dti":
                        estado_dti = data.get("estado") == "online"
                        
                        # Detectar si el DTI volvió online
                        dti_volvio = not self.dti_online and estado_dti
                        
                        with self.lock:
                            self.dti_online = estado_dti
                        
                        # Si el DTI volvió online, enviarle nuestra información
                        if dti_volvio:
                            print(f"[DTIBackup] 🔄 DTI volvió online - Enviando nuestra información...")
                            threading.Timer(2.0, self.enviar_sincronizacion_completa).start()
                
            except zmq.Again:
                time.sleep(0.5)
            except Exception as e:
                print(f"[DTIBackup] ❌ Error procesando notificación HealthCheck: {e}")
                time.sleep(1)

    def enviar_sincronizacion_completa(self):
        """Envía sincronización completa al DTI cuando vuelve online"""
        try:
            with self.lock:
                recursos = self.cargar_recursos()
            
            print(f"[DTIBackup] 📤 Enviando sincronización completa al DTI: {recursos}")
            self.sincronizar_dti(recursos)
            
        except Exception as e:
            print(f"[DTIBackup] ❌ Error enviando sincronización completa: {e}")

    def recibir_sincronizacion(self):
        while True:
            try:
                data = self.pull_sync.recv_json()
                
                # Solo procesar sincronización si el DTI está online
                if self.dti_online:
                    with self.lock:
                        # NO sincronizar de vuelta para evitar bucle
                        self.guardar_recursos(data, sincronizar=False)
                    print("[DTIBackup] Recursos sincronizados desde DTI principal.")
                else:
                    print("[DTIBackup] ⚠️ DTI offline - Ignorando sincronización entrante")
                    
            except Exception as e:
                print(f"[DTIBackup] Error recibiendo sincronización: {e}")
                time.sleep(1)

    def forzar_sincronizacion_completa(self):
        """Fuerza una sincronización completa con el DTI (equivalente al DTI pero hacia DTI)"""
        try:
            with self.lock:
                recursos = self.cargar_recursos()
            
            print(f"[DTIBackup] 📤 Forzando sincronización completa: {recursos}")
            self.sincronizar_dti(recursos)
            
            # Enviar mensaje especial indicando sincronización completa
            mensaje_sync = {
                "tipo": "sync_completa",
                "recursos": recursos,
                "timestamp": time.time(),
                "servidor_origen": "DTIBackup"
            }
            
            self.push_dti.send_json(mensaje_sync)
            print(f"[DTIBackup] ✅ Sincronización completa enviada al DTI")
            
        except Exception as e:
            print(f"[DTIBackup] ❌ Error en sincronización forzada: {e}")

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

    def guardar_recursos(self, data, sincronizar=True):
        with open(self.RUTA_JSON, 'w') as f:
            json.dump(data, f, indent=4)
        if sincronizar and self.dti_online:
            self.sincronizar_dti(data)

    def sincronizar_dti(self, data):
        try:
            self.push_dti.send_json(data)
            print("[DTIBackup] Sincronización enviada al DTI principal.")
        except Exception as e:
            print(f"[DTIBackup] Error al sincronizar con DTI principal: {e}")


    def procesar_solicitud(self, solicitud):
        if solicitud.get("tipo") == "healthcheck":
            return {"estado": "OK", "servidor": "Backup"}

        if solicitud.get("tipo") == "conexion":
            nombre_facultad = solicitud.get("facultad")
            password_facultad = solicitud.get("password")
            
            # Verificar autenticación de la facultad
            if not password_facultad:
                print(f"[DTIBackup] ✗ Conexión rechazada: Falta contraseña para {nombre_facultad}")
                return {"estado": "Autenticación requerida", "mensaje": "Falta contraseña", "servidor": "Backup"}
            
            if self.auth.verificar_facultad(nombre_facultad, password_facultad):
                print(f"[DTIBackup] ✓ Facultad autenticada: {nombre_facultad}")
                return {"estado": "Conexión aceptada", "mensaje": "Autenticación exitosa", "servidor": "Backup"}
            else:
                print(f"[DTIBackup] ✗ Autenticación fallida para: {nombre_facultad}")
                return {"estado": "Acceso denegado", "mensaje": "Credenciales inválidas", "servidor": "Backup"}

        # Verificar que la solicitud venga de una facultad autenticada
        nombre_facultad = solicitud.get("facultad")
        password_facultad = solicitud.get("password_facultad")
        
        if not password_facultad or not self.auth.verificar_facultad(nombre_facultad, password_facultad):
            print(f"[DTIBackup] ✗ Solicitud rechazada: Facultad no autenticada - {nombre_facultad}")
            return {
                "facultad": nombre_facultad,
                "estado": "Acceso denegado",
                "mensaje": "Facultad no autenticada",
                "servidor": "Backup"
            }

        with self.lock:
            recursos = self.cargar_recursos()
            salones = solicitud.get("salones", 0)
            laboratorios = solicitud.get("laboratorios", 0)

            if recursos["salones_disponibles"] >= salones and recursos["laboratorios_disponibles"] >= laboratorios:
                recursos["salones_disponibles"] -= salones
                recursos["laboratorios_disponibles"] -= laboratorios
                estado = "Aceptado"
            else:
                estado = "Rechazado"

            # Usar el flag sincronizar=True para que sincronice con el DTI
            self.guardar_recursos(recursos, sincronizar=True)

        respuesta = {
            "facultad": solicitud.get("facultad", "Desconocida"),
            "programa": solicitud.get("programa", "Desconocido"),
            "estado": estado,
            "salones": salones,
            "laboratorios": laboratorios,
            "servidor": "Backup"
        }

        print(f"[DTIBackup] Solicitud procesada: {respuesta}")
        print(f"[DTIBackup] Recursos restantes: Salones={recursos['salones_disponibles']}, Labs={recursos['laboratorios_disponibles']}\n")
        return respuesta

    def verificar_conexion_healthcheck(self):
        """Método de prueba para verificar la conexión con HealthCheck"""
        try:
            # Crear un socket temporal para probar
            test_socket = self.context.socket(zmq.SUB)
            test_socket.connect("tcp://localhost:5998")
            test_socket.setsockopt_string(zmq.SUBSCRIBE, "peer_status")
            test_socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 segundos timeout
            
            print("[DTIBackup] 🧪 Probando conexión con HealthCheck...")
            
            # Intentar recibir un mensaje
            try:
                mensaje = test_socket.recv_string()
                print(f"[DTIBackup] ✅ Mensaje HealthCheck recibido en prueba: {mensaje}")
            except zmq.Again:
                print("[DTIBackup] ⏰ No se recibieron mensajes HealthCheck en 2 segundos")
            
            test_socket.close()
            
        except Exception as e:
            print(f"[DTIBackup] ❌ Error en verificación HealthCheck: {e}")

    def ejecutar(self):
        try:
            while True:
                solicitud = self.receptor.recv_json()

                if solicitud.get("tipo") != "healthcheck":
                    print(f"[DTIBackup] Nueva solicitud recibida: {solicitud}")

                # Solo mostrar tiempo de procesamiento para solicitudes que NO sean healthcheck
                if solicitud.get("tipo") == "healthcheck":
                    respuesta = self.procesar_solicitud(solicitud)
                    self.receptor.send_json(respuesta)
                else:
                    inicio = time.time()
                    respuesta = self.procesar_solicitud(solicitud)
                    fin = time.time()
                    print(f"[DTIBackup] Tiempo de procesamiento: {fin - inicio:.4f} segundos")
                    self.receptor.send_json(respuesta)
        except KeyboardInterrupt:
            print("\n[DTIBackup] Servidor de respaldo detenido.")
        finally:
            print("[DTIBackup] Cerrando conexiones...")
            try:
                self.receptor.close()
                self.pull_sync.close()
                self.push_dti.close()
                self.subscriber_healthcheck.close()
                self.context.term()
            except Exception as e:
                print(f"[DTIBackup] Error al cerrar conexiones: {e}")

if __name__ == "__main__":
    dti_backup = DTIBackup()
    dti_backup.ejecutar()