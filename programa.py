import zmq
import json
import time
import random
import getpass

class ProgramaAcademico:
    def __init__(self):
        self.context = zmq.Context()
        self.facultades = {
            "Facultad de Ciencias Sociales": {
                "puerto": 5550,
                "programas": [
                    "Programa de Psicología", "Programa de Sociología", "Programa de Trabajo Social",
                    "Programa de Antropología", "Programa de Comunicación"
                ]
            },
            "Facultad de Ciencias Naturales": {
                "puerto": 5551,
                "programas": [
                    "Programa de Biología", "Programa de Química", "Programa de Física",
                    "Programa de Geología", "Programa de Ciencias Ambientales"
                ]
            },
            "Facultad de Ingeniería": {
                "puerto": 5552,
                "programas": [
                    "Programa de Ingeniería Civil", "Programa de Ingeniería Electrónica",
                    "Programa de Ingeniería de Sistemas", "Programa de Ingeniería Mecánica",
                    "Programa de Ingeniería Industrial"
                ]
            },
            "Facultad de Medicina": {
                "puerto": 5553,
                "programas": [
                    "Programa de Medicina General", "Programa de Enfermería", "Programa de Odontología",
                    "Programa de Farmacia", "Programa de Terapia Física"
                ]
            },
            "Facultad de Derecho": {
                "puerto": 5554,
                "programas": [
                    "Programa de Derecho Penal", "Programa de Derecho Civil", "Programa de Derecho Internacional",
                    "Programa de Derecho Laboral", "Programa de Derecho Constitucional"
                ]
            },
            "Facultad de Artes": {
                "puerto": 5555,
                "programas": [
                    "Programa de Bellas Artes", "Programa de Música", "Programa de Teatro",
                    "Programa de Danza", "Programa de Diseño Gráfico"
                ]
            },
            "Facultad de Educación": {
                "puerto": 5556,
                "programas": [
                    "Programa de Educación Primaria", "Programa de Educación Secundaria",
                    "Programa de Educación Especial", "Programa de Psicopedagogía",
                    "Programa de Administración Educativa"
                ]
            },
            "Facultad de Ciencias Económicas": {
                "puerto": 5557,
                "programas": [
                    "Programa de Administración de Empresas", "Programa de Contabilidad",
                    "Programa de Economía", "Programa de Mercadotecnia", "Programa de Finanzas"
                ]
            },
            "Facultad de Arquitectura": {
                "puerto": 5558,
                "programas": [
                    "Programa de Arquitectura", "Programa de Urbanismo",
                    "Programa de Diseño de Interiores", "Programa de Paisajismo",
                    "Programa de Restauración de Patrimonio"
                ]
            },
            "Facultad de Tecnología": {
                "puerto": 5559,
                "programas": [
                    "Programa de Desarrollo de Software", "Programa de Redes y Telecomunicaciones",
                    "Programa de Ciberseguridad", "Programa de Inteligencia Artificial", "Programa de Big Data"
                ]
            }
        }
        self.socket = None
        self.facultad = ""
        self.programa = ""
        self.puerto = 0
        self.usuario = ""
        self.password_programa = ""

    def autenticar_usuario(self):
        """Solicita credenciales de autenticación al usuario"""
        print("\n" + "="*50)
        print("SISTEMA DE AUTENTICACIÓN")
        print("="*50)
        
        while True:
            self.usuario = input("Usuario: ").strip()
            if self.usuario:
                break
            print("❌ El usuario no puede estar vacío")
        
        while True:
            self.password_programa = getpass.getpass("Contraseña: ")
            if self.password_programa:
                break
            print("❌ La contraseña no puede estar vacía")

    def seleccionar_facultad(self):
        print("\nSeleccione la facultad:")
        nombres = list(self.facultades.keys())
        for i, nombre in enumerate(nombres, 1):
            print(f"{i}. {nombre}")
        while True:
            try:
                opcion = int(input("Número de la facultad: "))
                if 1 <= opcion <= len(nombres):
                    self.facultad = nombres[opcion - 1]
                    self.puerto = self.facultades[self.facultad]["puerto"]
                    return self.facultades[self.facultad]["programas"]
                else:
                    print("Opción inválida.")
            except ValueError:
                print("Ingrese un número válido.")

    def seleccionar_programa(self, programas):
        print("\nSeleccione el programa académico:")
        for i, nombre in enumerate(programas, 1):
            print(f"{i}. {nombre}")
        while True:
            try:
                opcion = int(input("Número del programa: "))
                if 1 <= opcion <= len(programas):
                    self.programa = programas[opcion - 1]
                    return
                else:
                    print("Opción inválida.")
            except ValueError:
                print("Ingrese un número válido.")
    
    def solicitar_recursos(self):
        while True:
            try:
                salones_input = input("\nIngrese el número de salones necesarios: ")
                if salones_input.strip().lower() == "prueba":
                    for _ in range(20):
                        salones = random.randint(0, 30)
                        laboratorios = random.randint(0, 20)
                        print(f"Generando solicitud de prueba: Salones={salones}, Laboratorios={laboratorios}")
                        self.enviar_solicitud(salones, laboratorios)
                    print("Pruebas finalizadas.")
                    continue
                else:
                    salones = int(salones_input)
                    if salones >= 0:
                        break
                    else:
                        print("Debe ser un valor positivo.")
            except ValueError:
                print("Ingrese un número válido.")
    
        while True:
            try:
                laboratorios = int(input("Ingrese el número de laboratorios necesarios: "))
                if laboratorios >= 0:
                    break
                else:
                    print("Debe ser un valor positivo.")
            except ValueError:
                print("Ingrese un número válido.")
    
        return salones, laboratorios

    def enviar_solicitud(self, salones, laboratorios):
        solicitud = {
            "facultad": self.facultad,
            "programa": self.programa,
            "salones": salones,
            "laboratorios": laboratorios,
            "usuario": self.usuario,
            "password_programa": self.password_programa
        }
        
        print(f"\n[{self.programa}] Enviando solicitud: {solicitud}")
        
        try:
            inicio = time.time()
            self.socket.send_json(solicitud)
            respuesta = self.socket.recv_json()
            fin = time.time()
            
            if respuesta.get("estado") in ["Error de autenticación", "Acceso denegado"]:
                print(f"[{self.programa}] ✗ {respuesta['estado']}: {respuesta.get('mensaje', '')}")
                print("Verifique sus credenciales")
            else:
                print(f"[{self.programa}] Respuesta recibida: {respuesta}")
                print(f"[{self.programa}] Tiempo de respuesta: {fin - inicio:.4f} segundos\n")
                
        except Exception as e:
            print(f"[{self.programa}] Error enviando solicitud: {e}")

    def ejecutar(self):
        self.autenticar_usuario()
        programas = self.seleccionar_facultad()
        self.seleccionar_programa(programas)

        print(f"\n[{self.programa}] Usuario: {self.usuario}")
        print(f"[{self.programa}] Enviando solicitudes a {self.facultad} en el puerto {self.puerto}...\n")

        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{self.puerto}")

        try:
            while True:
                salones, laboratorios = self.solicitar_recursos()
                self.enviar_solicitud(salones, laboratorios)

                continuar = input("¿Desea enviar otra solicitud? (s/n): ").strip().lower()
                if continuar != "s":
                    break
        except KeyboardInterrupt:
            print("\n[Programa] Finalizando.")
        finally:
            self.socket.close()
            self.context.term()

if __name__ == "__main__":
    cliente = ProgramaAcademico()
    cliente.ejecutar()