import zmq
import json
import time


class Facultad:
    def __init__(self, nombre, puerto):
        self.nombre = nombre
        self.puerto = puerto
        self.context = zmq.Context()

        # Sockets
        self.socket_rep = self.context.socket(zmq.REP)
        self.socket_req = self.context.socket(zmq.REQ)
        self.socket_sub = self.context.socket(zmq.SUB)

        self.configurar_conexiones()
        self.notificar_conexion()

    def configurar_conexiones(self):
        self.socket_rep.bind(f"tcp://*:{self.puerto}")
        self.socket_req.connect("tcp://localhost:7001")  # Conexión al Broker
        self.socket_sub.connect("tcp://10.43.103.206:6001")
        self.socket_sub.setsockopt_string(zmq.SUBSCRIBE, self.nombre)

        print(f"[{self.nombre}] Facultad activa en puerto {self.puerto}.")

    def notificar_conexion(self):
        mensaje = {"tipo": "conexion", "facultad": self.nombre}
        self.socket_req.send_json(mensaje)
        respuesta = self.socket_req.recv_json()
        print(f"[{self.nombre}] Conexión al DTI: {respuesta}")

    def escuchar_solicitudes(self):
        print(f"[{self.nombre}] Esperando solicitudes académicas...")
        try:
            while True:
                solicitud = self.socket_rep.recv_json()
                print(f"[{self.nombre}] Solicitud recibida del programa: {solicitud}")

                # Enviar solicitud al DTI y medir el tiempo de respuesta
                inicio = time.time()  # Inicia el cronómetro
                self.socket_req.send_json(solicitud)
                respuesta = self.socket_req.recv_json()
                fin = time.time()  # Finaliza el cronómetro

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