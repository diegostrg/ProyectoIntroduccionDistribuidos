import zmq
import json
import time
import getpass
from AutenticacionFacultad import AutenticacionFacultad

class Facultad:
    def __init__(self, nombre, puerto):
        self.nombre = nombre
        self.puerto = puerto
        self.context = zmq.Context()
        self.password_facultad = None
        
        # Sistema de autenticación para programas
        self.auth = AutenticacionFacultad(nombre)

        # Sockets
        self.socket_rep = self.context.socket(zmq.REP)
        self.socket_req = self.context.socket(zmq.REQ)
        self.socket_sub = self.context.socket(zmq.SUB)

        self._solicitar_password_facultad()
        self.configurar_conexiones()
        self.notificar_conexion()

    def _solicitar_password_facultad(self):
        """Solicita la contraseña de la facultad al administrador"""
        print(f"\n[{self.nombre}] Sistema de autenticación")
        print("=" * 50)
        print("Para conectar al DTI, ingrese la contraseña de la facultad:")
        print("Contraseñas por defecto (formato: nombreXXXX2024):")
        print("Ejemplo: ingenieria2024, medicina2024, etc.")
        print("=" * 50)
        
        while True:
            self.password_facultad = getpass.getpass(f"Contraseña para {self.nombre}: ")
            if self.password_facultad:
                break
            print("❌ La contraseña no puede estar vacía")

    def configurar_conexiones(self):
        self.socket_rep.bind(f"tcp://*:{self.puerto}")
        self.socket_req.connect("tcp://localhost:7001")  # Conexión al Broker
        self.socket_sub.connect("tcp://10.43.103.206:6001")
        self.socket_sub.setsockopt_string(zmq.SUBSCRIBE, self.nombre)

        print(f"[{self.nombre}] Facultad activa en puerto {self.puerto}.")

    def notificar_conexion(self):
        """Notifica la conexión al DTI con autenticación"""
        mensaje = {
            "tipo": "conexion", 
            "facultad": self.nombre,
            "password": self.password_facultad
        }
        
        try:
            self.socket_req.send_json(mensaje)
            respuesta = self.socket_req.recv_json()
            
            if respuesta.get("estado") == "Conexión aceptada":
                print(f"[{self.nombre}] ✓ Autenticada exitosamente en el DTI")
                self.auth.mostrar_credenciales_iniciales()
            else:
                print(f"[{self.nombre}] ✗ Error de autenticación: {respuesta.get('mensaje', 'Error desconocido')}")
                print("Verifique la contraseña e intente nuevamente")
                exit(1)
                
        except Exception as e:
            print(f"[{self.nombre}] ✗ Error conectando al DTI: {e}")
            exit(1)

    def escuchar_solicitudes(self):
        print(f"[{self.nombre}] Esperando solicitudes académicas...")
        try:
            while True:
                solicitud = self.socket_rep.recv_json()
                print(f"[{self.nombre}] Solicitud recibida del programa: {solicitud}")

                # Verificar autenticación del programa
                usuario = solicitud.get("usuario")
                password_programa = solicitud.get("password_programa")
                
                if not usuario or not password_programa:
                    respuesta_error = {
                        "estado": "Error de autenticación",
                        "mensaje": "Usuario y contraseña requeridos"
                    }
                    self.socket_rep.send_json(respuesta_error)
                    print(f"[{self.nombre}] ✗ Solicitud rechazada: Faltan credenciales")
                    continue
                
                if not self.auth.verificar_programa(usuario, password_programa):
                    respuesta_error = {
                        "estado": "Acceso denegado",
                        "mensaje": "Credenciales inválidas"
                    }
                    self.socket_rep.send_json(respuesta_error)
                    print(f"[{self.nombre}] ✗ Solicitud rechazada: Credenciales inválidas para {usuario}")
                    continue

                print(f"[{self.nombre}] ✓ Programa autenticado: {usuario}")

                # Agregar credenciales de la facultad a la solicitud
                solicitud_dti = solicitud.copy()
                solicitud_dti["password_facultad"] = self.password_facultad
                
                # Enviar solicitud al DTI y medir el tiempo de respuesta
                inicio = time.time()
                self.socket_req.send_json(solicitud_dti)
                respuesta = self.socket_req.recv_json()
                fin = time.time()

                print(f"[{self.nombre}] Respuesta recibida del DTI: {respuesta}")
                print(f"[{self.nombre}] Tiempo de respuesta del DTI: {fin - inicio:.4f} segundos")

                self.socket_rep.send_json(respuesta)
                print(f"[{self.nombre}] Respuesta enviada al programa académico.\n")

        except KeyboardInterrupt:
            print(f"[{self.nombre}] Cerrando facultad...")
        finally:
            self.cerrar()

    def cerrar(self):
        self.socket_rep.close()
        self.socket_req.close()
        self.socket_sub.close()
        self.context.term()

# Esta función va fuera de la clase
def seleccionar_facultad():
    facultades = {
        "Facultad de Ciencias Sociales": 5550,
        "Facultad de Ciencias Naturales": 5551,
        "Facultad de Ingeniería": 5552,
        "Facultad de Medicina": 5553,
        "Facultad de Derecho": 5554,
        "Facultad de Artes": 5555,
        "Facultad de Educación": 5556,
        "Facultad de Ciencias Económicas": 5557,
        "Facultad de Arquitectura": 5558,
        "Facultad de Tecnología": 5559
    }
    print("Seleccione la facultad:")
    nombres = list(facultades.keys())
    for i, f in enumerate(nombres, start=1):
        print(f"{i}. {f}")

    while True:
        try:
            opcion = int(input("Número de la facultad: "))
            if 1 <= opcion <= 10:
                return nombres[opcion - 1], facultades[nombres[opcion - 1]]
            else:
                print("Opción inválida.")
        except ValueError:
            print("Ingrese un número válido.")

if __name__ == "__main__":
    nombre, puerto = seleccionar_facultad()
    facultad = Facultad(nombre, puerto)
    facultad.escuchar_solicitudes()