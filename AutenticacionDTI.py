import json
import hashlib
import os
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class AutenticacionDTI:
    def __init__(self, archivo="autenticacion_DTI.json"):
        self.archivo = archivo
        self.salt_size = 32  # 256 bits
        self.iterations = 100000  # Número de iteraciones para PBKDF2
        self._inicializar_credenciales()
    
    def _generar_salt(self):
        """Genera un salt aleatorio para cada contraseña"""
        return secrets.token_bytes(self.salt_size)
    
    def _generar_clave_encriptacion(self, password, salt):
        """Genera una clave de encriptación usando PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _encriptar_password(self, password):
        """Encripta una contraseña con salt y múltiples iteraciones"""
        # Generar salt único para esta contraseña
        salt = self._generar_salt()
        
        # Crear hash con PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        password_hash = kdf.derive(password.encode())
        
        # Combinar salt + hash para almacenamiento
        combined = salt + password_hash
        
        # Codificar en base64 para almacenamiento JSON
        return base64.b64encode(combined).decode('utf-8')
    
    def _verificar_password(self, password, hash_almacenado):
        """Verifica una contraseña contra el hash almacenado"""
        try:
            # Decodificar desde base64
            combined = base64.b64decode(hash_almacenado.encode('utf-8'))
            
            # Extraer salt (primeros 32 bytes) y hash (resto)
            salt = combined[:self.salt_size]
            hash_original = combined[self.salt_size:]
            
            # Recrear el hash con la contraseña proporcionada
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.iterations,
            )
            hash_nuevo = kdf.derive(password.encode())
            
            # Comparar los hashes de forma segura
            return secrets.compare_digest(hash_original, hash_nuevo)
            
        except Exception as e:
            print(f"[AutenticacionDTI] Error verificando password: {e}")
            return False
    
    def _inicializar_credenciales(self):
        """Inicializa las credenciales de las facultades si no existen"""
        if not os.path.exists(self.archivo):
            print(f"[AutenticacionDTI] Inicializando sistema de encriptación...")
            print(f"[AutenticacionDTI] Usando PBKDF2 con {self.iterations:,} iteraciones")
            
            # Contraseñas predefinidas para las facultades
            credenciales = {
                "Facultad de Ciencias Sociales": self._encriptar_password("sociales2024"),
                "Facultad de Ciencias Naturales": self._encriptar_password("naturales2024"),
                "Facultad de Ingeniería": self._encriptar_password("ingenieria2024"),
                "Facultad de Medicina": self._encriptar_password("medicina2024"),
                "Facultad de Derecho": self._encriptar_password("derecho2024"),
                "Facultad de Artes": self._encriptar_password("artes2024"),
                "Facultad de Educación": self._encriptar_password("educacion2024"),
                "Facultad de Ciencias Económicas": self._encriptar_password("economicas2024"),
                "Facultad de Arquitectura": self._encriptar_password("arquitectura2024"),
                "Facultad de Tecnología": self._encriptar_password("tecnologia2024")
            }
            
            # Agregar metadatos de seguridad
            archivo_datos = {
                "version": "2.0",
                "encriptacion": "PBKDF2-SHA256",
                "iteraciones": self.iterations,
                "salt_size": self.salt_size,
                "credenciales": credenciales
            }
            
            with open(self.archivo, 'w') as f:
                json.dump(archivo_datos, f, indent=4)
            
            print(f"[AutenticacionDTI] ✓ Archivo de credenciales encriptadas creado: {self.archivo}")
    
    def verificar_facultad(self, nombre_facultad, password):
        """Verifica las credenciales de una facultad con encriptación"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            # Verificar estructura del archivo
            if "credenciales" not in data:
                print(f"[AutenticacionDTI] Error: Formato de archivo inválido")
                return False
            
            credenciales = data["credenciales"]
            
            if nombre_facultad not in credenciales:
                print(f"[AutenticacionDTI] ✗ Facultad no encontrada: {nombre_facultad}")
                return False
            
            hash_almacenado = credenciales[nombre_facultad]
            es_valida = self._verificar_password(password, hash_almacenado)
            
            if es_valida:
                print(f"[AutenticacionDTI] ✓ Autenticación exitosa para: {nombre_facultad}")
            else:
                print(f"[AutenticacionDTI] ✗ Autenticación fallida para: {nombre_facultad}")
            
            return es_valida
            
        except Exception as e:
            print(f"[AutenticacionDTI] Error verificando credenciales: {e}")
            return False
    
    def agregar_facultad(self, nombre_facultad, password):
        """Agrega una nueva facultad al sistema"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            data["credenciales"][nombre_facultad] = self._encriptar_password(password)
            
            with open(self.archivo, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"[AutenticacionDTI] ✓ Facultad agregada: {nombre_facultad}")
            return True
            
        except Exception as e:
            print(f"[AutenticacionDTI] Error agregando facultad: {e}")
            return False
    
    def cambiar_password(self, nombre_facultad, password_nuevo):
        """Cambia la contraseña de una facultad"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            if nombre_facultad not in data["credenciales"]:
                print(f"[AutenticacionDTI] Facultad no encontrada: {nombre_facultad}")
                return False
            
            data["credenciales"][nombre_facultad] = self._encriptar_password(password_nuevo)
            
            with open(self.archivo, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"[AutenticacionDTI] ✓ Contraseña actualizada para: {nombre_facultad}")
            return True
            
        except Exception as e:
            print(f"[AutenticacionDTI] Error cambiando contraseña: {e}")
            return False
    
    def mostrar_info_seguridad(self):
        """Muestra información del sistema de seguridad"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            print("\n" + "="*50)
            print("INFORMACIÓN DE SEGURIDAD DTI")
            print("="*50)
            print(f"Versión: {data.get('version', 'N/A')}")
            print(f"Encriptación: {data.get('encriptacion', 'N/A')}")
            print(f"Iteraciones: {data.get('iteraciones', 'N/A'):,}")
            print(f"Tamaño Salt: {data.get('salt_size', 'N/A')} bytes")
            print(f"Facultades registradas: {len(data.get('credenciales', {}))}")
            print("="*50)
            
        except Exception as e:
            print(f"[AutenticacionDTI] Error mostrando info: {e}")
    
    def mostrar_credenciales_iniciales(self):
        """Muestra las credenciales iniciales para referencia"""
        credenciales_texto = {
            "Facultad de Ciencias Sociales": "sociales2024",
            "Facultad de Ciencias Naturales": "naturales2024", 
            "Facultad de Ingeniería": "ingenieria2024",
            "Facultad de Medicina": "medicina2024",
            "Facultad de Derecho": "derecho2024",
            "Facultad de Artes": "artes2024",
            "Facultad de Educación": "educacion2024",
            "Facultad de Ciencias Económicas": "economicas2024",
            "Facultad de Arquitectura": "arquitectura2024",
            "Facultad de Tecnología": "tecnologia2024"
        }
        
        print("\n" + "="*60)
        print("CREDENCIALES INICIALES DE FACULTADES")
        print("="*60)
        for facultad, password in credenciales_texto.items():
            print(f"{facultad}: {password}")
        print("="*60)
        print("⚠️  NOTA: Contraseñas encriptadas con PBKDF2-SHA256")
        print(f"⚠️  Salt único por contraseña + {self.iterations:,} iteraciones")
        print("="*60)