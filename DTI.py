import zmq
import json
import os
import threading
import time
from AutenticacionDTI import AutenticacionDTI

class DTI:
    def __init__(self, puerto_rep=6000, backup_ip="10.43.102.243", backup_port=6006):
        self.context = zmq.Context()
        self.receptor = self.context.socket(zmq.REP)
        self.receptor.bind(f"tcp://*:{puerto_rep}")

        # Este servidor debe usar la ip 10.43.103.206

        # Socket PUSH para sincronizar con el backup
        self.push_backup = self.context.socket(zmq.PUSH)
        self.push_backup.connect(f"tcp://{backup_ip}:{backup_port}")

        # Socket PULL para recibir sincronización desde backup
        self.pull_backup_sync = self.context.socket(zmq.PULL)
        self.pull_backup_sync.bind("tcp://*:6007")
        threading.Thread(target=self.recibir_sincronizacion_backup, daemon=True).start()

        # Socket SUB para escuchar notificaciones del HealthCheck
        self.subscriber_healthcheck = self.context.socket(zmq.SUB)
        self.subscriber_healthcheck.connect("tcp://10.43.96.34:6008")  # Puerto de notificaciones para DTI
        self.subscriber_healthcheck.setsockopt_string(zmq.SUBSCRIBE, "peer_status")
        # Configurar timeout para evitar bloqueos
        self.subscriber_healthcheck.setsockopt(zmq.RCVTIMEO, 1000)  # 1 segundo timeout
        
        print(f"[DTI] 📡 Suscrito a notificaciones HealthCheck en puerto 6008")
        threading.Thread(target=self.escuchar_notificaciones_healthcheck, daemon=True).start()

        self.RUTA_JSON = "recursos_dti.json"
        self.lock = threading.Lock()
        self.backup_online = False  # Estado del backup
        
        # Sistema de autenticación
        self.auth = AutenticacionDTI()
        #self.auth.mostrar_credenciales_iniciales()

        print(f"[DTI] Servidor iniciado en puerto {puerto_rep} y esperando solicitudes...")
        print(f"[DTI] Escuchando notificaciones de HealthCheck en puerto 6008")
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

    def guardar_recursos(self, data, sincronizar=True):
        with open(self.RUTA_JSON, 'w') as f:
            json.dump(data, f, indent=4)
        if sincronizar and self.backup_online:
            self.sincronizar_backup(data)

    def sincronizar_backup(self, data):
        try:
            self.push_backup.send_json(data)
            print("[DTI] Sincronización enviada al backup.")
        except Exception as e:
            print(f"[DTI] Error al sincronizar con backup: {e}")

    def recibir_sincronizacion_backup(self):
        """Recibe sincronización desde el backup"""
        while True:
            try:
                data = self.pull_backup_sync.recv_json()
                
                # Solo procesar sincronización si el backup está online
                if self.backup_online:
                    with self.lock:
                        # NO sincronizar de vuelta para evitar bucle
                        self.guardar_recursos(data, sincronizar=False)
                    print("[DTI] Recursos sincronizados desde Backup.")
                else:
                    print("[DTI] ⚠️ Backup offline - Ignorando sincronización entrante")
                    
            except Exception as e:
                print(f"[DTI] Error recibiendo sincronización desde backup: {e}")
                time.sleep(1)

    def escuchar_notificaciones_healthcheck(self):
        """Escucha notificaciones del HealthCheck sobre el estado del Backup"""
        
        time.sleep(1)
        
        while True:
            try:
                mensaje_completo = self.subscriber_healthcheck.recv_string(zmq.NOBLOCK)
                
                if mensaje_completo.startswith("peer_status "):
                    payload = mensaje_completo[12:]
                    data = json.loads(payload)
                    
                    if data.get("peer") == "backup":
                        estado_backup = data.get("estado") == "online"
                        
                        # Detectar si el BACKUP volvió online
                        backup_volvio = not self.backup_online and estado_backup
                        
                        with self.lock:
                            self.backup_online = estado_backup
                        
                        # Si el backup volvió online, enviarle nuestra información
                        if backup_volvio:
                            print(f"[DTI] 🔄 BACKUP volvió online - Enviando nuestra información...")
                            threading.Timer(2.0, self.enviar_sincronizacion_completa).start()
                
            except zmq.Again:
                time.sleep(0.5)
            except Exception as e:
                print(f"[DTI] ❌ Error procesando notificación HealthCheck: {e}")
                time.sleep(1)

    def enviar_sincronizacion_completa(self):
        """Envía sincronización completa al backup cuando vuelve online"""
        try:
            with self.lock:
                recursos = self.cargar_recursos()
            
            print(f"[DTI] 📤 Enviando sincronización completa al Backup: {recursos}")
            self.sincronizar_backup(recursos)
            
        except Exception as e:
            print(f"[DTI] ❌ Error enviando sincronización completa: {e}")


    def procesar_solicitud(self, solicitud):
        if solicitud.get("tipo") == "healthcheck":
            return {"estado": "OK", "servidor": "DTI"}

        if solicitud.get("tipo") == "conexion":
            nombre_facultad = solicitud.get("facultad")
            password_facultad = solicitud.get("password")
            
            # Verificar autenticación de la facultad
            if not password_facultad:
                print(f"[DTI] ✗ Conexión rechazada: Falta contraseña para {nombre_facultad}")
                return {"estado": "Autenticación requerida", "mensaje": "Falta contraseña", "servidor": "DTI"}
            
            if self.auth.verificar_facultad(nombre_facultad, password_facultad):
                print(f"[DTI] ✓ Facultad autenticada: {nombre_facultad}")
                return {"estado": "Conexión aceptada", "mensaje": "Autenticación exitosa", "servidor": "DTI"}
            else:
                print(f"[DTI] ✗ Autenticación fallida para: {nombre_facultad}")
                return {"estado": "Acceso denegado", "mensaje": "Credenciales inválidas", "servidor": "DTI"}

        # Verificar que la solicitud venga de una facultad autenticada
        nombre_facultad = solicitud.get("facultad")
        password_facultad = solicitud.get("password_facultad")
        
        if not password_facultad or not self.auth.verificar_facultad(nombre_facultad, password_facultad):
            print(f"[DTI] ✗ Solicitud rechazada: Facultad no autenticada - {nombre_facultad}")
            return {
                "facultad": nombre_facultad,
                "estado": "Acceso denegado",
                "mensaje": "Facultad no autenticada",
                "servidor": "DTI"
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
    
            # Usar el flag sincronizar=True para que sincronice con el backup
            self.guardar_recursos(recursos, sincronizar=True)
    
        respuesta = {
            "facultad": solicitud.get("facultad", "Desconocida"),
            "programa": solicitud.get("programa", "Desconocido"),
            "estado": estado,
            "salones": salones,
            "laboratorios": laboratorios,
            "servidor": "DTI"
        }
    
        print(f"[DTI] Solicitud procesada: {respuesta}")
        print(f"[DTI] Recursos restantes: Salones={recursos['salones_disponibles']}, Labs={recursos['laboratorios_disponibles']}\n")
        return respuesta
    
    def verificar_conexion_healthcheck(self):
        """Método de prueba para verificar la conexión con HealthCheck"""
        try:
            # Crear un socket temporal para probar
            test_socket = self.context.socket(zmq.SUB)
            test_socket.connect("tcp://10.43.96.34:6008")
            test_socket.setsockopt_string(zmq.SUBSCRIBE, "peer_status")
            test_socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 segundos timeout
            
            print("[DTI] 🧪 Probando conexión con HealthCheck...")
            
            # Intentar recibir un mensaje
            try:
                mensaje = test_socket.recv_string()
                print(f"[DTI] ✅ Mensaje HealthCheck recibido en prueba: {mensaje}")
            except zmq.Again:
                print("[DTI] ⏰ No se recibieron mensajes HealthCheck en 2 segundos")
            
            test_socket.close()
            
        except Exception as e:
            print(f"[DTI] ❌ Error en verificación HealthCheck: {e}")

    def ejecutar(self):
        try:
            while True:
                solicitud = self.receptor.recv_json()

                if solicitud.get("tipo") != "healthcheck":
                    print(f"[DTI] Nueva solicitud recibida: {solicitud}")

                # Solo mostrar tiempo de procesamiento para solicitudes que NO sean healthcheck
                if solicitud.get("tipo") == "healthcheck":
                    respuesta = self.procesar_solicitud(solicitud)
                    self.receptor.send_json(respuesta)
                else:
                    inicio = time.time()
                    respuesta = self.procesar_solicitud(solicitud)
                    fin = time.time()
                    print(f"[DTI] Tiempo de procesamiento: {fin - inicio:.4f} segundos")
                    self.receptor.send_json(respuesta)
        except KeyboardInterrupt:
            print("\n[DTI] Servidor detenido.")
        finally:
            print("[DTI] Cerrando conexiones...")
            try:
                self.receptor.close()
                self.push_backup.close()
                self.pull_backup_sync.close()
                self.subscriber_healthcheck.close()
                self.context.term()
            except Exception as e:
                print(f"[DTI] Error al cerrar conexiones: {e}")

if __name__ == "__main__":
    dti = DTI()
    dti.ejecutar()