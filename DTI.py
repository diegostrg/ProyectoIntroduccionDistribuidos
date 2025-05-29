import zmq
import json
import os
import threading
import time
from AutenticacionDTI import AutenticacionDTI

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

        # Nuevo: Socket SUB para escuchar notificaciones del HealthCheck
        self.subscriber_healthcheck = self.context.socket(zmq.SUB)
        self.subscriber_healthcheck.connect("tcp://localhost:6008")  # Puerto de notificaciones para DTI
        self.subscriber_healthcheck.setsockopt_string(zmq.SUBSCRIBE, "peer_status")
        threading.Thread(target=self.escuchar_notificaciones_healthcheck, daemon=True).start()

        self.RUTA_JSON = "recursos_dti.json"
        self.lock = threading.Lock()
        self.backup_online = False  # Estado del backup
        
        # Sistema de autenticación
        self.auth = AutenticacionDTI()
        self.auth.mostrar_credenciales_iniciales()

        print(f"[DTI] Servidor iniciado en puerto {puerto_rep} y esperando solicitudes...")
        print(f"[DTI] Escuchando notificaciones de HealthCheck en puerto 6008")
        self._inicializar_recursos()

    def escuchar_notificaciones_healthcheck(self):
        """Escucha notificaciones del HealthCheck sobre el estado del Backup"""
        print("[DTI] 🎧 Iniciando escucha de notificaciones HealthCheck...")
        
        while True:
            try:
                mensaje_completo = self.subscriber_healthcheck.recv_string(zmq.NOBLOCK)
                
                if mensaje_completo.startswith("peer_status "):
                    payload = mensaje_completo[12:]  # Remover "peer_status "
                    data = json.loads(payload)
                    
                    if data.get("peer") == "backup":
                        estado_backup = data.get("estado") == "online"
                        tipo_notificacion = data.get("tipo", "peer_status")
                        
                        # Detectar si el backup volvió online
                        backup_volvio = not self.backup_online and estado_backup
                        
                        with self.lock:
                            self.backup_online = estado_backup
                        
                        if tipo_notificacion == "peer_recovery" and data.get("accion") == "sincronizar_hacia_peer":
                            print(f"[DTI] 🔄 BACKUP HA VUELTO - Iniciando sincronización...")
                            self.forzar_sincronizacion_completa()
                        elif backup_volvio:
                            print(f"[DTI] 🟢 Backup detectado online - Preparando sincronización")
                            # Dar un momento al backup para estar completamente listo
                            threading.Timer(2.0, self.forzar_sincronizacion_completa).start()
                        elif not estado_backup:
                            print(f"[DTI] 🔴 Backup detectado offline")
                
            except zmq.Again:
                time.sleep(0.1)
            except Exception as e:
                print(f"[DTI] ❌ Error procesando notificación HealthCheck: {e}")
                time.sleep(1)

    def forzar_sincronizacion_completa(self):
        """Fuerza una sincronización completa con el backup"""
        try:
            with self.lock:
                recursos = self.cargar_recursos()
            
            print(f"[DTI] 📤 Forzando sincronización completa: {recursos}")
            self.sincronizar_backup(recursos)
            
            # Enviar mensaje especial indicando sincronización completa
            mensaje_sync = {
                "tipo": "sync_completa",
                "recursos": recursos,
                "timestamp": time.time(),
                "servidor_origen": "DTI"
            }
            
            self.push_backup.send_json(mensaje_sync)
            print(f"[DTI] ✅ Sincronización completa enviada al Backup")
            
        except Exception as e:
            print(f"[DTI] ❌ Error en sincronización forzada: {e}")

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

    def recibir_sincronizacion_del_backup(self):
        while True:
            try:
                data = self.pull_backup_sync.recv_json()
                
                # Verificar si es una sincronización especial
                if isinstance(data, dict) and data.get("tipo") == "sync_completa":
                    print("[DTI] 📥 Recibida sincronización completa desde Backup")
                    recursos = data.get("recursos", data)
                else:
                    recursos = data
                
                with self.lock:
                    # NO sincronizar de vuelta para evitar bucle
                    self.guardar_recursos(recursos, sincronizar=False)
                print("[DTI] Recursos sincronizados desde BACKUP.")
            except Exception as e:
                print(f"[DTI] Error recibiendo sincronización desde backup: {e}")
                time.sleep(1)

    def procesar_solicitud(self, solicitud):
        if solicitud.get("tipo") == "healthcheck":
            print("[DTI] Healthcheck recibido.")
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

    def ejecutar(self):
        try:
            while True:
                solicitud = self.receptor.recv_json()
                print(f"[DTI] Nueva solicitud recibida: {solicitud}")

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