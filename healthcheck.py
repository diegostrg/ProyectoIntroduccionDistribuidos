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

INTERVALO = 3   # segundos entre chequeos
TIMEOUT = 2.0   # timeout de espera

context = zmq.Context()

# Socket para notificar al broker
notificador = context.socket(zmq.PUB)
notificador.bind(f"tcp://*:{BROKER_PUB_PORT}")

# Estado de servidores
servidores_anteriores = []
contador_chequeos = 0

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
        print(f"[HealthCheck] ✅ {nombre} ({ip}:{puerto}) - Respuesta: {respuesta}")
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

def monitorear_servidores():
    """Función principal de monitoreo"""
    global servidores_anteriores, contador_chequeos
    
    print("[HealthCheck] 🚀 Iniciando monitor de servidores...")
    print(f"[HealthCheck] ⏰ Intervalo: {INTERVALO}s | Timeout: {TIMEOUT}s")
    print(f"[HealthCheck] 📡 Puerto notificación: {BROKER_PUB_PORT}")
    print("=" * 60)
    
    # Dar tiempo al broker para conectarse
    time.sleep(2)
    
    while True:
        try:
            contador_chequeos += 1
            print(f"\n[HealthCheck] 🔍 Chequeo #{contador_chequeos} - {time.strftime('%H:%M:%S')}")
            
            servidores_disponibles = []
            
            # Verificar DTI Principal
            if probar_servidor("DTI Principal", DTI_IP, DTI_PORT):
                servidores_disponibles.append("dti")
            
            # Verificar DTI Backup
            if probar_servidor("DTI Backup", BACKUP_IP, BACKUP_PORT):
                servidores_disponibles.append("backup")
            
            # Mostrar resumen
            print(f"[HealthCheck] 📊 Resultado: {len(servidores_disponibles)}/2 servidores activos")
            
            # Notificar siempre al broker (no solo en cambios)
            # Esto asegura que el broker mantenga la información actualizada
            notificar_broker(servidores_disponibles)
            
            # Mostrar estado si cambió
            if servidores_disponibles != servidores_anteriores:
                if servidores_anteriores:  # No mostrar en el primer chequeo
                    print(f"[HealthCheck] 🔄 CAMBIO DETECTADO:")
                    print(f"    Anterior: {servidores_anteriores}")
                    print(f"    Actual:   {servidores_disponibles}")
                
                servidores_anteriores = servidores_disponibles.copy()
            
            # Advertencia si no hay servidores
            if not servidores_disponibles:
                print("[HealthCheck] ⚠️  ALERTA: Ningún servidor disponible!")
            
            # Esperar antes del siguiente chequeo
            time.sleep(INTERVALO)
            
        except KeyboardInterrupt:
            print("\n[HealthCheck] 🛑 Deteniendo monitor...")
            break
        except Exception as e:
            print(f"[HealthCheck] ❌ Error en monitoreo: {e}")
            time.sleep(INTERVALO)

if __name__ == "__main__":
    try:
        monitorear_servidores()
    except KeyboardInterrupt:
        print("\n[HealthCheck] ✋ Monitor detenido por usuario")
    finally:
        notificador.close()
        context.term()
        print("[HealthCheck] 🔚 Recursos liberados")