"""import pandas as pd
import smtplib
import os
import time
import win32com.client as win32
from .logs_config import logger

#outlook = win32.Dispatch('Outlook.Application')
def generar_excel(df, responsable, ruta):
    df_responsable = df[df['Responsable'] == responsable]

    carpeta = os.path.join(ruta, "responsable")
    os.makedirs(carpeta, exist_ok=True)
    archivo = os.path.join(carpeta, f"{responsable}.xlsx")

    df_responsable.to_excel(archivo, index=False)
    logger.info(f"arhivo guardao en {archivo}")
    return archivo

def enviar_correo(destinatario, asunto, mensaje, archivo_adjunto):
    try:
        outlook = win32.Dispatch('Outlook.Application')
        mail = outlook.CreateItem(0)

        mail.To = destinatario
        mail.Subject = asunto
        mail.HTMLbody = mensaje

        mail.Attachments.Add(archivo_adjunto)
        mail.Send()
        logger.info(f"correo enviado a {destinatario}")
    except Exception as e:
        logger.error(f"Error al enviar el correo: {e}")

def analizar_excel(ruta_archivo, hoja):
    try:
        # Leer el archivo Excel y la hoja específica
        df = pd.read_excel(ruta_archivo, sheet_name=hoja)

        # Crear un diccionario clave=columna A, valor=columna B
        correos = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))  # Columna A: 0, Columna B: 1

        return correos
    except Exception as e:
        print(f"Error al procesar el archivo: {e}")
        return None

def procesar_envio(ruta_excel, reglas, hoja, ruta_base):
    try:
        responsables_dict = analizar_excel(reglas, hoja)
        print(responsables_dict)
        if not responsables_dict:
            logger.error(f"no se pudo generar el diccionario de responsables")
            return
        df = pd.read_excel(ruta_excel)
        print(f"primeras filas", df.head())
        responsables = df['Responsable'].unique()
        print(responsables)
        for i, responsable in enumerate(responsables):
            if responsable in responsables_dict or i !=0 :
                correo_responsable = responsables_dict[responsable]
                print(correo_responsable)
            else:
                print(f"No se encontró correo para el responsable; {responsable}") 
                continue
            asunto = f"Registros pendientes para {responsable}"
            archivo_adjunto = generar_excel(df, responsable, ruta_base)
            mensaje = f
            <html>
            <body>
                <h2>Estimado {responsable},</h2>
                <p>Adjunto encontrarás el archivo con los registros asignados a ti.</p>
                <p>Saludos,</p>
            </body>
            </html>
            
            enviar_correo(correo_responsable, asunto, mensaje, archivo_adjunto)
            time.sleep(1)
    except Exception as e:
        logger.error(f"{e}")

"""