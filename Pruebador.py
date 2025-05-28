import zmq
import json
import os
import threading
import time
import random
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

class Pruebador:
    def __init__(self):
        self.context = zmq.Context()
        self.archivos_recursos = [
            "recursos_dti.json",
            "recursos_backup.json"
        ]
        
        # Datos para gráficas
        self.datos_rendimiento = {
            "DTI Principal": {"tiempos": [], "timestamps": [], "estados": []},
            "DTI Backup": {"tiempos": [], "timestamps": [], "estados": []}
        }
        
    def mostrar_menu(self):
        print("\n" + "="*60)
        print("           SISTEMA DE PRUEBAS - DTI DISTRIBUIDO")
        print("="*60)
        print("1.  Probar conexión al DTI Principal (puerto 6000)")
        print("2.  Probar conexión al DTI Backup (puerto 5999)")
        print("3.  Probar envío masivo de solicitudes al DTI")
        print("4.  Probar envío masivo de solicitudes al Backup")
        print("5.  Probar falla del DTI (simulación)")
        print("6.  Verificar sincronización entre servidores")
        print("7.  Ver estado de recursos en archivos JSON")
        print("8.  Comparar archivos de recursos")
        print("9.  Monitoreo en tiempo real con gráficas")
        print("10. Stress test - Solicitudes concurrentes")
        print("11. Comparación de rendimiento DTI vs Backup")
        print("12. Limpiar y reinicializar archivos de recursos")
        print("13. Generar reporte de rendimiento con gráficas")
        print("14. Gráfica de utilización de recursos")
        print("0.  Salir")
        print("="*60)
        

    def monitoreo_tiempo_real(self):
        """Monitoreo en tiempo real con gráficas actualizadas"""
        print("\n[MONITOREO] Iniciando monitoreo en tiempo real...")
        print("Presione Ctrl+C para detener el monitoreo")
        
        # Configurar la gráfica
        plt.ion()  # Modo interactivo
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle('Monitoreo DTI en Tiempo Real', fontsize=16)
        
        # Datos para el monitoreo
        timestamps = []
        tiempos_dti = []
        tiempos_backup = []
        
        try:
            while True:
                timestamp = datetime.now()
                
                # Probar DTI Principal
                tiempo_dti = self._medir_tiempo_respuesta(6000, "DTI Principal")
                if tiempo_dti:
                    tiempos_dti.append(tiempo_dti * 1000)  # Convertir a ms
                else:
                    tiempos_dti.append(None)
                
                # Probar DTI Backup
                tiempo_backup = self._medir_tiempo_respuesta(5999, "DTI Backup")
                if tiempo_backup:
                    tiempos_backup.append(tiempo_backup * 1000)  # Convertir a ms
                else:
                    tiempos_backup.append(None)
                
                timestamps.append(timestamp)
                
                # Mantener solo los últimos 20 puntos
                if len(timestamps) > 20:
                    timestamps = timestamps[-20:]
                    tiempos_dti = tiempos_dti[-20:]
                    tiempos_backup = tiempos_backup[-20:]
                
                # Actualizar gráfica de tiempos de respuesta
                ax1.clear()
                if any(t for t in tiempos_dti if t is not None):
                    ax1.plot([t.strftime('%H:%M:%S') for t in timestamps], 
                            [t if t is not None else 0 for t in tiempos_dti], 
                            'b-o', label='DTI Principal', linewidth=2)
                if any(t for t in tiempos_backup if t is not None):
                    ax1.plot([t.strftime('%H:%M:%S') for t in timestamps], 
                            [t if t is not None else 0 for t in tiempos_backup], 
                            'r-o', label='DTI Backup', linewidth=2)
                
                ax1.set_title('Tiempo de Respuesta (ms)')
                ax1.set_ylabel('Milisegundos')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                ax1.tick_params(axis='x', rotation=45)
                
                # Gráfica de estado de recursos
                self._actualizar_grafica_recursos(ax2)
                
                plt.tight_layout()
                plt.pause(2)  # Actualizar cada 2 segundos
                
        except KeyboardInterrupt:
            print("\n[MONITOREO] Detenido por el usuario")
        finally:
            plt.ioff()
            plt.show()
    
    def _medir_tiempo_respuesta(self, puerto, servidor_nombre):
        """Mide el tiempo de respuesta de un servidor"""
        socket = None
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 3000)  # Timeout reducido
            socket.connect(f"tcp://localhost:{puerto}")
            
            mensaje_prueba = {
                "tipo": "conexion",
                "facultad": f"Monitor {servidor_nombre}"
            }
            
            inicio = time.time()
            socket.send_json(mensaje_prueba)
            respuesta = socket.recv_json()
            fin = time.time()
            
            return fin - inicio
            
        except Exception:
            return None
        finally:
            if socket:
                socket.close()
    
    def _actualizar_grafica_recursos(self, ax):
        """Actualiza la gráfica de recursos disponibles"""
        recursos_data = []
        labels = []
        
        for archivo in self.archivos_recursos:
            if os.path.exists(archivo):
                try:
                    with open(archivo, 'r') as f:
                        contenido = json.load(f)
                    
                    nombre = archivo.replace('recursos_', '').replace('.json', '')
                    labels.append(nombre)
                    recursos_data.append([
                        contenido.get('salones_disponibles', 0),
                        contenido.get('laboratorios_disponibles', 0)
                    ])
                except:
                    pass
        
        if recursos_data:
            ax.clear()
            x = np.arange(len(labels))
            width = 0.35
            
            salones = [r[0] for r in recursos_data]
            labs = [r[1] for r in recursos_data]
            
            ax.bar(x - width/2, salones, width, label='Salones', color='skyblue')
            ax.bar(x + width/2, labs, width, label='Laboratorios', color='lightcoral')
            
            ax.set_title('Recursos Disponibles')
            ax.set_ylabel('Cantidad')
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.legend()
            ax.grid(True, alpha=0.3)
    
    def comparacion_rendimiento_servidores(self):
        """Compara el rendimiento entre DTI Principal y Backup"""
        print("\n[COMPARACIÓN] Analizando rendimiento DTI vs Backup...")
        
        servidores = [
            {"nombre": "DTI Principal", "puerto": 6000, "color": "blue"},
            {"nombre": "DTI Backup", "puerto": 5999, "color": "red"}
        ]
        
        num_pruebas = int(input("Número de pruebas por servidor (default 20): ") or "20")
        
        resultados = {}
        
        for servidor in servidores:
            print(f"Probando {servidor['nombre']}...")
            tiempos = []
            exitosas = 0
            
            for i in range(num_pruebas):
                socket = None
                try:
                    socket = self.context.socket(zmq.REQ)
                    socket.setsockopt(zmq.RCVTIMEO, 5000)
                    socket.connect(f"tcp://localhost:{servidor['puerto']}")
                    
                    solicitud = {
                        "facultad": f"Facultad Test {i}",
                        "programa": f"Programa Test {i}",
                        "salones": random.randint(1, 5),
                        "laboratorios": random.randint(1, 3)
                    }
                    
                    inicio = time.time()
                    socket.send_json(solicitud)
                    respuesta = socket.recv_json()
                    fin = time.time()
                    
                    tiempo_respuesta = (fin - inicio) * 1000  # ms
                    tiempos.append(tiempo_respuesta)
                    
                    if respuesta.get("estado") == "Aceptado":
                        exitosas += 1
                    
                    print(f"  Prueba {i+1}/{num_pruebas}: {tiempo_respuesta:.2f}ms")
                    
                except Exception as e:
                    print(f"  Prueba {i+1}/{num_pruebas}: Error - {e}")
                finally:
                    if socket:
                        socket.close()
            
            resultados[servidor['nombre']] = {
                'tiempos': tiempos,
                'exitosas': exitosas,
                'color': servidor['color']
            }
        
        # Crear gráficas comparativas
        self._crear_graficas_comparacion(resultados, num_pruebas)
    
    def _crear_graficas_comparacion(self, resultados, num_pruebas):
        """Crea gráficas comparativas de rendimiento"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Comparación de Rendimiento: DTI Principal vs Backup', fontsize=16)
        
        # Gráfica 1: Histograma de tiempos de respuesta
        for nombre, datos in resultados.items():
            if datos['tiempos']:
                ax1.hist(datos['tiempos'], bins=15, alpha=0.7, 
                        label=nombre, color=datos['color'])
        ax1.set_title('Distribución de Tiempos de Respuesta')
        ax1.set_xlabel('Tiempo (ms)')
        ax1.set_ylabel('Frecuencia')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Gráfica 2: Box plot comparativo
        tiempos_lista = []
        labels = []
        for nombre, datos in resultados.items():
            if datos['tiempos']:
                tiempos_lista.append(datos['tiempos'])
                labels.append(nombre)
        
        if tiempos_lista:
            ax2.boxplot(tiempos_lista, labels=labels)
            ax2.set_title('Comparación de Tiempos (Box Plot)')
            ax2.set_ylabel('Tiempo (ms)')
            ax2.grid(True, alpha=0.3)
        
        # Gráfica 3: Tasa de éxito
        nombres = list(resultados.keys())
        tasas_exito = [datos['exitosas']/num_pruebas*100 for datos in resultados.values()]
        colores = [datos['color'] for datos in resultados.values()]
        
        ax3.bar(nombres, tasas_exito, color=colores, alpha=0.7)
        ax3.set_title('Tasa de Éxito (%)')
        ax3.set_ylabel('Porcentaje')
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3)
        
        # Gráfica 4: Estadísticas resumidas
        estadisticas = []
        for nombre, datos in resultados.items():
            if datos['tiempos']:
                stats = {
                    'Promedio': np.mean(datos['tiempos']),
                    'Mediana': np.median(datos['tiempos']),
                    'Min': np.min(datos['tiempos']),
                    'Max': np.max(datos['tiempos'])
                }
                estadisticas.append(stats)
        
        if estadisticas:
            x = np.arange(len(list(estadisticas[0].keys())))
            width = 0.35
            
            for i, (nombre, datos) in enumerate(resultados.items()):
                if datos['tiempos']:
                    valores = list(estadisticas[i].values())
                    ax4.bar(x + i*width, valores, width, 
                           label=nombre, color=datos['color'], alpha=0.7)
            
            ax4.set_title('Estadísticas Comparativas (ms)')
            ax4.set_ylabel('Tiempo (ms)')
            ax4.set_xticks(x + width/2)
            ax4.set_xticklabels(list(estadisticas[0].keys()))
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar gráfica
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"comparacion_rendimiento_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"\n✓ Gráficas guardadas en: {filename}")
        
        plt.show()
    
    def grafica_utilizacion_recursos(self):
        """Genera gráfica de utilización de recursos a lo largo del tiempo"""
        print("\n[UTILIZACIÓN] Generando gráfica de utilización de recursos...")
        
        # Simular cambios en recursos enviando solicitudes
        num_solicitudes = int(input("Número de solicitudes para simular (default 15): ") or "15")
        servidor = input("Servidor a probar (6000=DTI, 5999=Backup, default 6000): ") or "6000"
        
        historial_recursos = []
        timestamps = []
        
        for i in range(num_solicitudes):
            # Registrar estado actual
            if os.path.exists("recursos_dti.json"):
                with open("recursos_dti.json", 'r') as f:
                    recursos = json.load(f)
                    historial_recursos.append({
                        'salones': recursos.get('salones_disponibles', 0),
                        'laboratorios': recursos.get('laboratorios_disponibles', 0)
                    })
                    timestamps.append(datetime.now())
            
            # Enviar solicitud
            socket = None
            try:
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 5000)
                socket.connect(f"tcp://localhost:{servidor}")
                
                solicitud = {
                    "facultad": f"Facultad Utilización {i}",
                    "programa": f"Programa Util {i}",
                    "salones": random.randint(1, 10),
                    "laboratorios": random.randint(1, 5)
                }
                
                socket.send_json(solicitud)
                respuesta = socket.recv_json()
                print(f"Solicitud {i+1}: {respuesta.get('estado', 'Error')}")
                
            except Exception as e:
                print(f"Error en solicitud {i+1}: {e}")
            finally:
                if socket:
                    socket.close()
            
            time.sleep(0.5)  # Pausa entre solicitudes
        
        # Crear gráfica de utilización
        if historial_recursos:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            fig.suptitle('Utilización de Recursos a lo largo del Tiempo', fontsize=16)
            
            salones = [r['salones'] for r in historial_recursos]
            laboratorios = [r['laboratorios'] for r in historial_recursos]
            tiempos = [t.strftime('%H:%M:%S') for t in timestamps]
            
            # Gráfica de líneas
            ax1.plot(tiempos, salones, 'b-o', label='Salones Disponibles', linewidth=2)
            ax1.plot(tiempos, laboratorios, 'r-o', label='Laboratorios Disponibles', linewidth=2)
            ax1.set_title('Recursos Disponibles vs Tiempo')
            ax1.set_ylabel('Cantidad')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
            
            # Gráfica de área apilada
            ax2.fill_between(range(len(salones)), salones, alpha=0.5, color='blue', label='Salones')
            ax2.fill_between(range(len(laboratorios)), laboratorios, alpha=0.5, color='red', label='Laboratorios')
            ax2.set_title('Área de Utilización')
            ax2.set_xlabel('Número de Solicitud')
            ax2.set_ylabel('Cantidad')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Guardar gráfica
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"utilizacion_recursos_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"\n✓ Gráfica guardada en: {filename}")
            
            plt.show()
    

    def probar_conexion_dti(self):
        print("\n[PRUEBA] Probando conexión al DTI Principal...")
        socket = None
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # Timeout 5 segundos
            socket.connect("tcp://localhost:6000")
            
            mensaje_prueba = {
                "tipo": "conexion",
                "facultad": "Facultad de Pruebas"
            }
            
            inicio = time.time()
            socket.send_json(mensaje_prueba)
            respuesta = socket.recv_json()
            fin = time.time()
            
            print(f"✓ Conexión exitosa al DTI")
            print(f"  Respuesta: {respuesta}")
            print(f"  Tiempo de respuesta: {fin - inicio:.4f} segundos")
            
            return True
            
        except Exception as e:
            print(f"✗ Error conectando al DTI: {e}")
            return False
        finally:
            if socket:
                socket.close()
    
    def probar_conexion_backup(self):
        print("\n[PRUEBA] Probando conexión al DTI Backup...")
        socket = None
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)
            socket.connect("tcp://localhost:5999")
            
            mensaje_prueba = {
                "tipo": "conexion", 
                "facultad": "Facultad de Pruebas Backup"
            }
            
            inicio = time.time()
            socket.send_json(mensaje_prueba)
            respuesta = socket.recv_json()
            fin = time.time()
            
            print(f"✓ Conexión exitosa al DTI Backup")
            print(f"  Respuesta: {respuesta}")
            print(f"  Tiempo de respuesta: {fin - inicio:.4f} segundos")
            
            return True
            
        except Exception as e:
            print(f"✗ Error conectando al DTI Backup: {e}")
            return False
        finally:
            if socket:
                socket.close()
    
    def envio_masivo_solicitudes(self, puerto, servidor_nombre, num_solicitudes=10):
        print(f"\n[PRUEBA] Enviando {num_solicitudes} solicitudes masivas a {servidor_nombre}...")
        
        socket = None
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 10000)
            socket.connect(f"tcp://localhost:{puerto}")
            
            tiempos_respuesta = []
            solicitudes_exitosas = 0
            solicitudes_rechazadas = 0
            
            for i in range(num_solicitudes):
                solicitud = {
                    "facultad": f"Facultad Prueba {i+1}",
                    "programa": f"Programa Test {i+1}",
                    "salones": random.randint(1, 20),
                    "laboratorios": random.randint(1, 10)
                }
                
                try:
                    inicio = time.time()
                    socket.send_json(solicitud)
                    respuesta = socket.recv_json()
                    fin = time.time()
                    
                    tiempo_respuesta = fin - inicio
                    tiempos_respuesta.append(tiempo_respuesta)
                    
                    if respuesta.get("estado") == "Aceptado":
                        solicitudes_exitosas += 1
                    else:
                        solicitudes_rechazadas += 1
                        
                    print(f"  Solicitud {i+1}: {respuesta['estado']} - {tiempo_respuesta:.4f}s")
                    
                except Exception as e:
                    print(f"  Solicitud {i+1}: Error - {e}")
            
            if tiempos_respuesta:
                print(f"\n--- RESUMEN {servidor_nombre} ---")
                print(f"Solicitudes exitosas: {solicitudes_exitosas}")
                print(f"Solicitudes rechazadas: {solicitudes_rechazadas}")
                print(f"Tiempo promedio: {sum(tiempos_respuesta)/len(tiempos_respuesta):.4f}s")
                print(f"Tiempo mínimo: {min(tiempos_respuesta):.4f}s")
                print(f"Tiempo máximo: {max(tiempos_respuesta):.4f}s")
            
        except Exception as e:
            print(f"✗ Error en envío masivo: {e}")
        finally:
            if socket:
                socket.close()

    def verificar_sincronizacion(self):
        print("\n[PRUEBA] Verificando sincronización entre servidores...")
        
        # Verificar que existan los archivos
        archivos_existentes = []
        for archivo in self.archivos_recursos:
            if os.path.exists(archivo):
                archivos_existentes.append(archivo)
                print(f"✓ Archivo encontrado: {archivo}")
            else:
                print(f"✗ Archivo no encontrado: {archivo}")
        
        if len(archivos_existentes) < 2:
            print("⚠ No hay suficientes archivos para comparar sincronización")
            return
        
        # Comparar contenidos
        contenidos = {}
        for archivo in archivos_existentes:
            try:
                with open(archivo, 'r') as f:
                    contenidos[archivo] = json.load(f)
            except Exception as e:
                print(f"✗ Error leyendo {archivo}: {e}")
        
        # Verificar si están sincronizados
        if len(set(str(sorted(cont.items())) for cont in contenidos.values())) == 1:
            print("✓ Todos los archivos están sincronizados")
        else:
            print("✗ Los archivos NO están sincronizados:")
            for archivo, contenido in contenidos.items():
                print(f"  {archivo}: {contenido}")
    
    def ver_estado_recursos(self):
        print("\n[ESTADO] Archivos de recursos:")
        print("-" * 50)
        
        for archivo in self.archivos_recursos:
            if os.path.exists(archivo):
                try:
                    with open(archivo, 'r') as f:
                        contenido = json.load(f)
                    
                    print(f"\n📁 {archivo}:")
                    print(f"   Salones disponibles: {contenido.get('salones_disponibles', 'N/A')}")
                    print(f"   Laboratorios disponibles: {contenido.get('laboratorios_disponibles', 'N/A')}")
                    
                    # Información adicional del archivo
                    stat = os.stat(archivo)
                    fecha_mod = datetime.fromtimestamp(stat.st_mtime)
                    print(f"   Última modificación: {fecha_mod.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                except Exception as e:
                    print(f"✗ Error leyendo {archivo}: {e}")
            else:
                print(f"\n📁 {archivo}: No existe")

    def comparar_archivos_recursos(self):
        print("\n[COMPARACIÓN] Diferencias entre archivos de recursos:")
        print("-" * 60)
        
        archivos_data = {}
        for archivo in self.archivos_recursos:
            if os.path.exists(archivo):
                try:
                    with open(archivo, 'r') as f:
                        archivos_data[archivo] = json.load(f)
                except Exception as e:
                    print(f"Error leyendo {archivo}: {e}")
        
        if len(archivos_data) < 2:
            print("No hay suficientes archivos para comparar")
            return
        
        archivos_nombres = list(archivos_data.keys())
        for i in range(len(archivos_nombres)):
            for j in range(i+1, len(archivos_nombres)):
                archivo1 = archivos_nombres[i]
                archivo2 = archivos_nombres[j]
                data1 = archivos_data[archivo1]
                data2 = archivos_data[archivo2]
                
                print(f"\n🔄 Comparando {archivo1} vs {archivo2}:")
                
                if data1 == data2:
                    print("   ✓ Idénticos")
                else:
                    print("   ✗ Diferentes:")
                    for key in set(data1.keys()) | set(data2.keys()):
                        val1 = data1.get(key, "NO EXISTE")
                        val2 = data2.get(key, "NO EXISTE")
                        if val1 != val2:
                            print(f"     {key}: {val1} vs {val2}")
    
    def stress_test_concurrente(self):
        print("\n[STRESS TEST] Prueba de solicitudes concurrentes...")
        
        num_hilos = int(input("Número de hilos concurrentes (default 5): ") or "5")
        solicitudes_por_hilo = int(input("Solicitudes por hilo (default 10): ") or "10")
        puerto = input("Puerto del servidor (6000=DTI, 5999=Backup, default 6000): ") or "6000"
        
        def enviar_solicitudes_hilo(hilo_id):
            socket = None
            try:
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 15000)
                socket.connect(f"tcp://localhost:{puerto}")
                
                for i in range(solicitudes_por_hilo):
                    solicitud = {
                        "facultad": f"Facultad Stress {hilo_id}",
                        "programa": f"Programa Stress {hilo_id}-{i}",
                        "salones": random.randint(1, 15),
                        "laboratorios": random.randint(1, 8)
                    }
                    
                    inicio = time.time()
                    socket.send_json(solicitud)
                    respuesta = socket.recv_json()
                    fin = time.time()
                    
                    print(f"Hilo-{hilo_id} Sol-{i}: {respuesta['estado']} ({fin-inicio:.4f}s)")
                
            except Exception as e:
                print(f"Error en hilo {hilo_id}: {e}")
            finally:
                if socket:
                    socket.close()
        
        print(f"Iniciando {num_hilos} hilos con {solicitudes_por_hilo} solicitudes cada uno...")
        
        hilos = []
        inicio_total = time.time()
        
        for i in range(num_hilos):
            hilo = threading.Thread(target=enviar_solicitudes_hilo, args=(i,))
            hilos.append(hilo)
            hilo.start()
        
        for hilo in hilos:
            hilo.join()
        
        fin_total = time.time()
        print(f"\n--- STRESS TEST COMPLETADO ---")
        print(f"Tiempo total: {fin_total - inicio_total:.4f} segundos")
        print(f"Total solicitudes: {num_hilos * solicitudes_por_hilo}")
    
    def limpiar_reinicializar_recursos(self):
        print("\n[LIMPIEZA] Reinicializando archivos de recursos...")
        
        recursos_iniciales = {
            "salones_disponibles": 380,
            "laboratorios_disponibles": 60
        }
        
        for archivo in self.archivos_recursos:
            try:
                with open(archivo, 'w') as f:
                    json.dump(recursos_iniciales, f, indent=4)
                print(f"✓ {archivo} reinicializado")
            except Exception as e:
                print(f"✗ Error reinicializando {archivo}: {e}")
        
        print("✓ Limpieza completada")
    
    def generar_reporte_rendimiento(self):
        print("\n[REPORTE] Generando reporte de rendimiento...")
        
        # Probar ambos servidores
        servidores = [
            {"nombre": "DTI Principal", "puerto": 6000},
            {"nombre": "DTI Backup", "puerto": 5999}
        ]
        
        reporte = f"""
REPORTE DE RENDIMIENTO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

"""
        
        for servidor in servidores:
            print(f"Probando {servidor['nombre']}...")
            
            socket = None
            try:
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 5000)
                socket.connect(f"tcp://localhost:{servidor['puerto']}")
                
                tiempos = []
                exitosas = 0
                
                for i in range(10):
                    solicitud = {
                        "facultad": "Facultad Reporte",
                        "programa": f"Programa Reporte {i}",
                        "salones": random.randint(1, 5),
                        "laboratorios": random.randint(1, 3)
                    }
                    
                    inicio = time.time()
                    socket.send_json(solicitud)
                    respuesta = socket.recv_json()
                    fin = time.time()
                    
                    tiempos.append(fin - inicio)
                    if respuesta.get("estado") == "Aceptado":
                        exitosas += 1
                
                reporte += f"""
{servidor['nombre']} (Puerto {servidor['puerto']}):
    ✓ Disponible
    ⏱ Tiempo promedio: {sum(tiempos)/len(tiempos):.4f}s
    ⏱ Tiempo mínimo: {min(tiempos):.4f}s  
    ⏱ Tiempo máximo: {max(tiempos):.4f}s
    📊 Solicitudes exitosas: {exitosas}/10
    📊 Tasa de éxito: {exitosas*10}%

"""
                                
            except Exception as e:
                reporte += f"""
{servidor['nombre']} (Puerto {servidor['puerto']}):
    ✗ No disponible - {e}

"""
            finally:
                if socket:
                    socket.close()
        
        # Agregar estado de recursos
        reporte += "\nESTADO DE RECURSOS:\n"
        reporte += "-" * 30 + "\n"
        
        for archivo in self.archivos_recursos:
            if os.path.exists(archivo):
                try:
                    with open(archivo, 'r') as f:
                        contenido = json.load(f)
                    reporte += f"{archivo}: Salones={contenido.get('salones_disponibles', 'N/A')}, Labs={contenido.get('laboratorios_disponibles', 'N/A')}\n"
                except:
                    reporte += f"{archivo}: Error al leer\n"
            else:
                reporte += f"{archivo}: No existe\n"
        
        # Guardar reporte
        nombre_reporte = f"reporte_rendimiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(nombre_reporte, 'w') as f:
            f.write(reporte)
        
        print(reporte)
        print(f"✓ Reporte guardado en: {nombre_reporte}")


    def ejecutar(self):
        try:
            while True:
                self.mostrar_menu()
                
                try:
                    opcion = input("\nSeleccione una opción: ").strip()
                    
                    if opcion == "0":
                        print("👋 Saliendo del sistema de pruebas...")
                        break
                    elif opcion == "1":
                        self.probar_conexion_dti()
                    elif opcion == "2":
                        self.probar_conexion_backup()
                    elif opcion == "3":
                        num = int(input("Número de solicitudes (default 10): ") or "10")
                        self.envio_masivo_solicitudes(6000, "DTI Principal", num)
                    elif opcion == "4":
                        num = int(input("Número de solicitudes (default 10): ") or "10")
                        self.envio_masivo_solicitudes(5999, "DTI Backup", num)
                    elif opcion == "5":
                        print("⚠ Para simular falla del DTI, deten manualmente el proceso DTI.py")
                        print("sudo fuser -k 6000/tcp")
                        print("  Luego pruebe las conexiones para verificar el comportamiento del backup")
                    elif opcion == "6":
                        self.verificar_sincronizacion()
                    elif opcion == "7":
                        self.ver_estado_recursos()
                    elif opcion == "8":
                        self.comparar_archivos_recursos()
                    elif opcion == "9":
                        self.monitoreo_tiempo_real()
                    elif opcion == "10":
                        self.stress_test_concurrente()
                    elif opcion == "11":
                        self.comparacion_rendimiento_servidores()
                    elif opcion == "12":
                        self.limpiar_reinicializar_recursos()
                    elif opcion == "13":
                        self.generar_reporte_rendimiento()
                    elif opcion == "14":
                        self.grafica_utilizacion_recursos()
                    else:
                        print("❌ Opción no válida")
                    
                    if opcion != "0":
                        input("\nPresione Enter para continuar...")
                    
                except ValueError:
                    print("❌ Por favor ingrese un número válido")
                    input("\nPresione Enter para continuar...")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    input("\nPresione Enter para continuar...")
                    
        except KeyboardInterrupt:
            print("\n👋 Saliendo por interrupción del usuario...")
        finally:
            print("Cerrando conexiones...")
            self.context.term()
            print("✓ Sistema de pruebas cerrado correctamente")

if __name__ == "__main__":
    pruebador = Pruebador()
    pruebador.ejecutar()