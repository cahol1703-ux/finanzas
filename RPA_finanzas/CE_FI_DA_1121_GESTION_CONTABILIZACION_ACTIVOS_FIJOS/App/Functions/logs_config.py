import logging
import os
from datetime import datetime

def configurar_logger(nombre='CE1121'):
    carpeta_logs = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "Data", "logs"))
    os.makedirs(carpeta_logs, exist_ok=True)

    formato = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    nombre_archivo_log = os.path.join(carpeta_logs, f"log_{fecha_actual}.log")

    logger = logging.getLogger(nombre)
    logger.setLevel(logging.INFO)

    if not any(isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == os.path.abspath(nombre_archivo_log)
               for handler in logger.handlers):
        file_handler = logging.FileHandler(nombre_archivo_log)
        file_handler.setFormatter(formato)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
