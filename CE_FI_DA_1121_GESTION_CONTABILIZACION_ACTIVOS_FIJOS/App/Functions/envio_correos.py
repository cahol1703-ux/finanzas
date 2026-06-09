<<<<<<< HEAD
import pandas as pd
import smtplib
import os
import time
import platform
from typing import Optional, Dict
from .logs_config import logger


def generar_excel(df: pd.DataFrame, responsable: str, ruta: str) -> str:
    df_responsable = df[df['Responsable'] == responsable]

    carpeta = os.path.join(ruta, responsable)
=======
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
>>>>>>> 952da04 (Actualización)
    os.makedirs(carpeta, exist_ok=True)
    archivo = os.path.join(carpeta, f"{responsable}.xlsx")

    df_responsable.to_excel(archivo, index=False)
<<<<<<< HEAD
    logger.info(f"archivo guardado en {archivo}")
    return archivo


def _send_via_outlook(destinatario: str, asunto: str, mensaje: str, archivo_adjunto: str) -> bool:
    try:
        import win32com.client as win32  # import local para evitar fallo en Linux
        outlook = win32.Dispatch('Outlook.Application')
        mail = outlook.CreateItem(0)
        mail.To = destinatario
        mail.Subject = asunto
        mail.HTMLBody = mensaje
        mail.Attachments.Add(archivo_adjunto)
        mail.Send()
        logger.info(f"correo enviado vía Outlook a {destinatario}")
        return True
    except Exception as e:
        logger.exception("Fallo envío vía Outlook")
        return False


def _send_via_smtp(destinatario: str, asunto: str, mensaje: str, archivo_adjunto: str, smtp_config: Optional[Dict] = None) -> bool:
    smtp_config = smtp_config or {}
    servidor = smtp_config.get('server', 'localhost')
    puerto = smtp_config.get('port', 25)
    remitente = smtp_config.get('from_addr', f'noreply@{platform.node()}')
    import mimetypes
    from email.message import EmailMessage

    try:
        msg = EmailMessage()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.set_content(mensaje, subtype='html')

        # Adjuntar archivo si existe
        if archivo_adjunto and os.path.exists(archivo_adjunto):
            ctype, encoding = mimetypes.guess_type(archivo_adjunto)
            if ctype is None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            with open(archivo_adjunto, 'rb') as f:
                data = f.read()
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(archivo_adjunto))

        # Conectar al servidor
        use_tls = smtp_config.get('use_tls', False)
        username = smtp_config.get('username')
        password = smtp_config.get('password')

        with smtplib.SMTP(servidor, puerto, timeout=30) as s:
            s.ehlo()
            if use_tls:
                s.starttls()
                s.ehlo()
            if username and password:
                s.login(username, password)
            s.send_message(msg)

        logger.info(f"correo enviado vía SMTP a {destinatario} (servidor={servidor}:{puerto})")
        return True
    except Exception as e:
        logger.exception("Fallo envío vía SMTP")
        return False


def enviar_correo(destinatario: str, asunto: str, mensaje: str, archivo_adjunto: str, *, dry_run: bool = False, use_outlook: Optional[bool] = None, smtp_config: Optional[Dict] = None) -> bool:
    if dry_run:
        logger.info(f"[dry_run] Preparado para enviar a {destinatario}: {asunto} (adj: {archivo_adjunto})")
        return True

    # Si use_outlook no especificado, preferir Outlook en Windows
    prefer_outlook = (use_outlook if use_outlook is not None else (platform.system() == 'Windows'))

    if prefer_outlook:
        ok = _send_via_outlook(destinatario, asunto, mensaje, archivo_adjunto)
        if ok:
            return True
        logger.warning("Outlook falló, intentando SMTP de fallback")

    # Fallback a SMTP
    return _send_via_smtp(destinatario, asunto, mensaje, archivo_adjunto, smtp_config=smtp_config)


def analizar_excel(ruta_archivo: str, hoja: Optional[str] = 0) -> Optional[Dict[str, str]]:
    try:
        # Intentar leer sin encabezado (header=None) — funciona si el archivo no tiene headers
        df_none = pd.read_excel(ruta_archivo, sheet_name=hoja, header=None)
        vals_none = df_none.iloc[:, 1].astype(str).str.strip()
        if vals_none.str.contains('@').any():
            keys = df_none.iloc[:, 0].astype(str).str.strip()
            correos = dict(zip(keys, vals_none))
            return correos

        # Si no se detectan emails, intentar con header=0 (archivo con encabezado)
        df_hdr = pd.read_excel(ruta_archivo, sheet_name=hoja, header=0)

        # Preferir segunda columna si contiene correos
        if df_hdr.shape[1] >= 2 and df_hdr.iloc[:, 1].astype(str).str.contains('@').any():
            keys = df_hdr.iloc[:, 0].astype(str).str.strip()
            vals = df_hdr.iloc[:, 1].astype(str).str.strip()
            correos = dict(zip(keys, vals))
            return correos

        # Buscar automáticamente la columna que más tenga '@' si no está en la segunda
        best_col = None
        best_count = 0
        for col in df_hdr.columns:
            try:
                cnt = df_hdr[col].astype(str).str.contains('@').sum()
                if cnt > best_count:
                    best_count = cnt
                    best_col = col
            except Exception:
                continue

        if best_col is not None and best_count > 0:
            # usar la primera columna como clave y best_col como valor
            keys = df_hdr.iloc[:, 0].astype(str).str.strip()
            vals = df_hdr[best_col].astype(str).str.strip()
            correos = dict(zip(keys, vals))
            return correos

        logger.warning("No se detectaron direcciones de correo en el archivo de reglas; revisa el formato")
        return None
    except Exception as e:
        logger.exception(f"Error al procesar el archivo de reglas: {e}")
        return None


def procesar_envio(ruta_excel: str, reglas: str, hoja: Optional[str], ruta_base: str, *, dry_run: bool = False, smtp_config: Optional[Dict] = None, use_outlook: Optional[bool] = None, delay: float = 1.0) -> None:
    try:
        responsables_dict = analizar_excel(reglas, hoja)
        if not responsables_dict:
            logger.error("no se pudo generar el diccionario de responsables desde reglas")
            return

        df = pd.read_excel(ruta_excel)
        logger.info(f"datos leídos: {len(df)} filas")

        if 'Responsable' not in df.columns:
            logger.error("La columna 'Responsable' no existe en el Excel de datos")
            return

        responsables = df['Responsable'].dropna().unique()
        for responsable in responsables:
            correo_responsable = responsables_dict.get(str(responsable))
            if not correo_responsable:
                logger.warning(f"No se encontró correo para el responsable: {responsable}")
                continue

            asunto = f"Registros pendientes para {responsable}"
            archivo_adjunto = generar_excel(df, responsable, ruta_base)
            mensaje = f"""
<html>
<body>
    <h2>Estimado {responsable},</h2>
    <p>Adjunto encontrarás el archivo con los registros asignados a ti.</p>
    <p>Saludos,</p>
</body>
</html>
"""

            enviado = enviar_correo(correo_responsable, asunto, mensaje, archivo_adjunto, dry_run=dry_run, use_outlook=use_outlook, smtp_config=smtp_config)
            if not enviado:
                logger.error(f"No fue posible enviar el correo a {correo_responsable} para {responsable}")
            time.sleep(delay)

    except Exception as e:
        logger.exception(f"Error en procesar_envio: {e}")
=======
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
>>>>>>> 952da04 (Actualización)
