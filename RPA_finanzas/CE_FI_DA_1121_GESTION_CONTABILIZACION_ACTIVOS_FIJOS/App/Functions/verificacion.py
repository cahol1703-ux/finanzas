import os
import requests
import time
from .logs_config import configurar_logger
from config import URL_BASE


logger = configurar_logger()

def verificar_archivo_y_conexion(archivo_entrada, Latencia_max, url_prueba=None):
    # Verificar si el archivo de entrada existe
    if not os.path.exists(archivo_entrada):
        logger.error(f"Error: El archivo de entrada '{archivo_entrada}' no se encuentra o no es accesible.")
        return False  # Si el archivo no existe, retornamos False

    logger.info(f"El archivo de entrada '{archivo_entrada}' está disponible.")

    url_prueba = url_prueba or URL_BASE
    try:
        start_time = time.time()
        response = requests.get(url_prueba, timeout=10)
        end_time = time.time()
        
        # Medimos la latencia
        latencia = round((end_time - start_time) * 1000, 2)  # Latencia en milisegundos
        if response.status_code == 200:
            logger.info(f"Conexión exitosa a JDE. Latencia: {latencia} ms. URL: {url_prueba}")
                        # Verificar si la latencia está dentro del límite aceptable
            if latencia > Latencia_max:
                logger.error(f"Advertencia: La latencia a JDE es demasiado alta ({latencia} ms). La conexión puede no ser confiable.")
                return False  # Si la latencia es alta, se retorna False (no continuar con el proceso)
            
            return True  # Si la conexión es exitosa, retornamos True
        else:
            logger.error(f"Error: No se pudo conectar al servidor. Código de respuesta: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error: No se pudo conectar a JDE. {e}")
        return False


