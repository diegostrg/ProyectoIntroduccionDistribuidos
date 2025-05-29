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
import csv
from datetime import datetime
import os


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

        self.puerto_ip_map = {
            6000: "10.43.103.206",  # DTI Principal
            5999: "10.43.102.243",   # DTI Backup
            7001: "10.43.96.34",   # Broker
            6001: "10.43.96.34"    # Broker puerto alternativo
        }

        # Credenciales de autenticación para las pruebas
        self.credenciales_facultades = {
            "Facultad de Ciencias Sociales": "sociales2024",
            "Facultad de Ciencias Naturales": "naturales2024",
            "Facultad de Ingeniería": "ingenieria2024",
            "Facultad de Medicina": "medicina2024",
            "Facultad de Artes": "artes2024",
            "Facultad de Educación": "educacion2024",
            "Facultad de Ciencias Económicas": "economicas2024",
            "Facultad de Arquitectura": "arquitectura2024",
            "Facultad de Tecnología": "tecnologia2024"
        }
        
        # Facultad por defecto para pruebas
        self.facultad_prueba = "Facultad de Ingeniería"
        self.password_facultad = self.credenciales_facultades[self.facultad_prueba]


    def _get_ip_for_port(self, puerto):
        """Obtiene la IP correcta según el puerto"""
        return self.puerto_ip_map.get(puerto, "localhost")
        
    def _crear_solicitud_autenticada(self, facultad=None, programa=None, salones=1, laboratorios=1):
        """Crea una solicitud con autenticación válida"""
        if facultad is None:
            facultad = self.facultad_prueba
        
        # Obtener contraseña para la facultad
        password = self.credenciales_facultades.get(facultad, None)
        
        # VERIFICACIÓN ADICIONAL
        if password is None:
            print(f"❌ ERROR: No se encontraron credenciales para {facultad}")
            print(f"📋 Facultades disponibles: {list(self.credenciales_facultades.keys())}")
            # Usar facultad por defecto como fallback
            facultad = self.facultad_prueba
            password = self.password_facultad
            print(f"🔄 Usando facultad por defecto: {facultad}")
        
        return {
            "facultad": facultad,
            "programa": programa or f"Programa de {facultad}",
            "salones": salones,
            "laboratorios": laboratorios,
            "password_facultad": password
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
        print("15. Prueba de failover controlado")
        print("16. Prueba de rendimiento con logs (broker)")
        print("17. Prueba autenticación de facultades")
        print("18. Prueba seguridad completa")
        print("19. Información archivos de autenticación")
        print("20. Escenario 1: 5 Facultades - Prueba intensiva (7-2 aulas/labs)")
        print("21. Escenario 2: 5 Facultades - Prueba máxima (10-4 aulas/labs)")
        print("0.  Salir")
        print("="*60)
        
    # metodo para el escenario de la prueba 1

    def escenario_1_prueba_intensiva(self):
        """Escenario 1: 5 facultades, 5 programas c/u, mínimo 7 aulas y 2 labs (o máximo 2 y 7) - CONCURRENTE"""
        print("\n[ESCENARIO 1] Prueba Intensiva: 5 Facultades x 5 Programas - CONCURRENTE")
        print("Configuración: Mínimo 7 aulas y 2 laboratorios (o máximo 2 aulas y 7 laboratorios)")
        print("="*80)
        
        # Seleccionar 5 facultades
        # Seleccionar 5 facultades
        facultades_seleccionadas = list(self.credenciales_facultades.keys())[:5]

        # VERIFICACIÓN DE CREDENCIALES
        print(f"\n🔍 Facultades seleccionadas para la prueba:")
        for i, facultad in enumerate(facultades_seleccionadas, 1):
            password = self.credenciales_facultades.get(facultad, "NO_ENCONTRADA")
            print(f"   {i}. {facultad} -> {password}")

        # Verificar que todas las facultades tengan credenciales
        facultades_validas = []
        for facultad in facultades_seleccionadas:
            if facultad in self.credenciales_facultades:
                facultades_validas.append(facultad)
            else:
                print(f"❌ ADVERTENCIA: {facultad} no tiene credenciales válidas")

        if len(facultades_validas) < 5:
            print(f"⚠️  Solo {len(facultades_validas)} facultades tienen credenciales válidas")
            facultades_seleccionadas = facultades_validas

        num_programas_por_facultad = 5
        num_solicitudes_por_programa = int(input("Solicitudes por programa (default 3): ") or "3")
        
        # Estructuras para recopilar datos (thread-safe)
        import threading
        lock = threading.Lock()
        resultados_por_facultad = {}
        resultados_por_programa = {}
        tiempos_respuesta_globales = []
        tiempos_atencion_globales = []
        
        # Inicializar estructuras
        for facultad in facultades_seleccionadas:
            resultados_por_facultad[facultad] = {
                'tiempos_respuesta': [],
                'exitosas': 0,
                'rechazadas': 0,
                'errores': 0
            }
            
            for programa_num in range(1, num_programas_por_facultad + 1):
                programa_nombre = f"Programa {programa_num} de {facultad.split()[-1]}"
                programa_key = f"{facultad}_{programa_nombre}"
                
                resultados_por_programa[programa_key] = {
                    'tiempos_respuesta': [],
                    'tiempos_atencion': [],
                    'exitosas': 0,
                    'rechazadas': 0,
                    'errores': 0,
                    'solicitudes_total': num_solicitudes_por_programa
                }
        
        def procesar_solicitud(facultad, programa_nombre, programa_key, solicitud_num):
            """Función para procesar una solicitud individual en paralelo"""
            # Configuración del escenario 1: mínimo 7 aulas y 2 labs O máximo 2 aulas y 7 labs
            if random.choice([True, False]):
                # Opción A: Muchas aulas, pocos laboratorios
                salones = random.randint(7, 15)
                laboratorios = random.randint(2, 4)
            else:
                # Opción B: Pocas aulas, muchos laboratorios
                salones = random.randint(1, 2)
                laboratorios = random.randint(7, 12)
            
            solicitud = self._crear_solicitud_autenticada(
                facultad=facultad,
                programa=programa_nombre,
                salones=salones,
                laboratorios=laboratorios
            )
            
            # Medir tiempo de atención (desde solicitud hasta respuesta)
            inicio_atencion = time.time()
            respuesta, tiempo_respuesta = self._usar_broker_para_solicitud(solicitud)
            fin_atencion = time.time()
            
            tiempo_atencion = fin_atencion - inicio_atencion
            
            # Actualizar resultados de forma thread-safe
            with lock:
                if tiempo_respuesta:
                    # Datos por facultad
                    resultados_por_facultad[facultad]['tiempos_respuesta'].append(tiempo_respuesta * 1000)
                    
                    # Datos por programa
                    resultados_por_programa[programa_key]['tiempos_respuesta'].append(tiempo_respuesta * 1000)
                    resultados_por_programa[programa_key]['tiempos_atencion'].append(tiempo_atencion * 1000)
                    
                    # Datos globales
                    tiempos_respuesta_globales.append(tiempo_respuesta * 1000)
                    tiempos_atencion_globales.append(tiempo_atencion * 1000)
                    
                    estado = respuesta.get("estado", "Error")
                    servidor = respuesta.get("servidor", "Desconocido")
                    
                    if estado == "Aceptado":
                        resultados_por_facultad[facultad]['exitosas'] += 1
                        resultados_por_programa[programa_key]['exitosas'] += 1
                        status_symbol = "✅"
                    elif estado == "Rechazado":
                        resultados_por_facultad[facultad]['rechazadas'] += 1
                        resultados_por_programa[programa_key]['rechazadas'] += 1
                        status_symbol = "❌"
                    else:
                        resultados_por_facultad[facultad]['errores'] += 1
                        resultados_por_programa[programa_key]['errores'] += 1
                        status_symbol = "⚠️"
                    
                    print(f"    {status_symbol} {facultad.split()[-1]} - {programa_nombre} - Sol {solicitud_num+1}: {estado} ({tiempo_respuesta*1000:.1f}ms) - S:{salones} L:{laboratorios} - {servidor}")
                else:
                    resultados_por_facultad[facultad]['errores'] += 1
                    resultados_por_programa[programa_key]['errores'] += 1
                    print(f"    ⚠️  {facultad.split()[-1]} - {programa_nombre} - Sol {solicitud_num+1}: Error - S:{salones} L:{laboratorios}")
        
        print(f"\n🚀 Iniciando {len(facultades_seleccionadas) * num_programas_por_facultad * num_solicitudes_por_programa} solicitudes CONCURRENTES...")
        
        inicio_escenario = time.time()
        
        # Crear todos los hilos para TODAS las solicitudes al mismo tiempo
        hilos = []
        
        for facultad in facultades_seleccionadas:
            print(f"🏛️  Preparando {facultad}...")
            
            for programa_num in range(1, num_programas_por_facultad + 1):
                programa_nombre = f"Programa {programa_num} de {facultad.split()[-1]}"
                programa_key = f"{facultad}_{programa_nombre}"
                
                print(f"  📚 Preparando {programa_nombre}...")
                
                for solicitud_num in range(num_solicitudes_por_programa):
                    # Crear hilo para cada solicitud
                    hilo = threading.Thread(
                        target=procesar_solicitud,
                        args=(facultad, programa_nombre, programa_key, solicitud_num)
                    )
                    hilos.append(hilo)
        
        print(f"\n⚡ LANZANDO TODAS LAS {len(hilos)} SOLICITUDES SIMULTÁNEAMENTE...")
        
        # Iniciar TODOS los hilos al mismo tiempo
        for hilo in hilos:
            hilo.start()
        
        # Esperar a que terminen TODOS los hilos
        for hilo in hilos:
            hilo.join()
        
        fin_escenario = time.time()
        
        print(f"\n✅ Todas las solicitudes completadas en {fin_escenario - inicio_escenario:.2f} segundos")
        
        # Generar reporte detallado
        self._generar_reporte_escenario(
            "ESCENARIO 1 - PRUEBA INTENSIVA (CONCURRENTE)",
            resultados_por_facultad,
            resultados_por_programa,
            tiempos_respuesta_globales,
            tiempos_atencion_globales,
            inicio_escenario,
            fin_escenario,
            "escenario_1_concurrente"
        )

    def escenario_2_prueba_maxima(self):
        """Escenario 2: 5 facultades, 5 programas c/u, máximo 10 aulas y 4 labs (o máximo 4 y 10) - CONCURRENTE"""
        print("\n[ESCENARIO 2] Prueba Máxima: 5 Facultades x 5 Programas - CONCURRENTE")
        print("Configuración: Máximo 10 aulas y 4 laboratorios (o máximo 4 aulas y 10 laboratorios)")
        print("="*80)
        
        # Seleccionar 5 facultades
        facultades_seleccionadas = list(self.credenciales_facultades.keys())[:5]
        num_programas_por_facultad = 5
        num_solicitudes_por_programa = int(input("Solicitudes por programa (default 3): ") or "3")
        
        # Estructuras para recopilar datos (thread-safe)
        import threading
        lock = threading.Lock()
        resultados_por_facultad = {}
        resultados_por_programa = {}
        tiempos_respuesta_globales = []
        tiempos_atencion_globales = []
        
        # Inicializar estructuras
        for facultad in facultades_seleccionadas:
            resultados_por_facultad[facultad] = {
                'tiempos_respuesta': [],
                'exitosas': 0,
                'rechazadas': 0,
                'errores': 0
            }
            
            for programa_num in range(1, num_programas_por_facultad + 1):
                programa_nombre = f"Programa {programa_num} de {facultad.split()[-1]}"
                programa_key = f"{facultad}_{programa_nombre}"
                
                resultados_por_programa[programa_key] = {
                    'tiempos_respuesta': [],
                    'tiempos_atencion': [],
                    'exitosas': 0,
                    'rechazadas': 0,
                    'errores': 0,
                    'solicitudes_total': num_solicitudes_por_programa
                }
        
        def procesar_solicitud(facultad, programa_nombre, programa_key, solicitud_num):
            """Función para procesar una solicitud individual en paralelo"""
            # Configuración del escenario 2: máximo 10 aulas y 4 labs O máximo 4 aulas y 10 labs
            if random.choice([True, False]):
                # Opción A: Muchas aulas, pocos laboratorios
                salones = random.randint(5, 10)
                laboratorios = random.randint(1, 4)
            else:
                # Opción B: Pocas aulas, muchos laboratorios
                salones = random.randint(1, 4)
                laboratorios = random.randint(5, 10)
            
            solicitud = self._crear_solicitud_autenticada(
                facultad=facultad,
                programa=programa_nombre,
                salones=salones,
                laboratorios=laboratorios
            )
            
            # Medir tiempo de atención (desde solicitud hasta respuesta)
            inicio_atencion = time.time()
            respuesta, tiempo_respuesta = self._usar_broker_para_solicitud(solicitud)
            fin_atencion = time.time()
            
            tiempo_atencion = fin_atencion - inicio_atencion
            
            # Actualizar resultados de forma thread-safe
            with lock:
                if tiempo_respuesta:
                    # Datos por facultad
                    resultados_por_facultad[facultad]['tiempos_respuesta'].append(tiempo_respuesta * 1000)
                    
                    # Datos por programa
                    resultados_por_programa[programa_key]['tiempos_respuesta'].append(tiempo_respuesta * 1000)
                    resultados_por_programa[programa_key]['tiempos_atencion'].append(tiempo_atencion * 1000)
                    
                    # Datos globales
                    tiempos_respuesta_globales.append(tiempo_respuesta * 1000)
                    tiempos_atencion_globales.append(tiempo_atencion * 1000)
                    
                    estado = respuesta.get("estado", "Error")
                    servidor = respuesta.get("servidor", "Desconocido")
                    
                    if estado == "Aceptado":
                        resultados_por_facultad[facultad]['exitosas'] += 1
                        resultados_por_programa[programa_key]['exitosas'] += 1
                        status_symbol = "✅"
                    elif estado == "Rechazado":
                        resultados_por_facultad[facultad]['rechazadas'] += 1
                        resultados_por_programa[programa_key]['rechazadas'] += 1
                        status_symbol = "❌"
                    else:
                        resultados_por_facultad[facultad]['errores'] += 1
                        resultados_por_programa[programa_key]['errores'] += 1
                        status_symbol = "⚠️"
                    
                    print(f"    {status_symbol} {facultad.split()[-1]} - {programa_nombre} - Sol {solicitud_num+1}: {estado} ({tiempo_respuesta*1000:.1f}ms) - S:{salones} L:{laboratorios} - {servidor}")
                else:
                    resultados_por_facultad[facultad]['errores'] += 1
                    resultados_por_programa[programa_key]['errores'] += 1
                    print(f"    ⚠️  {facultad.split()[-1]} - {programa_nombre} - Sol {solicitud_num+1}: Error - S:{salones} L:{laboratorios}")
        
        print(f"\n🚀 Iniciando {len(facultades_seleccionadas) * num_programas_por_facultad * num_solicitudes_por_programa} solicitudes CONCURRENTES...")
        
        inicio_escenario = time.time()
        
        # Crear todos los hilos para TODAS las solicitudes al mismo tiempo
        hilos = []
        
        for facultad in facultades_seleccionadas:
            print(f"🏛️  Preparando {facultad}...")
            
            for programa_num in range(1, num_programas_por_facultad + 1):
                programa_nombre = f"Programa {programa_num} de {facultad.split()[-1]}"
                programa_key = f"{facultad}_{programa_nombre}"
                
                print(f"  📚 Preparando {programa_nombre}...")
                
                for solicitud_num in range(num_solicitudes_por_programa):
                    # Crear hilo para cada solicitud
                    hilo = threading.Thread(
                        target=procesar_solicitud,
                        args=(facultad, programa_nombre, programa_key, solicitud_num)
                    )
                    hilos.append(hilo)
        
        print(f"\n⚡ LANZANDO TODAS LAS {len(hilos)} SOLICITUDES SIMULTÁNEAMENTE...")
        
        # Iniciar TODOS los hilos al mismo tiempo
        for hilo in hilos:
            hilo.start()
        
        # Esperar a que terminen TODOS los hilos
        for hilo in hilos:
            hilo.join()
        
        fin_escenario = time.time()
        
        print(f"\n✅ Todas las solicitudes completadas en {fin_escenario - inicio_escenario:.2f} segundos")
        
        # Generar reporte detallado
        self._generar_reporte_escenario(
            "ESCENARIO 2 - PRUEBA MÁXIMA (CONCURRENTE)",
            resultados_por_facultad,
            resultados_por_programa,
            tiempos_respuesta_globales,
            tiempos_atencion_globales,
            inicio_escenario,
            fin_escenario,
            "escenario_2_concurrente"
        )

    def _usar_broker_para_solicitud(self, solicitud):
        """Helper para enviar solicitudes a través del broker - Thread Safe"""
        socket = None
        try:
            # Crear nuevo contexto ZMQ para cada hilo (thread-safe)
            context_local = zmq.Context()
            socket = context_local.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 15000)  # Timeout más alto para concurrencia
            ip = self._get_ip_for_port(7001)  # Puerto del broker
            socket.connect(f"tcp://{ip}:7001")
            
            inicio = time.time()
            socket.send_json(solicitud)
            respuesta = socket.recv_json()
            fin = time.time()
            
            return respuesta, fin - inicio
            
        except Exception as e:
            return {"estado": "Error", "mensaje": str(e)}, None
        finally:
            if socket:
                socket.close()
            try:
                context_local.term()
            except:
                pass
        

    def _generar_reporte_escenario(self, titulo, resultados_facultad, resultados_programa, 
                                 tiempos_respuesta, tiempos_atencion, inicio, fin, prefijo_archivo):
        """Genera reporte detallado para los escenarios"""
        
        duracion_total = fin - inicio
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Calcular estadísticas globales
        if tiempos_respuesta:
            tiempo_resp_promedio = np.mean(tiempos_respuesta)
            tiempo_resp_min = np.min(tiempos_respuesta)
            tiempo_resp_max = np.max(tiempos_respuesta)
        else:
            tiempo_resp_promedio = tiempo_resp_min = tiempo_resp_max = 0
        
        if tiempos_atencion:
            tiempo_aten_promedio = np.mean(tiempos_atencion)
            tiempo_aten_min = np.min(tiempos_atencion)
            tiempo_aten_max = np.max(tiempos_atencion)
        else:
            tiempo_aten_promedio = tiempo_aten_min = tiempo_aten_max = 0
        
        # Crear reporte de texto
        reporte = f"""
    {titulo}
    {'='*80}
    Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Duración total del escenario: {duracion_total:.2f} segundos
    
    ESTADÍSTICAS GLOBALES:
    {'='*50}
    📊 Tiempo de respuesta (servidor a facultades):
       • Promedio: {tiempo_resp_promedio:.2f}ms
       • Mínimo: {tiempo_resp_min:.2f}ms
       • Máximo: {tiempo_resp_max:.2f}ms
    
    ⏱️  Tiempo de atención (programa a respuesta):
       • Promedio: {tiempo_aten_promedio:.2f}ms
       • Mínimo: {tiempo_aten_min:.2f}ms
       • Máximo: {tiempo_aten_max:.2f}ms
    
    RESULTADOS POR FACULTAD:
    {'='*50}
    """
        
        for facultad, datos in resultados_facultad.items():
            total_solicitudes = datos['exitosas'] + datos['rechazadas'] + datos['errores']
            tasa_exito = (datos['exitosas'] / total_solicitudes * 100) if total_solicitudes > 0 else 0
            
            if datos['tiempos_respuesta']:
                prom_facultad = np.mean(datos['tiempos_respuesta'])
            else:
                prom_facultad = 0
            
            reporte += f"""
    🏛️  {facultad}:
       • Total solicitudes: {total_solicitudes}
       • Exitosas: {datos['exitosas']} ({tasa_exito:.1f}%)
       • Rechazadas: {datos['rechazadas']}
       • Errores: {datos['errores']}
       • Tiempo promedio respuesta: {prom_facultad:.2f}ms
    """
        
        reporte += f"""
    
    RESULTADOS POR PROGRAMA:
    {'='*50}
    """
        
        for programa_key, datos in resultados_programa.items():
            # CORRECCIÓN: Parsing mejorado para el formato real
            try:
                # El formato es: "Facultad de Ciencias Sociales_Programa 1 de Sociales"
                if '_' in programa_key:
                    partes = programa_key.split('_', 1)  # Dividir solo en la primera _
                    facultad_display = partes[0]  # "Facultad de Ciencias Sociales"
                    programa_display = partes[1]  # "Programa 1 de Sociales"
                else:
                    # Fallback si no hay _
                    facultad_display = "Facultad Desconocida"
                    programa_display = programa_key
                    
            except Exception as e:
                print(f"Error procesando clave de programa: {programa_key} - {e}")
                facultad_display = "Facultad Desconocida"
                programa_display = programa_key
            
            tasa_exito = (datos['exitosas'] / datos['solicitudes_total'] * 100) if datos['solicitudes_total'] > 0 else 0
            
            if datos['tiempos_respuesta']:
                prom_resp = np.mean(datos['tiempos_respuesta'])
            else:
                prom_resp = 0
                
            if datos['tiempos_atencion']:
                prom_aten = np.mean(datos['tiempos_atencion'])
            else:
                prom_aten = 0
            
            reporte += f"""
    📚 {programa_display} ({facultad_display}):
       • Solicitudes atendidas satisfactoriamente: {datos['exitosas']}/{datos['solicitudes_total']} ({tasa_exito:.1f}%)
       • Tiempo promedio respuesta: {prom_resp:.2f}ms
       • Tiempo promedio atención: {prom_aten:.2f}ms
       • Rechazadas: {datos['rechazadas']} | Errores: {datos['errores']}
    """
        
        # Guardar reporte
        nombre_reporte = f"{prefijo_archivo}_{timestamp}.txt"
        with open(nombre_reporte, 'w', encoding='utf-8') as f:
            f.write(reporte)
        
        # Crear gráficas
        self._crear_graficas_escenario(resultados_facultad, resultados_programa, 
                                     tiempos_respuesta, tiempos_atencion, 
                                     titulo, f"{prefijo_archivo}_{timestamp}")
        
        print(reporte)
        print(f"\n✓ Reporte guardado en: {nombre_reporte}")

    def _crear_graficas_escenario(self, resultados_facultad, resultados_programa, 
                                tiempos_respuesta, tiempos_atencion, titulo, filename_base):
        """Crea gráficas para los escenarios"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(titulo, fontsize=16)
        
        # Gráfica 1: Tiempos de respuesta por facultad
        facultades = list(resultados_facultad.keys())
        tiempos_facultad = []
        
        for facultad in facultades:
            if resultados_facultad[facultad]['tiempos_respuesta']:
                tiempos_facultad.append(np.mean(resultados_facultad[facultad]['tiempos_respuesta']))
            else:
                tiempos_facultad.append(0)
        
        ax1.bar(range(len(facultades)), tiempos_facultad, color='skyblue', alpha=0.7)
        ax1.set_title('Tiempo de Respuesta Promedio por Facultad')
        ax1.set_ylabel('Tiempo (ms)')
        ax1.set_xticks(range(len(facultades)))
        ax1.set_xticklabels([f.split()[-1] for f in facultades], rotation=45)
        ax1.grid(True, alpha=0.3)
        
        # Gráfica 2: Tasa de éxito por facultad
        tasas_exito = []
        for facultad in facultades:
            datos = resultados_facultad[facultad]
            total = datos['exitosas'] + datos['rechazadas'] + datos['errores']
            tasa = (datos['exitosas'] / total * 100) if total > 0 else 0
            tasas_exito.append(tasa)
        
        ax2.bar(range(len(facultades)), tasas_exito, color='lightgreen', alpha=0.7)
        ax2.set_title('Tasa de Éxito por Facultad')
        ax2.set_ylabel('Porcentaje (%)')
        ax2.set_xticks(range(len(facultades)))
        ax2.set_xticklabels([f.split()[-1] for f in facultades], rotation=45)
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        
        # Gráfica 3: Distribución de tiempos de respuesta
        if tiempos_respuesta:
            ax3.hist(tiempos_respuesta, bins=20, alpha=0.7, color='orange', edgecolor='black')
            ax3.set_title('Distribución de Tiempos de Respuesta')
            ax3.set_xlabel('Tiempo (ms)')
            ax3.set_ylabel('Frecuencia')
            ax3.grid(True, alpha=0.3)
        
        # Gráfica 4: Comparación tiempos respuesta vs atención
        if tiempos_respuesta and tiempos_atencion:
            ax4.scatter(tiempos_respuesta, tiempos_atencion, alpha=0.6, color='purple')
            ax4.set_title('Tiempo Respuesta vs Tiempo Atención')
            ax4.set_xlabel('Tiempo Respuesta (ms)')
            ax4.set_ylabel('Tiempo Atención (ms)')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar gráfica
        plt.savefig(f"{filename_base}.png", dpi=300, bbox_inches='tight')
        print(f"✓ Gráficas guardadas en: {filename_base}.png")
        
        plt.show()
        


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
            ip = self._get_ip_for_port(puerto)
            socket.connect(f"tcp://{ip}:{puerto}")
            

            # Por esta:
            solicitud = self._crear_solicitud_autenticada(
                facultad=self.facultad_prueba,
                programa="Programa Test Failover",
                salones=random.randint(1, 5),
                laboratorios=random.randint(0, 2)
            )
            
            inicio = time.time()
            socket.send_json(solicitud)
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
        """Compara el rendimiento del sistema vía BROKER con gráficas"""
        print("\n[COMPARACIÓN] Analizando rendimiento del sistema vía BROKER...")
        
        num_pruebas = int(input("Número de pruebas (default 20): ") or "20")
        
        print(f"Probando sistema vía BROKER con {num_pruebas} solicitudes...")
        
        # Datos para recopilar
        tiempos = []
        estados = []
        servidores_usados = []
        timestamps = []
        exitosas = 0
        rechazadas = 0
        errores = 0
        
        # Contador de servidores
        conteo_servidores = {}
        
        for i in range(num_pruebas):
            solicitud = self._crear_solicitud_autenticada(
                facultad=list(self.credenciales_facultades.keys())[i % len(self.credenciales_facultades)],
                programa=f"Programa Test {i}",
                salones=random.randint(1, 5),
                laboratorios=random.randint(1, 3)
            )
            
            respuesta, tiempo_respuesta = self._usar_broker_para_solicitud(solicitud)
            
            if tiempo_respuesta:
                tiempo_respuesta_ms = tiempo_respuesta * 1000  # Convertir a ms
                tiempos.append(tiempo_respuesta_ms)
                
                estado = respuesta.get("estado", "Error")
                estados.append(estado)
                
                servidor_usado = respuesta.get("servidor", "Desconocido").lower()
                servidores_usados.append(servidor_usado)
                
                # Contar servidores
                conteo_servidores[servidor_usado] = conteo_servidores.get(servidor_usado, 0) + 1
                
                timestamps.append(datetime.now())
                
                if estado == "Aceptado":
                    exitosas += 1
                elif estado == "Rechazado":
                    rechazadas += 1
                
                print(f"  Prueba {i+1}/{num_pruebas}: {tiempo_respuesta_ms:.2f}ms - {estado} (Servidor: {servidor_usado})")
            else:
                errores += 1
                tiempos.append(0)  # Para mantener la secuencia
                estados.append("Error")
                servidores_usados.append("Error")
                timestamps.append(datetime.now())
                print(f"  Prueba {i+1}/{num_pruebas}: Error - {respuesta.get('mensaje', 'Desconocido')}")
        
        # Mostrar estadísticas
        if tiempos:
            tiempos_validos = [t for t in tiempos if t > 0]
            if tiempos_validos:
                print(f"\n--- ESTADÍSTICAS BROKER ---")
                print(f"Pruebas exitosas: {exitosas}/{num_pruebas}")
                print(f"Pruebas rechazadas: {rechazadas}/{num_pruebas}")
                print(f"Errores: {errores}/{num_pruebas}")
                print(f"Tiempo promedio: {sum(tiempos_validos)/len(tiempos_validos):.2f}ms")
                print(f"Tiempo mínimo: {min(tiempos_validos):.2f}ms")
                print(f"Tiempo máximo: {max(tiempos_validos):.2f}ms")
                print(f"Distribución de servidores: {conteo_servidores}")
        
        # Crear gráficas
        self._crear_graficas_broker_comparacion(
            tiempos, estados, servidores_usados, timestamps, 
            num_pruebas, exitosas, rechazadas, errores, conteo_servidores
        )
    
    def _crear_graficas_broker_comparacion(self, tiempos, estados, servidores_usados, timestamps, 
                                         num_pruebas, exitosas, rechazadas, errores, conteo_servidores):
        """Crea gráficas comparativas del rendimiento vía BROKER enfocadas en tiempos por servidor"""
        
        # Filtrar tiempos válidos para gráficas
        tiempos_validos = [t for t in tiempos if t > 0]
        
        if not tiempos_validos:
            print("❌ No hay datos válidos para generar gráficas")
            return
        
        # Separar datos por servidor
        datos_por_servidor = {}
        for i, servidor in enumerate(servidores_usados):
            if servidor not in datos_por_servidor:
                datos_por_servidor[servidor] = []
            if tiempos[i] > 0:  # Solo tiempos válidos
                datos_por_servidor[servidor].append(tiempos[i])
        
        # Colores por servidor
        colores_servidor = {
            'dti': '#2E86AB',           # Azul DTI
            'backup': '#C73E1D',        # Rojo/Rosa Backup
            'DTI': '#2E86AB',           # Azul DTI (por si acaso)
            'Backup': '#C73E1D',        # Rojo/Rosa Backup (por si acaso)
            'Error': '#F18F01',         # Naranja Error
            'Desconocido': '#FFFFFF'    # Rojo Error
        }
        
        # Crear figura con subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Análisis Comparativo de Tiempos de Respuesta por Servidor', fontsize=16)
        
        # Gráfica 1: Histograma comparativo por servidor
        ax1.clear()
        for servidor, tiempos_srv in datos_por_servidor.items():
            if servidor != 'Error' and tiempos_srv:
                ax1.hist(tiempos_srv, bins=min(10, len(tiempos_srv)), 
                        alpha=0.7, label=f'Servidor {servidor.upper()}', 
                        color=colores_servidor.get(servidor, '#808080'),
                        edgecolor='black', linewidth=0.5)
        
        ax1.set_title('Distribución de Tiempos por Servidor')
        ax1.set_xlabel('Tiempo de Respuesta (ms)')
        ax1.set_ylabel('Frecuencia')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Gráfica 2: Box Plot comparativo por servidor
        ax2.clear()
        if len(datos_por_servidor) > 0:
            box_data = []
            box_labels = []
            box_colors = []
            
            for servidor, tiempos_srv in datos_por_servidor.items():
                if servidor != 'Error' and tiempos_srv:
                    box_data.append(tiempos_srv)
                    box_labels.append(f'{servidor.upper()}\n({len(tiempos_srv)} req)')
                    box_colors.append(colores_servidor.get(servidor, '#808080'))
            
            if box_data:
                bp = ax2.boxplot(box_data, labels=box_labels, patch_artist=True)
                
                # Colorear las cajas
                for patch, color in zip(bp['boxes'], box_colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                
                # Añadir estadísticas como texto
                for i, (servidor, tiempos_srv) in enumerate([(k, v) for k, v in datos_por_servidor.items() if k != 'Error' and v]):
                    promedio = np.mean(tiempos_srv)
                    ax2.text(i+1, max(tiempos_srv) * 1.05, f'μ={promedio:.1f}ms', 
                            ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax2.set_title('Comparación de Distribución de Tiempos')
        ax2.set_ylabel('Tiempo de Respuesta (ms)')
        ax2.grid(True, alpha=0.3)
        
        # Gráfica 3: Evolución temporal separada por servidor
        ax3.clear()
        if len(timestamps) == len(tiempos):
            indices = range(len(tiempos))
            
            for servidor in set(servidores_usados):
                if servidor != 'Error':
                    indices_servidor = [i for i, s in enumerate(servidores_usados) if s == servidor]
                    tiempos_servidor = [tiempos[i] for i in indices_servidor]
                    
                    if tiempos_servidor:
                        # Línea conectando puntos del mismo servidor
                        ax3.plot(indices_servidor, tiempos_servidor, 
                                color=colores_servidor.get(servidor, 'purple'),
                                marker='o', markersize=6, linewidth=2, alpha=0.8,
                                label=f'Servidor {servidor.upper()}')
            
            # Línea de tendencia general
            indices_validos = [i for i, t in enumerate(tiempos) if t > 0]
            tiempos_validos_orden = [tiempos[i] for i in indices_validos]
            
            if len(indices_validos) > 1:
                z = np.polyfit(indices_validos, tiempos_validos_orden, 1)
                p = np.poly1d(z)
                tendencia_color = 'green' if z[0] <= 0 else 'red'  # Verde si mejora, rojo si empeora
                ax3.plot(indices_validos, p(indices_validos), "--", alpha=0.8, 
                        color=tendencia_color, linewidth=2,
                        label=f'Tendencia: {z[0]:.2f}ms/req')
        
        ax3.set_title('Evolución Temporal por Servidor')
        ax3.set_xlabel('Número de Solicitud')
        ax3.set_ylabel('Tiempo de Respuesta (ms)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Gráfica 4: Comparación de estadísticas por servidor
        ax4.clear()
        if datos_por_servidor:
            servidores_validos = {k: v for k, v in datos_por_servidor.items() if k != 'Error' and v}
            
            if servidores_validos:
                estadisticas = ['Promedio', 'Mediana', 'Mínimo', 'Máximo', 'Desv. Std']
                x = np.arange(len(estadisticas))
                width = 0.35
                
                servidores_lista = list(servidores_validos.keys())
                
                for i, servidor in enumerate(servidores_lista):
                    tiempos_srv = servidores_validos[servidor]
                    valores = [
                        np.mean(tiempos_srv),      # Promedio
                        np.median(tiempos_srv),    # Mediana
                        np.min(tiempos_srv),       # Mínimo
                        np.max(tiempos_srv),       # Máximo
                        np.std(tiempos_srv)        # Desviación estándar
                    ]
                    
                    offset = (i - len(servidores_lista)/2 + 0.5) * width
                    bars = ax4.bar(x + offset, valores, width, 
                                  label=f'Servidor {servidor.upper()}',
                                  color=colores_servidor.get(servidor, '#808080'),
                                  alpha=0.8)
                    
                    # Añadir valores encima de las barras
                    for bar, valor in zip(bars, valores):
                        height = bar.get_height()
                        ax4.text(bar.get_x() + bar.get_width()/2., height + max(valores)*0.01,
                                f'{valor:.1f}', ha='center', va='bottom', fontsize=9)
                
                ax4.set_title('Estadísticas Comparativas por Servidor')
                ax4.set_ylabel('Tiempo (ms)')
                ax4.set_xticks(x)
                ax4.set_xticklabels(estadisticas)
                ax4.legend()
                ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar gráfica
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analisis_tiempos_servidores_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"\n✓ Gráficas guardadas en: {filename}")
        
        # Crear reporte de texto mejorado
        reporte = f"""
    ANÁLISIS COMPARATIVO DE TIEMPOS - SISTEMA BROKER
    {'='*60}
    Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Número de pruebas: {num_pruebas}
    
    RESUMEN GENERAL:
    - Solicitudes exitosas: {exitosas} ({exitosas/num_pruebas*100:.1f}%)
    - Solicitudes rechazadas: {rechazadas} ({rechazadas/num_pruebas*100:.1f}%)
    - Errores de conexión: {errores} ({errores/num_pruebas*100:.1f}%)
    
    ANÁLISIS POR SERVIDOR:
    {'='*40}
    """
        
        for servidor, tiempos_srv in datos_por_servidor.items():
            if servidor != 'Error' and tiempos_srv:
                reporte += f"""
    SERVIDOR {servidor.upper()}:
    - Solicitudes procesadas: {len(tiempos_srv)}
    - Tiempo promedio: {np.mean(tiempos_srv):.2f}ms
    - Tiempo mediana: {np.median(tiempos_srv):.2f}ms
    - Tiempo mínimo: {np.min(tiempos_srv):.2f}ms
    - Tiempo máximo: {np.max(tiempos_srv):.2f}ms
    - Desviación estándar: {np.std(tiempos_srv):.2f}ms
    - Percentil 95: {np.percentile(tiempos_srv, 95):.2f}ms
    """
        
        # Comparación directa si hay 2 servidores
        servidores_validos = {k: v for k, v in datos_por_servidor.items() if k != 'Error' and v}
        if len(servidores_validos) == 2:
            servidores_lista = list(servidores_validos.keys())
            srv1, srv2 = servidores_lista[0], servidores_lista[1]
            tiempos1, tiempos2 = servidores_validos[srv1], servidores_validos[srv2]
            
            diferencia_promedio = np.mean(tiempos1) - np.mean(tiempos2)
            servidor_mas_rapido = srv1 if diferencia_promedio < 0 else srv2
            
            reporte += f"""
    COMPARACIÓN DIRECTA:
    {'='*20}
    - Servidor más rápido: {servidor_mas_rapido.upper()}
    - Diferencia promedio: {abs(diferencia_promedio):.2f}ms
    - Diferencia porcentual: {abs(diferencia_promedio)/min(np.mean(tiempos1), np.mean(tiempos2))*100:.1f}%
    """
        
        # Guardar reporte
        nombre_reporte = f"analisis_tiempos_servidores_{timestamp}.txt"
        with open(nombre_reporte, 'w') as f:
            f.write(reporte)
        
        print(f"✓ Reporte guardado en: {nombre_reporte}")
        plt.show()
    





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
        """Genera gráfica de utilización de recursos vía BROKER"""
        print("\n[UTILIZACIÓN] Generando gráfica de utilización de recursos vía BROKER...")
        
        num_solicitudes = int(input("Número de solicitudes para simular (default 15): ") or "15")
        
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
            
            # Enviar solicitud vía broker
            solicitud = self._crear_solicitud_autenticada(
                facultad=self.facultad_prueba,
                programa=f"Programa Util {i}",
                salones=random.randint(1, 10),
                laboratorios=random.randint(1, 5)
            )
            
            respuesta, tiempo_respuesta = self._usar_broker_para_solicitud(solicitud)
            servidor_usado = respuesta.get("servidor", "Desconocido")
            print(f"Solicitud {i+1}: {respuesta.get('estado', 'Error')} (Servidor: {servidor_usado})")
            
            time.sleep(0.5)  # Pausa entre solicitudes
        
        # Crear gráfica de utilización (mismo código que antes)
        if historial_recursos:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            fig.suptitle('Utilización de Recursos vía BROKER', fontsize=16)
            
            salones = [r['salones'] for r in historial_recursos]
            laboratorios = [r['laboratorios'] for r in historial_recursos]
            tiempos = [t.strftime('%H:%M:%S') for t in timestamps]
            
            # Gráfica de líneas
            ax1.plot(tiempos, salones, 'b-o', label='Salones Disponibles', linewidth=2)
            ax1.plot(tiempos, laboratorios, 'r-o', label='Laboratorios Disponibles', linewidth=2)
            ax1.set_title('Recursos Disponibles vs Tiempo (vía BROKER)')
            ax1.set_ylabel('Cantidad')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
            
            # Gráfica de área apilada
            ax2.fill_between(range(len(salones)), salones, alpha=0.5, color='blue', label='Salones')
            ax2.fill_between(range(len(laboratorios)), laboratorios, alpha=0.5, color='red', label='Laboratorios')
            ax2.set_title('Área de Utilización (vía BROKER)')
            ax2.set_xlabel('Número de Solicitud')
            ax2.set_ylabel('Cantidad')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Guardar gráfica
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"utilizacion_recursos_broker_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"\n✓ Gráfica guardada en: {filename}")
            
            plt.show()

    def probar_conexion_dti(self):
        print("\n[PRUEBA] Probando conexión al DTI Principal...")
        socket = None
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # Timeout 5 segundos
            ip = self._get_ip_for_port(6000)
            socket.connect(f"tcp://{ip}:6000")
            
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
            ip = self._get_ip_for_port(5999)
            socket.connect(f"tcp://{ip}:5999")
            
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
        print(f"\n[PRUEBA] Enviando {num_solicitudes} solicitudes masivas a través del BROKER...")
        
        tiempos_respuesta = []
        solicitudes_exitosas = 0
        solicitudes_rechazadas = 0
        
        for i in range(num_solicitudes):
            facultades_disponibles = list(self.credenciales_facultades.keys())
            facultad = facultades_disponibles[i % len(facultades_disponibles)]
    
            solicitud = self._crear_solicitud_autenticada(
                facultad=facultad,
                programa=f"Programa Test {i+1}",
                salones=random.randint(1, 20),
                laboratorios=random.randint(1, 10)
            )
            
            respuesta, tiempo_respuesta = self._usar_broker_para_solicitud(solicitud)
            
            if tiempo_respuesta:
                tiempos_respuesta.append(tiempo_respuesta)
            
            if respuesta.get("estado") == "Aceptado":
                solicitudes_exitosas += 1
            else:
                solicitudes_rechazadas += 1
                
            print(f"  Solicitud {i+1}: {respuesta.get('estado', 'Error')} - {tiempo_respuesta:.4f}s" if tiempo_respuesta else f"  Solicitud {i+1}: Error")
        
        if tiempos_respuesta:
            print(f"\n--- RESUMEN vía BROKER ---")
            print(f"Solicitudes exitosas: {solicitudes_exitosas}")
            print(f"Solicitudes rechazadas: {solicitudes_rechazadas}")
            print(f"Tiempo promedio: {sum(tiempos_respuesta)/len(tiempos_respuesta):.4f}s")
            print(f"Tiempo mínimo: {min(tiempos_respuesta):.4f}s")
            print(f"Tiempo máximo: {max(tiempos_respuesta):.4f}s")

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
        print("\n[STRESS TEST] Prueba de solicitudes concurrentes vía BROKER...")
        
        num_hilos = int(input("Número de hilos concurrentes (default 5): ") or "5")
        solicitudes_por_hilo = int(input("Solicitudes por hilo (default 10): ") or "10")
        
        def enviar_solicitudes_hilo(hilo_id):
            facultades_disponibles = list(self.credenciales_facultades.keys())
            facultad = facultades_disponibles[hilo_id % len(facultades_disponibles)]
    
            for i in range(solicitudes_por_hilo):
                solicitud = self._crear_solicitud_autenticada(
                    facultad=facultad,
                    programa=f"Programa Stress {hilo_id}-{i}",
                    salones=random.randint(1, 15),
                    laboratorios=random.randint(1, 8)
                )
                
                respuesta, tiempo_respuesta = self._usar_broker_para_solicitud(solicitud)
                tiempo_str = f"({tiempo_respuesta:.4f}s)" if tiempo_respuesta else "(error)"
                print(f"Hilo-{hilo_id} Sol-{i}: {respuesta.get('estado', 'Error')} {tiempo_str}")
        
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
        print(f"\n--- STRESS TEST COMPLETADO (vía BROKER) ---")
        print(f"Tiempo total: {fin_total - inicio_total:.4f} segundos")
        print(f"Total solicitudes: {num_hilos * solicitudes_por_hilo}")
    
    def generar_reporte_rendimiento(self):
        print("\n[REPORTE] Generando reporte de rendimiento vía BROKER...")
        
        num_solicitudes = int(input("Número de solicitudes (default 10): ") or "10")
        
        reporte = f"""
    REPORTE DE RENDIMIENTO VÍA BROKER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    {'='*70}
    Número de solicitudes: {num_solicitudes}
    
    """
        
        print(f"Probando sistema vía BROKER con {num_solicitudes} solicitudes...")
        
        tiempos = []
        exitosas = 0
        rechazadas = 0
        errores = 0
        servidores_usados = {}
        
        for i in range(num_solicitudes):
            facultades_disponibles = list(self.credenciales_facultades.keys())
            facultad = facultades_disponibles[i % len(facultades_disponibles)]
            
            solicitud = self._crear_solicitud_autenticada(
                facultad=facultad,
                programa=f"Programa Reporte {i}",
                salones=random.randint(1, 5),
                laboratorios=random.randint(1, 3)
            )
            
            respuesta, tiempo_respuesta = self._usar_broker_para_solicitud(solicitud)
            
            if tiempo_respuesta:
                tiempos.append(tiempo_respuesta)
                
                if respuesta.get("estado") == "Aceptado":
                    exitosas += 1
                elif respuesta.get("estado") == "Rechazado":
                    rechazadas += 1
                
                # Contar servidores usados
                servidor = respuesta.get("servidor", "Desconocido")
                servidores_usados[servidor] = servidores_usados.get(servidor, 0) + 1
                
                print(f"  Solicitud {i+1}/{num_solicitudes}: {respuesta.get('estado', 'Sin estado')} - {tiempo_respuesta:.4f}s (Servidor: {servidor})")
            else:
                errores += 1
                print(f"  Solicitud {i+1}/{num_solicitudes}: Error - {respuesta.get('mensaje', 'Desconocido')}")
        
        # Calcular estadísticas
        if tiempos:
            tiempo_promedio = sum(tiempos) / len(tiempos)
            tiempo_min = min(tiempos)
            tiempo_max = max(tiempos)
            tasa_exito = (exitosas / num_solicitudes) * 100
            tasa_rechazo = (rechazadas / num_solicitudes) * 100
            tasa_error = (errores / num_solicitudes) * 100
            
            reporte += f"""
    SISTEMA VÍA BROKER:
        ✓ Disponible
        📊 Estadísticas de {num_solicitudes} solicitudes:
            ✅ Exitosas: {exitosas} ({tasa_exito:.1f}%)
            ❌ Rechazadas: {rechazadas} ({tasa_rechazo:.1f}%)
            ⚠️  Errores: {errores} ({tasa_error:.1f}%)
        ⏱ Tiempos de respuesta:
            📈 Promedio: {tiempo_promedio:.4f}s ({tiempo_promedio*1000:.2f}ms)
            ⚡ Mínimo: {tiempo_min:.4f}s ({tiempo_min*1000:.2f}ms)
            🐌 Máximo: {tiempo_max:.4f}s ({tiempo_max*1000:.2f}ms)
        
        🔄 Distribución de servidores:
    """
            for servidor, count in servidores_usados.items():
                porcentaje = (count / sum(servidores_usados.values())) * 100
                reporte += f"        {servidor}: {count} solicitudes ({porcentaje:.1f}%)\n"
            
        else:
            reporte += f"""
    SISTEMA VÍA BROKER:
        ❌ No se pudo completar ninguna solicitud
        ⚠️  Errores en todas las {num_solicitudes} solicitudes
    """
        
        # Guardar reporte
        nombre_reporte = f"reporte_rendimiento_broker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(nombre_reporte, 'w') as f:
            f.write(reporte)
        
        print(reporte)
        print(f"✓ Reporte guardado en: {nombre_reporte}")

    def _usar_broker_para_solicitud(self, solicitud):
        """Helper para enviar solicitudes a través del broker"""
        socket = None
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 10000)  # Timeout más alto para broker
            ip = self._get_ip_for_port(7001)  # Puerto del broker
            socket.connect(f"tcp://{ip}:7001")
            
            inicio = time.time()
            socket.send_json(solicitud)
            respuesta = socket.recv_json()
            fin = time.time()
            
            return respuesta, fin - inicio
            
        except Exception as e:
            return {"estado": "Error", "mensaje": str(e)}, None
        finally:
            if socket:
                socket.close()


# bbbbbbb

    def _medir_tiempo_respuesta(self, puerto, servidor_nombre):
        """Helper method to measure response time from a specific server"""
        socket = None
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            ip = self._get_ip_for_port(puerto)
            socket.connect(f"tcp://{ip}:{puerto}")
            
            solicitud = {
                "facultad": "Facultad de Prueba Failover",
                "programa": "Programa Test Failover",
                "salones": random.randint(1, 5),
                "laboratorios": random.randint(0, 2)
            }
            
            inicio = time.time()
            socket.send_json(solicitud)
            respuesta = socket.recv_json()
            fin = time.time()
            
            return fin - inicio
            
        except Exception as e:
            print(f"❌ Error conectando a {servidor_nombre}: {e}")
            return None
        finally:
            if socket:
                socket.close()

    def prueba_failover_controlado(self):
        print("\n[FAILOVER] Prueba de failover controlado")

        print("🔴 Paso 1: Asegurese de tener corriendo DTI, DTIBackup, Broker y HealthCheck")
        input("➡ Presione Enter cuando este listo para continuar...")

        print("🛑 Paso 2: Detenga manualmente el DTI (puerto 6000) con Ctrl+C")
        input("➡ Presione Enter cuando el DTI esté apagado...")

        print("⏳ Esperando 3 segundos para que healthcheck detecte la falla...")
        time.sleep(3)

        print("📤 Enviando solicitud al puerto 5999 (backup)...")
        resultado = self._medir_tiempo_respuesta(5999, "Backup")
        if resultado:
            print(f"✅ Backup respondió en {resultado*1000:.2f}ms")
        else:
            print("❌ El backup no respondió")

        print("✅ Paso 3: Reinicia el DTI y espera unos segundos...")
        input("➡ Presiona Enter cuando el DTI esté encendido nuevamente...")

        print("⏳ Esperando 3 segundos para verificar que aún no se use el DTI...")
        time.sleep(3)

        print("📤 Enviando otra solicitud al backup...")
        resultado2 = self._medir_tiempo_respuesta(5999, "Backup")
        if resultado2:
            print(f"✅ Aún se usa el backup (correcto): {resultado2*1000:.2f}ms")
        else:
            print("❌ El backup falló inesperadamente")

        print("🛑 Paso 4: Detén el backup para que el sistema vuelva al DTI")
        input("➡ Presiona Enter cuando el backup esté detenido...")

        print("⏳ Esperando 3 segundos para que el broker se redirija al DTI...")
        time.sleep(3)

        print("📤 Enviando solicitud al DTI (6000)...")
        resultado3 = self._medir_tiempo_respuesta(6000, "DTI Principal")
        if resultado3:
            print(f"✅ DTI respondió nuevamente: {resultado3*1000:.2f}ms")
        else:
            print("❌ El DTI no respondió correctamente")

        print("\n📊 Verificando estado de JSONs:")
        self.comparar_archivos_recursos()

    def prueba_log_rendimiento(self):
        print("\n[Prueba 16] Recolectando datos de rendimiento desde broker...")
        n = input("¿Cuántas solicitudes desea enviar?: ")
        try:
            n = int(n)
        except ValueError:
            print("❌ Número inválido.")
            return

        puerto_broker = 7001  # Cambiar de 6001 a 7001
        resultados = []

        for i in range(n):
            print(f"\nSolicitud {i+1}/{n}...")
            salones = random.randint(1, 10)
            laboratorios = random.randint(0, 3)

            solicitud = self._crear_solicitud_autenticada(
                facultad=self.facultad_prueba,
                programa="Programa de Ingeniería de Sistemas",
                salones=salones,
                laboratorios=laboratorios
            )

            try:
                socket = self.context.socket(zmq.REQ)
                ip = self._get_ip_for_port(puerto_broker)
                socket.connect(f"tcp://{ip}:{puerto_broker}")

                inicio = time.time()
                socket.send_json(solicitud)
                respuesta = socket.recv_json()
                fin = time.time()
                socket.close()

                duracion_ms = (fin - inicio) * 1000

                print(f"✅ Respuesta recibida en {duracion_ms:.2f} ms")

                resultados.append({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "salones": salones,
                    "laboratorios": laboratorios,
                    "estado": respuesta.get("estado"),
                    "tiempo_ms": f"{duracion_ms:.2f}",
                    "servidor": respuesta.get("servidor", "Desconocido")
                })

            except Exception as e:
                print(f"❌ Error: {e}")

        # Guardar CSV
        os.makedirs("logs", exist_ok=True)
        ruta = "logs/registro_solicitudes.csv"
        with open(ruta, "w", newline="") as csvfile:
            fieldnames = ["timestamp", "salones", "laboratorios", "estado", "tiempo_ms", "servidor"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(resultados)

        print(f"\n📁 Resultados guardados en '{ruta}'")

# Pruebas de autenticacion

    def prueba_autenticacion_facultades(self):
        """Prueba el sistema de autenticación de facultades"""
        print("\n[PRUEBA SEGURIDAD] Probando autenticación de facultades...")
        
        # Pruebas de autenticación
        pruebas = [
            {"facultad": "Facultad de Ingeniería", "password": "ingenieria2024", "esperado": True},
            {"facultad": "Facultad de Medicina", "password": "medicina2024", "esperado": True},
            {"facultad": "Facultad de Ingeniería", "password": "contraseña_incorrecta", "esperado": False},
            {"facultad": "Facultad Inexistente", "password": "cualquier2024", "esperado": False},
            {"facultad": "Facultad de Medicina", "password": "", "esperado": False},
        ]
        
        servidor = input("Servidor a probar (6000=DTI, 5999=Backup, default 6000): ") or "6000"
        puerto = int(servidor)
        
        for i, prueba in enumerate(pruebas):
            print(f"\nPrueba {i+1}: {prueba['facultad']}")
            
            socket = None
            try:
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 5000)
                ip = self._get_ip_for_port(puerto)
                socket.connect(f"tcp://{ip}:{puerto}")
                
                mensaje = {
                    "tipo": "conexion",
                    "facultad": prueba["facultad"],
                    "password": prueba["password"]
                }
                
                socket.send_json(mensaje)
                respuesta = socket.recv_json()
                
                # Verificar resultado
                exito = respuesta.get("estado") == "Conexión aceptada"
                
                if exito == prueba["esperado"]:
                    print(f"  ✅ ÉXITO: {respuesta}")
                else:
                    print(f"  ❌ FALLO: Esperado {prueba['esperado']}, obtuvo {exito}")
                    print(f"     Respuesta: {respuesta}")
                
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
            finally:
                if socket:
                    socket.close()

    def prueba_seguridad_completa(self):
        """Prueba completa del sistema de seguridad"""
        print("\n[PRUEBA SEGURIDAD COMPLETA] Verificando todo el flujo de autenticación...")
        
        # 1. Probar autenticación de facultad
        print("\n1. Probando autenticación de facultad...")
        socket_facultad = self.context.socket(zmq.REQ)
        socket_facultad.setsockopt(zmq.RCVTIMEO, 5000)
        ip = self._get_ip_for_port(6000)
        socket_facultad.connect(f"tcp://{ip}:6000")
        
        mensaje_conexion = {
            "tipo": "conexion",
            "facultad": "Facultad de Ingeniería",
            "password": "ingenieria2024"
        }
        
        socket_facultad.send_json(mensaje_conexion)
        respuesta_conexion = socket_facultad.recv_json()
        socket_facultad.close()
        
        if respuesta_conexion.get("estado") == "Conexión aceptada":
            print("  ✅ Facultad autenticada correctamente")
        else:
            print(f"  ❌ Fallo en autenticación de facultad: {respuesta_conexion}")
            return
        
        # 2. Probar solicitud con autenticación completa
        print("\n2. Probando solicitud con autenticación completa...")
        socket_solicitud = self.context.socket(zmq.REQ)
        socket_solicitud.setsockopt(zmq.RCVTIMEO, 5000)
        ip = self._get_ip_for_port(6000)
        socket_solicitud.connect(f"tcp://{ip}:6000")
        
        solicitud_recursos = {
            "facultad": "Facultad de Ingeniería",
            "programa": "Programa de Ingeniería de Sistemas",
            "salones": 5,
            "laboratorios": 2,
            "password_facultad": "ingenieria2024"
        }
        
        socket_solicitud.send_json(solicitud_recursos)
        respuesta_recursos = socket_solicitud.recv_json()
        socket_solicitud.close()
        
        if respuesta_recursos.get("estado") in ["Aceptado", "Rechazado"]:
            print(f"  ✅ Solicitud procesada: {respuesta_recursos}")
        else:
            print(f"  ❌ Error en solicitud: {respuesta_recursos}")
        
        # 3. Probar solicitud sin autenticación
        print("\n3. Probando solicitud sin autenticación (debe fallar)...")
        socket_no_auth = self.context.socket(zmq.REQ)
        socket_no_auth.setsockopt(zmq.RCVTIMEO, 5000)
        ip = self._get_ip_for_port(6000)
        socket_no_auth.connect(f"tcp://{ip}:6000")
        
        solicitud_sin_auth = {
            "facultad": "Facultad de Ingeniería",
            "programa": "Programa de Ingeniería de Sistemas",
            "salones": 3,
            "laboratorios": 1
            # Sin password_facultad
        }
        
        socket_no_auth.send_json(solicitud_sin_auth)
        respuesta_sin_auth = socket_no_auth.recv_json()
        socket_no_auth.close()
        
        if respuesta_sin_auth.get("estado") == "Acceso denegado":
            print("  ✅ Solicitud sin autenticación rechazada correctamente")
        else:
            print(f"  ❌ Error: Solicitud sin autenticación debería ser rechazada: {respuesta_sin_auth}")

    def mostrar_info_archivos_autenticacion(self):
        """Muestra información sobre los archivos de autenticación"""
        print("\n[INFO SEGURIDAD] Archivos de autenticación en el sistema:")
        print("=" * 60)
        
        # Buscar archivos de autenticación
        archivos_auth = []
        
        # Archivo DTI
        if os.path.exists("autenticacion_DTI.json"):
            archivos_auth.append("autenticacion_DTI.json")
        
        # Archivos de facultades
        for archivo in os.listdir("."):
            if archivo.startswith("autenticacion_Facultad_") and archivo.endswith(".json"):
                archivos_auth.append(archivo)
        
        for archivo in archivos_auth:
            try:
                with open(archivo, 'r') as f:
                    data = json.load(f)
                
                print(f"\n📁 {archivo}:")
                print(f"   Versión: {data.get('version', 'N/A')}")
                print(f"   Encriptación: {data.get('encriptacion', 'N/A')}")
                print(f"   Iteraciones: {data.get('iteraciones', 'N/A'):,}")
                
                if 'credenciales' in data:
                    credenciales = data['credenciales']
                    print(f"   Usuarios/Facultades: {len(credenciales)}")
                    
                    # Mostrar algunos ejemplos (sin mostrar hashes completos)
                    for i, cred in enumerate(list(credenciales.keys())[:3]):
                        hash_preview = data['credenciales'][cred][:20] + "..."
                        print(f"     {cred}: {hash_preview}")
                    
                    if len(credenciales) > 3:
                        print(f"     ... y {len(credenciales) - 3} más")
                
                # Información del archivo
                stat = os.stat(archivo)
                fecha_mod = datetime.fromtimestamp(stat.st_mtime)
                print(f"   Última modificación: {fecha_mod.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                print(f"❌ Error leyendo {archivo}: {e}")
        
        if not archivos_auth:
            print("⚠️  No se encontraron archivos de autenticación")
            print("   Ejecute DTI.py o facultad.py para crear los archivos")


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
                        num_solicitudes = int(input("Número de solicitudes (default 10): ") or "10")
                        self.envio_masivo_solicitudes(None, "BROKER", num_solicitudes)
                    elif opcion == "4":
                        num_solicitudes = int(input("Número de solicitudes (default 10): ") or "10")
                        self.envio_masivo_solicitudes(None, "BROKER", num_solicitudes)
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
                    elif opcion == "15":
                        self.prueba_failover_controlado()
                    elif opcion == "16":
                        self.prueba_log_rendimiento()
                    elif opcion == "17":
                        self.prueba_autenticacion_facultades()
                    elif opcion == "18":
                        self.prueba_seguridad_completa()
                    elif opcion == "19":
                        self.mostrar_info_archivos_autenticacion()
                    elif opcion == "20":
                        self.escenario_1_prueba_intensiva()
                    elif opcion == "21":
                        self.escenario_2_prueba_maxima()
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