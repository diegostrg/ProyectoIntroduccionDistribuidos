import zmq
import time
import json
import threading

# Configuración de servidores
DTI_IP = "localhost"
DTI_PORT = 6000
BACKUP_IP = "localhost"
BACKUP_PORT = 5999
BROKER_PUB_PORT = 7000

# Nuevos puertos para notificar a los servidores
DTI_NOTIFICATION_PORT = 6008    # Puerto para notificar al DTI
BACKUP_NOTIFICATION_PORT = 5998 # Puerto para notificar al Backup

INTERVALO = 3   # segundos entre chequeos
TIMEOUT = 2.0   # timeout de espera

context = zmq.Context()

    # Este programa debe llevar la ip 10.43.96.34


# Socket para notificar al broker
notificador = context.socket(zmq.PUB)
notificador.bind(f"tcp://*:{BROKER_PUB_PORT}")

# Sockets para notificar a los servidores sobre el estado del otro
notificador_dti = context.socket(zmq.PUB)
notificador_dti.bind(f"tcp://*:{DTI_NOTIFICATION_PORT}")

notificador_backup = context.socket(zmq.PUB)
notificador_backup.bind(f"tcp://*:{BACKUP_NOTIFICATION_PORT}")

# Estado de servidores
servidores_anteriores = []
contador_chequeos = 0
estado_anterior = {"dti": False, "backup": False}

def probar_servidor(nombre, ip, puerto):
    """Prueba si un servidor específico está disponible"""
    temp_socket = None
    try:
        temp_socket = context.socket(zmq.REQ)
        temp_socket.RCVTIMEO = int(TIMEOUT * 1000)
        temp_socket.LINGER = 0
        temp_socket.connect(f"tcp://{ip}:{puerto}")
        
        # Enviar healthcheck
        temp_socket.send_json({"tipo": "healthcheck"})
        respuesta = temp_socket.recv_json()
        
        # Verificar respuesta válida
        estado_ok = respuesta.get("estado") == "OK"
        servidor_info = respuesta.get("servidor", "Desconocido")
        print(f"[HealthCheck] ✅ {nombre} ({ip}:{puerto}) - {servidor_info}: {respuesta}")
        return estado_ok
        
    except zmq.Again:
        print(f"[HealthCheck] ❌ {nombre} ({ip}:{puerto}) - Timeout")
        return False
    except Exception as e:
        print(f"[HealthCheck] ❌ {nombre} ({ip}:{puerto}) - Error: {e}")
        return False
    finally:
        if temp_socket:
            temp_socket.close()

def notificar_broker(lista_activos):
    """Notifica al broker sobre el estado de los servidores"""
    try:
        mensaje = {
            "activos": lista_activos,
            "timestamp": time.time(),
            "total_servidores": len(lista_activos)
        }
        
        # Enviar notificación
        notificador.send_string("switch " + json.dumps(mensaje))
        
        estado = "🟢 ACTIVOS" if lista_activos else "🔴 SIN SERVIDORES"
        print(f"[HealthCheck] 📡 Notificado al broker: {estado} = {lista_activos}")
        
    except Exception as e:
        print(f"[HealthCheck] ❌ Error notificando al broker: {e}")

def notificar_servidores_estado(estado_actual):
    """Notifica a cada servidor sobre el estado del otro para sincronización"""
    global estado_anterior
    
    # Detectar cambios en el estado
    dti_volvio = not estado_anterior["dti"] and estado_actual["dti"]
    backup_volvio = not estado_anterior["backup"] and estado_actual["backup"]
    
    # Si el DTI volvió a estar activo, notificar al Backup
    if dti_volvio and estado_actual["backup"]:
        try:
            mensaje_para_backup = {
                "tipo": "peer_recovery",
                "peer": "dti",
                "estado": "online",
                "timestamp": time.time(),
                "accion": "sincronizar_desde_peer"
            }
            notificador_backup.send_string("peer_status " + json.dumps(mensaje_para_backup))
            print(f"[HealthCheck] 🔄 Notificado al Backup: DTI ha vuelto - Sincronizar")
        except Exception as e:
            print(f"[HealthCheck] ❌ Error notificando al Backup sobre DTI: {e}")
    
    # Si el Backup volvió a estar activo, notificar al DTI
    if backup_volvio and estado_actual["dti"]:
        try:
            mensaje_para_dti = {
                "tipo": "peer_recovery",
                "peer": "backup",
                "estado": "online",
                "timestamp": time.time(),
                "accion": "sincronizar_hacia_peer"
            }
            notificador_dti.send_string("peer_status " + json.dumps(mensaje_para_dti))
            print(f"[HealthCheck] 🔄 Notificado al DTI: Backup ha vuelto - Sincronizar")
        except Exception as e:
            print(f"[HealthCheck] ❌ Error notificando al DTI sobre Backup: {e}")
    
    # Notificar siempre el estado actual (para mantener información actualizada)
    try:
        # Notificar al DTI sobre el estado del Backup
        if estado_actual["dti"]:
            mensaje_dti = {
                "tipo": "peer_status",
                "peer": "backup",
                "estado": "online" if estado_actual["backup"] else "offline",
                "timestamp": time.time()
            }
            notificador_dti.send_string("peer_status " + json.dumps(mensaje_dti))
        
        # Notificar al Backup sobre el estado del DTI
        if estado_actual["backup"]:
            mensaje_backup = {
                "tipo": "peer_status",
                "peer": "dti",
                "estado": "online" if estado_actual["dti"] else "offline",
                "timestamp": time.time()
            }
            notificador_backup.send_string("peer_status " + json.dumps(mensaje_backup))
            
    except Exception as e:
        print(f"[HealthCheck] ❌ Error enviando estado general: {e}")
    
    # Actualizar estado anterior
    estado_anterior = estado_actual.copy()

def monitorear_servidores():
    """Función principal de monitoreo"""
    global contador_chequeos
    
    print("[HealthCheck] 🚀 Iniciando monitor de servidores mejorado...")
    print(f"[HealthCheck] ⏰ Intervalo: {INTERVALO}s | Timeout: {TIMEOUT}s")
    print(f"[HealthCheck] 📡 Puerto broker: {BROKER_PUB_PORT}")
    print(f"[HealthCheck] 📡 Puerto notif DTI: {DTI_NOTIFICATION_PORT}")
    print(f"[HealthCheck] 📡 Puerto notif Backup: {BACKUP_NOTIFICATION_PORT}")
    print("=" * 70)
    
    # Dar tiempo a los sockets para conectarse
    time.sleep(2)
    
    while True:
        try:
            contador_chequeos += 1
            timestamp = time.strftime('%H:%M:%S')
            print(f"\n[HealthCheck] 🔍 Chequeo #{contador_chequeos} - {timestamp}")
            
            # Verificar estado de ambos servidores
            estado_actual = {
                "dti": probar_servidor("DTI Principal", DTI_IP, DTI_PORT),
                "backup": probar_servidor("DTI Backup", BACKUP_IP, BACKUP_PORT)
            }
            
            # Crear lista para el broker
            servidores_disponibles = []
            if estado_actual["dti"]:
                servidores_disponibles.append("dti")
            if estado_actual["backup"]:
                servidores_disponibles.append("backup")
            
            # Mostrar resumen
            print(f"[HealthCheck] 📊 Estado: DTI={'🟢' if estado_actual['dti'] else '🔴'} | "
                  f"Backup={'🟢' if estado_actual['backup'] else '🔴'} | "
                  f"Total: {len(servidores_disponibles)}/2")
            
            # Notificar al broker
            notificar_broker(servidores_disponibles)
            
            # Notificar a los servidores sobre el estado del otro
            notificar_servidores_estado(estado_actual)
            
            # Mostrar cambios específicos
            if estado_actual != estado_anterior:
                print(f"[HealthCheck] 🔄 CAMBIOS DETECTADOS:")
                
                if estado_anterior["dti"] != estado_actual["dti"]:
                    estado_dti = "CONECTADO" if estado_actual["dti"] else "DESCONECTADO"
                    emoji_dti = "🟢" if estado_actual["dti"] else "🔴"
                    print(f"    DTI Principal: {emoji_dti} {estado_dti}")
                
                if estado_anterior["backup"] != estado_actual["backup"]:
                    estado_backup = "CONECTADO" if estado_actual["backup"] else "DESCONECTADO"
                    emoji_backup = "🟢" if estado_actual["backup"] else "🔴"
                    print(f"    DTI Backup: {emoji_backup} {estado_backup}")
            
            # Advertencias
            if not estado_actual["dti"] and not estado_actual["backup"]:
                print("[HealthCheck] ⚠️  ALERTA CRÍTICA: Ningún servidor disponible!")
            elif not estado_actual["dti"]:
                print("[HealthCheck] ⚠️  ADVERTENCIA: DTI Principal fuera de línea")
            elif not estado_actual["backup"]:
                print("[HealthCheck] ⚠️  ADVERTENCIA: DTI Backup fuera de línea")
            
            # Esperar antes del siguiente chequeo
            time.sleep(INTERVALO)
            
        except KeyboardInterrupt:
            print("\n[HealthCheck] 🛑 Deteniendo monitor...")
            break
        except Exception as e:
            print(f"[HealthCheck] ❌ Error en monitoreo: {e}")
            time.sleep(INTERVALO)

def cleanup():
    """Limpia todos los recursos"""
    print("[HealthCheck] 🧹 Cerrando sockets...")
    try:
        notificador.close()
        notificador_dti.close()
        notificador_backup.close()
        context.term()
    except:
        pass
    print("[HealthCheck] 🔚 Recursos liberados")

if __name__ == "__main__":
    try:
        monitorear_servidores()
    except KeyboardInterrupt:
        print("\n[HealthCheck] ✋ Monitor detenido por usuario")
    finally:
        cleanup()