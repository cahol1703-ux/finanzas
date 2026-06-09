import json
import os
from .logs_config import configurar_logger

logger = configurar_logger()

def guardar_estado(estado, archivo, variables=None):
    try:
        if estado is None:
            estado = {}
        if variables:
            estado.update(variables)
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(estado, f, indent=4)
    except Exception as e:
        logger.exception("Error al guardar el checkpoint: %s", e)
        raise

def cargar_estado(archivo):
    """Carga el estado y variables desde un archivo JSON."""
    try: 
        # Crear archivo vacío si no existe
        if not os.path.exists(archivo):
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
        # Cargar contenido del archivo
        with open(archivo, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        logger.info(f"Estado y variables cargados desde {archivo}")
        return estado
    except Exception as e:
        logger.error(f"Error al cargar el estado y las variables: {e}")
        return None  
    
def vaciar_json(ruta):
    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=4)
        print(f"Contenido de '{ruta}' vaciado correctamente.")
    except Exception as e:
        print(f"Error al vaciar el JSON: {e}")

def vaciar_json_manteniendo_excel(ruta):
    try:
        datos = {}
        
        # Leer el JSON actual
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                datos = json.load(f)

        # Conservar solo "excel_referencia" si existe
        nuevo_contenido = {}
        if "excel_referencia" in datos:
            nuevo_contenido["excel_referencia"] = datos["excel_referencia"]

        # Guardar el nuevo contenido
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(nuevo_contenido, f, indent=4)
        
        print(f"Contenido de '{ruta}' vaciado correctamente, conservando 'excel_referencia'.")
    
    except Exception as e:
        print(f"Error al vaciar el JSON: {e}")

