import json
import hashlib
import os
import secrets
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class AutenticacionFacultad:
    def __init__(self, nombre_facultad, archivo=None):
        if archivo is None:
            archivo = f"autenticacion_Facultad_{nombre_facultad.replace(' ', '_')}.json"
        self.archivo = archivo
        self.nombre_facultad = nombre_facultad
        self.salt_size = 32
        self.iterations = 100000
        self._inicializar_credenciales()
    
    def _generar_salt(self):
        """Genera un salt aleatorio para cada contraseña"""
        return secrets.token_bytes(self.salt_size)
    
    def _encriptar_password(self, password):
        """Encripta una contraseña con salt y múltiples iteraciones"""
        salt = self._generar_salt()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        password_hash = kdf.derive(password.encode())
        
        combined = salt + password_hash
        return base64.b64encode(combined).decode('utf-8')
    
    def _verificar_password(self, password, hash_almacenado):
        """Verifica una contraseña contra el hash almacenado"""
        try:
            combined = base64.b64decode(hash_almacenado.encode('utf-8'))
            salt = combined[:self.salt_size]
            hash_original = combined[self.salt_size:]
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.iterations,
            )
            hash_nuevo = kdf.derive(password.encode())
            
            return secrets.compare_digest(hash_original, hash_nuevo)
            
        except Exception as e:
            print(f"[AutenticacionFacultad] Error verificando password: {e}")
            return False
    
    def _inicializar_credenciales(self):
        """Inicializa las credenciales de los programas si no existen"""
        if not os.path.exists(self.archivo):
            print(f"[AutenticacionFacultad] Inicializando encriptación para {self.nombre_facultad}...")
            
            # Usuarios y contraseñas predefinidos para programas
            credenciales = {
                "programa1": self._encriptar_password("prog123"),
                "programa2": self._encriptar_password("prog456"),
                "programa3": self._encriptar_password("prog789"),
                "admin_facultad": self._encriptar_password("admin2024"),
                "estudiante_test": self._encriptar_password("test123"),
                "coordinador": self._encriptar_password("coord2024"),
                "profesor": self._encriptar_password("prof2024")
            }
            
            archivo_datos = {
                "version": "2.0",
                "facultad": self.nombre_facultad,
                "encriptacion": "PBKDF2-SHA256",
                "iteraciones": self.iterations,
                "salt_size": self.salt_size,
                "credenciales": credenciales
            }
            
            with open(self.archivo, 'w') as f:
                json.dump(archivo_datos, f, indent=4)
            
            print(f"[AutenticacionFacultad] ✓ Archivo encriptado creado: {self.archivo}")
    
    def verificar_programa(self, usuario, password):
        """Verifica las credenciales de un programa académico"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            if "credenciales" not in data:
                print(f"[AutenticacionFacultad] Error: Formato de archivo inválido")
                return False
            
            credenciales = data["credenciales"]
            
            if usuario not in credenciales:
                print(f"[AutenticacionFacultad] ✗ Usuario no encontrado: {usuario}")
                return False
            
            hash_almacenado = credenciales[usuario]
            es_valida = self._verificar_password(password, hash_almacenado)
            
            if es_valida:
                print(f"[AutenticacionFacultad] ✓ Autenticación exitosa para usuario: {usuario}")
            else:
                print(f"[AutenticacionFacultad] ✗ Autenticación fallida para usuario: {usuario}")
            
            return es_valida
            
        except Exception as e:
            print(f"[AutenticacionFacultad] Error verificando credenciales: {e}")
            return False
    
    def agregar_usuario(self, usuario, password):
        """Agrega un nuevo usuario al sistema"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            if usuario in data["credenciales"]:
                print(f"[AutenticacionFacultad] Usuario ya existe: {usuario}")
                return False
            
            data["credenciales"][usuario] = self._encriptar_password(password)
            
            with open(self.archivo, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"[AutenticacionFacultad] ✓ Usuario agregado: {usuario}")
            return True
            
        except Exception as e:
            print(f"[AutenticacionFacultad] Error agregando usuario: {e}")
            return False
    
    def cambiar_password(self, usuario, password_nuevo):
        """Cambia la contraseña de un usuario"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            if usuario not in data["credenciales"]:
                print(f"[AutenticacionFacultad] Usuario no encontrado: {usuario}")
                return False
            
            data["credenciales"][usuario] = self._encriptar_password(password_nuevo)
            
            with open(self.archivo, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"[AutenticacionFacultad] ✓ Contraseña actualizada para: {usuario}")
            return True
            
        except Exception as e:
            print(f"[AutenticacionFacultad] Error cambiando contraseña: {e}")
            return False
    
    def listar_usuarios(self):
        """Lista todos los usuarios registrados"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            usuarios = list(data["credenciales"].keys())
            print(f"\n[AutenticacionFacultad] Usuarios registrados en {self.nombre_facultad}:")
            for i, usuario in enumerate(usuarios, 1):
                print(f"  {i}. {usuario}")
            
            return usuarios
            
        except Exception as e:
            print(f"[AutenticacionFacultad] Error listando usuarios: {e}")
            return []
    
    def mostrar_info_seguridad(self):
        """Muestra información del sistema de seguridad"""
        try:
            with open(self.archivo, 'r') as f:
                data = json.load(f)
            
            print(f"\n" + "="*50)
            print(f"INFORMACIÓN DE SEGURIDAD - {self.nombre_facultad}")
            print("="*50)
            print(f"Versión: {data.get('version', 'N/A')}")
            print(f"Encriptación: {data.get('encriptacion', 'N/A')}")
            print(f"Iteraciones: {data.get('iteraciones', 'N/A'):,}")
            print(f"Tamaño Salt: {data.get('salt_size', 'N/A')} bytes")
            print(f"Usuarios registrados: {len(data.get('credenciales', {}))}")
            print("="*50)
            
        except Exception as e:
            print(f"[AutenticacionFacultad] Error mostrando info: {e}")
    
    def mostrar_credenciales_iniciales(self):
        """Muestra las credenciales iniciales para referencia"""
        credenciales_texto = {
            "programa1": "prog123",
            "programa2": "prog456",
            "programa3": "prog789",
            "admin_facultad": "admin2024",
            "estudiante_test": "test123",
            "coordinador": "coord2024",
            "profesor": "prof2024"
        }
        
        print(f"\n" + "="*60)
        print(f"CREDENCIALES INICIALES - {self.nombre_facultad}")
        print("="*60)
        for usuario, password in credenciales_texto.items():
            print(f"Usuario: {usuario:15} | Contraseña: {password}")
        print("="*60)
        print("⚠️  NOTA: Contraseñas encriptadas con PBKDF2-SHA256")
        print(f"⚠️  Salt único por contraseña + {self.iterations:,} iteraciones")
        print("="*60)