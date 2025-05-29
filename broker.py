import zmq
import threading
import json
import time

class BrokerBalanceador:
    def __init__(self):
        self.context = zmq.Context()
        
        # Conexiones a servidores DTI
        self.backend_dti = self.context.socket(zmq.DEALER)
        self.backend_dti.connect("tcp://localhost:6000")
        
        self.backend_backup = self.context.socket(zmq.DEALER)
        self.backend_backup.connect("tcp://localhost:5999")
        
        # Frontend para facultades
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind("tcp://*:7001")  # Puerto para facultades
        
        # Subscriber para healthcheck
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect("tcp://localhost:7000")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "switch")
        
        # Estado del broker
        self.servidores = {
            "dti": self.backend_dti,
            "backup": self.backend_backup
        }
        
        self.servidores_activos = ["dti", "backup"]  # Iniciar con ambos servidores activos.
        self.indice_actual = 0
        self.lock = threading.Lock()
        self.mapa_respuestas = {}
        self.estadisticas = {
            "solicitudes_procesadas": 0,
            "solicitudes_dti": 0,
            "solicitudes_backup": 0,
            "errores": 0
        }
        
        print("[Broker] 🚀 Inicializando Broker Balanceador...")
        print("[Broker] 📡 Escuchando facultades en puerto 7001")
        print("[Broker] 🔍 Escuchando healthcheck en puerto 7000")
    
    def recibir_notificaciones_healthcheck(self):
        """Recibe notificaciones del HealthCheck sobre servidores activos"""
        print("[Broker] 🎧 Hilo de notificaciones iniciado...")
        
        while True:
            try:
                # Recibir mensaje del healthcheck
                mensaje_completo = self.subscriber.recv_string(zmq.NOBLOCK)
                
                # Parsear mensaje: "switch {json_data}"
                if mensaje_completo.startswith("switch "):
                    payload = mensaje_completo[7:]  # Remover "switch "
                    data = json.loads(payload)
                    
                    nuevos_activos = data.get("activos", [])
                    timestamp = data.get("timestamp", time.time())
                    
                    with self.lock:
                        # Actualizar lista de servidores activos
                        servidores_anteriores = self.servidores_activos.copy()
                        self.servidores_activos = nuevos_activos
                        
                        # Mostrar cambios
                        if servidores_anteriores != self.servidores_activos:
                            print(f"\n[Broker] 🔄 ACTUALIZACIÓN DE SERVIDORES:")
                            print(f"    Anterior: {servidores_anteriores}")
                            print(f"    Nuevo:    {self.servidores_activos}")
                        
                        if self.servidores_activos:
                            print(f"[Broker] ✅ Servidores disponibles: {self.servidores_activos}")
                        else:
                            print(f"[Broker] ❌ SIN SERVIDORES DISPONIBLES")
                
            except zmq.Again:
                # No hay mensajes disponibles, continuar
                time.sleep(0.1)
            except Exception as e:
                print(f"[Broker] ❌ Error en notificaciones: {e}")
                time.sleep(1)
    
    def seleccionar_servidor(self):
        """Selecciona el siguiente servidor usando Round-Robin"""
        with self.lock:
            if not self.servidores_activos:
                return None, None
            
            servidor = self.servidores_activos[self.indice_actual % len(self.servidores_activos)]
            socket_destino = self.servidores[servidor]
            
            # Avanzar al siguiente servidor
            self.indice_actual += 1
            
            return servidor, socket_destino
    
    def procesar_solicitudes(self):
        """Maneja las solicitudes de facultades y respuestas de servidores"""
        print("[Broker] 🔄 Procesador de solicitudes iniciado...")
        
        poller = zmq.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        poller.register(self.backend_dti, zmq.POLLIN)
        poller.register(self.backend_backup, zmq.POLLIN)
        
        while True:
            try:
                socks = dict(poller.poll(timeout=1000))  # 1 segundo timeout
                
                # Procesar solicitudes de facultades
                if self.frontend in socks:
                    self._procesar_solicitud_facultad()
                
                # Procesar respuestas de servidores
                for servidor_nombre, socket_servidor in self.servidores.items():
                    if socket_servidor in socks:
                        self._procesar_respuesta_servidor(servidor_nombre, socket_servidor)
                
            except Exception as e:
                print(f"[Broker] ❌ Error procesando: {e}")
                self.estadisticas["errores"] += 1
    
    def _procesar_solicitud_facultad(self):
        """Procesa una solicitud de una facultad"""
        try:
            identidad, _, mensaje = self.frontend.recv_multipart()
            
            # Parsear solicitud para obtener información
            try:
                solicitud = json.loads(mensaje.decode())
                facultad = solicitud.get("facultad", "Desconocida")
                tipo_solicitud = solicitud.get("tipo", "recurso")
            except:
                facultad = "Desconocida"
                tipo_solicitud = "desconocido"
            
            # Seleccionar servidor disponible
            servidor, socket_destino = self.seleccionar_servidor()
            
            if not servidor or not socket_destino:
                # No hay servidores disponibles
                print(f"[Broker] ❌ Sin servidores para '{facultad}' - Rechazando solicitud")
                
                respuesta_error = json.dumps({
                    "estado": "Error",
                    "mensaje": "No hay servidores disponibles",
                    "facultad": facultad
                }).encode()
                
                self.frontend.send_multipart([identidad, b'', respuesta_error])
                self.estadisticas["errores"] += 1
                return
            
            # Enviar solicitud al servidor seleccionado
            socket_destino.send_multipart([identidad, b'', mensaje])
            self.mapa_respuestas[identidad] = self.frontend
            
            # Actualizar estadísticas
            self.estadisticas["solicitudes_procesadas"] += 1
            if servidor == "dti":
                self.estadisticas["solicitudes_dti"] += 1
            elif servidor == "backup":
                self.estadisticas["solicitudes_backup"] += 1
            
            print(f"[Broker] 📤 Solicitud #{self.estadisticas['solicitudes_procesadas']}: "
                  f"'{facultad}' → {servidor.upper()} ({tipo_solicitud})")
            
        except Exception as e:
            print(f"[Broker] ❌ Error procesando solicitud: {e}")
            self.estadisticas["errores"] += 1
    
    def _procesar_respuesta_servidor(self, servidor_nombre, socket_servidor):
        """Procesa una respuesta de un servidor"""
        try:
            identidad, _, respuesta = socket_servidor.recv_multipart()
            
            if identidad in self.mapa_respuestas:
                # Reenviar respuesta a la facultad
                frontend_socket = self.mapa_respuestas[identidad]
                frontend_socket.send_multipart([identidad, b'', respuesta])
                
                # Limpiar mapeo
                del self.mapa_respuestas[identidad]
                
                # Log de respuesta
                try:
                    resp_data = json.loads(respuesta.decode())
                    estado = resp_data.get("estado", "desconocido")
                    facultad = resp_data.get("facultad", "N/A")
                    print(f"[Broker] 📥 Respuesta: {servidor_nombre.upper()} → '{facultad}' ({estado})")
                except:
                    print(f"[Broker] 📥 Respuesta: {servidor_nombre.upper()} → (datos binarios)")
            else:
                print(f"[Broker] ⚠️  Respuesta huérfana de {servidor_nombre}")
                
        except Exception as e:
            print(f"[Broker] ❌ Error procesando respuesta de {servidor_nombre}: {e}")
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas del broker cada 30 segundos"""
        while True:
            time.sleep(30)
            with self.lock:
                activos = len(self.servidores_activos)
                total = self.estadisticas["solicitudes_procesadas"]
                dti = self.estadisticas["solicitudes_dti"]
                backup = self.estadisticas["solicitudes_backup"]
                errores = self.estadisticas["errores"]
                
                print(f"\n[Broker] 📊 ESTADÍSTICAS:")
                print(f"    Servidores activos: {activos}/2 {self.servidores_activos}")
                print(f"    Solicitudes totales: {total}")
                print(f"    DTI: {dti} | Backup: {backup} | Errores: {errores}")
                print(f"    Solicitudes pendientes: {len(self.mapa_respuestas)}")
    
    def ejecutar(self):
        """Inicia todos los hilos del broker"""
        try:
            # Iniciar hilos
            threading.Thread(target=self.recibir_notificaciones_healthcheck, daemon=True).start()
            threading.Thread(target=self.mostrar_estadisticas, daemon=True).start()
            
            print("[Broker] ✅ Todos los hilos iniciados")
            print("[Broker] 🔄 Iniciando procesamiento principal...")
            print("=" * 60)
            
            # Procesar solicitudes (hilo principal)
            self.procesar_solicitudes()
            
        except KeyboardInterrupt:
            print("\n[Broker] 🛑 Deteniendo broker...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Limpia recursos del broker"""
        print("[Broker] 🧹 Limpiando recursos...")
        try:
            self.frontend.close()
            self.backend_dti.close()
            self.backend_backup.close()
            self.subscriber.close()
            self.context.term()
        except:
            pass
        print("[Broker] ✅ Broker terminado")

if __name__ == "__main__":
    broker = BrokerBalanceador()
    broker.ejecutar()