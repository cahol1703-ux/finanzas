import pandas as pd
import os
import json
from openpyxl import load_workbook
import logging
from .logs_config import configurar_logger

# Tipos de documento usados por la lógica OTES.
OTES = ("2C", "2E", "2K")

# Inicializar el logger para registrar eventos y errores
logger = configurar_logger()

def leer_excel(excel_reglas):
    """Lee todas las hojas del archivo Excel sin encabezado."""
    # Lee todas las hojas del Excel sin considerar la primera fila como encabezado
    return pd.read_excel(excel_reglas, sheet_name=None, header=None)

def procesar_datos(ruta_excel,ruta_json, hoja_a_ignorar=["PERSONAL_CENS", "CORREOS", "Reglas"]):
    """Procesa los datos de las hojas, ignorando una hoja específica."""
    # Inicializar diccionario para almacenar las reglas
    reglas = {}
    # Leer todas las hojas del archivo Excel
    excel_data = leer_excel(ruta_excel)
    # Verificar si el archivo Excel existe
    if not os.path.exists(ruta_excel):
        logger.error(f"El archivo {ruta_excel} no existe.")
        return {}
    
    try:
        # Verificar si el archivo Excel tiene contenido
        if not excel_data:
            logger.error(f"El archivo {ruta_excel} está vacío.")
            return {}
        # Intentar cargar el archivo JSON existente para comparación
        if os.path.exists(ruta_json):
            with open(ruta_json, 'r', encoding='utf-8') as f:
                reglas_json = json.load(f)
        else:
            # Si no existe el JSON, inicializar diccionario vacío
            reglas_json = {}
        # Procesar cada hoja del archivo Excel
        for nombre_hoja, df in excel_data.items():
            # Saltar hojas que están en la lista de ignorar
            if nombre_hoja in hoja_a_ignorar:
                continue
            # Resetear índices del DataFrame para procesamiento limpio
            df = df.reset_index(drop=True)

            # Iterar sobre las filas de la hoja
            for index, row in df.iterrows():
                # Extraer clave (primera columna) y valor (segunda columna)
                clave = row.iloc[0]  
                valor = row.iloc[1]  
                # Limpiar espacios y convertir a string, manejar valores None
                clave = str(clave).strip() if clave is not None else ""
                valor = str(valor).strip() if valor is not None else ""
                # Crear estructura anidada si la hoja no existe en reglas
                if nombre_hoja not in reglas:
                    reglas[nombre_hoja] = {}
                # Guardar la relación clave-valor en el diccionario de reglas
                reglas[nombre_hoja][clave] = valor
        # Comparar reglas actuales con las del JSON para detectar cambios
        if reglas != reglas_json:
            # Si hay cambios, actualizar el archivo JSON 
            logger.debug("El archivo Excel ha sido modificado. Se han actualizado las reglas en el archivo JSON.")
            guardar_json(reglas, ruta_json)
            return reglas  # Devuelve las reglas y modificado 
        else:
            # Si no hay cambios, mantener el JSON actual
            logger.debug("El archivo Excel no ha sufrido modificaciones. El archivo JSON está actualizado.")
            guardar_json(reglas, ruta_json)
            return reglas
    except Exception as e:
        # Capturar y registrar cualquier error durante el procesamiento
        logger.error(f"Error al procesar el archivo Excel: {e}")
        return reglas

def guardar_json(datos, ruta_json):
    """Guarda los datos procesados en un archivo JSON."""
    # Guardar en JSON con formato indentado y soporte para caracteres Unicode
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
        logger.info("Se guardo el archivo correctamente")

def separar_tres_hojas(ruta_excel, ruta_json):
    # Procesar todas las reglas del archivo Excel
    json_reglas = procesar_datos(ruta_excel,ruta_json)
    # Extraer los tres tipos de reglas específicas, usar dict vacío si no existe
    tipo_doc = json_reglas.get("Tipo doc.", {})
    cuentas_historial = json_reglas.get("Cuentas historial",{})
    otes = json_reglas.get("OTES(2C,2E,2K)",{})
    
    return tipo_doc, cuentas_historial, otes

def extraer_dataframe(ruta_excel, columnas=['A','C','D','E','F','K','P','V']):
    # Leer el archivo Excel completo
    df = pd.read_excel(ruta_excel)
    # Crear mapeo de letras de columnas (A, B, C...) a índices numéricos (0, 1, 2...)
    indices = {letter: idx for idx, letter in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}
    # Convertir letras de columnas especificadas a índices numéricos
    indices_col = [indices[i] for i in columnas]
    # Obtener nombres reales de columnas basados en los índices, verificar que existan
    nombre_col = [df.columns[x] for x in indices_col if x < len(df.columns)]
    # Seleccionar solo las columnas especificadas
    df_seleccionado = df.loc[:, nombre_col]
    # Limpiar espacios en blanco de todas las columnas de tipo texto
    for col in df_seleccionado.columns:
        if df_seleccionado[col].dtype == object:  # Solo columnas tipo string
            df_seleccionado[col] = df_seleccionado[col].astype(str).str.strip()

    return df_seleccionado

def filtro_tipo_doc(df, dict_tipo_doc):
    # Verificar que existan las columnas necesarias
    if 'Responsable' not in df.columns or 'Tipo doc' not in df.columns:
        raise ValueError("El DataFrame debe contener las columnas 'Responsable' y 'Tipo doc'.")
    # Limpiar espacios en blanco de las columnas relevantes
    df['Responsable'] = df['Responsable'].astype(object).str.strip()
    df['Tipo doc'] = df['Tipo doc'].str.strip()

    # Crear una máscara booleana para filas donde la columna K es clave del diccionario
    mask = df['Tipo doc'].apply(lambda x: any(key in x for key in dict_tipo_doc.keys()))

    # Aplicar el cambio en columna 'Responsable' usando map con diccionario solo en filas que cumplen la condición
    for key in dict_tipo_doc.keys():
        df.loc[mask & df['Tipo doc'].str.contains(key), 'Responsable'] = dict_tipo_doc[key]
    
    return df   

def filtro_otes(df, dict_otes, tipo_doc=None):
    # Limpiar y preparar las columnas necesarias
    if tipo_doc is None:
        tipo_doc = OTES
    df['Cuenta'] = df['Cuenta'].astype(str).str.strip()
    df['Responsable'] = df['Responsable'].astype(object).str.strip()
    df.columns = df.columns.str.strip()
    # Crear una máscara booleana para filas donde 'Cuenta' contenga las claves del diccionario
    mask = (df['Tipo doc'].isin(tipo_doc)) & (df['Cuenta'].apply(lambda x: any(key in x for key in dict_otes.keys())))

    # Aplicar el cambio en columna 'Responsable' usando map con diccionario solo en filas que cumplen la condición
    for key in dict_otes.keys():
        df.loc[mask & df['Cuenta'].str.contains(key), 'Responsable'] = dict_otes[key]

    # LÓGICA ESPECIAL PARA OTES: Propagación de responsables
    # Filtrar solo documentos OTES para análisis de propagación
    df_filtrado = df[df['Tipo doc'].isin(tipo_doc)].copy()
    responsables = df_filtrado['Responsable'].dropna().unique()

    # Para cada responsable encontrado
    for responsable in responsables:
        # Saltar responsables vacíos o inválidos
        if responsable == "" or responsable =='nan':
            continue
        # Obtener todos los números de documento asociados a este responsable
        docs = df_filtrado[df_filtrado['Responsable'] == responsable]['Número documento'].unique()
        # Asignar el responsable a todos los registros que tienen el mismo número de documento
        pares_mask = (df['Tipo doc'].isin(tipo_doc)) & (df['Número documento'].isin(docs))
        # Asignar el mismo responsable a todos los registros con números de documento relacionados
        df.loc[pares_mask, 'Responsable'] = responsable
    
    return df


def filtro_historial(df, dict_historial):
    # Limpiar espacios en blanco de las columnas relevantes
    df['Cuenta'] = df['Cuenta'].astype(str).str.strip()
    df['Responsable'] = df['Responsable'].astype(object).str.strip()

    # Crear una máscara booleana para filas donde 'Cuenta' contenga las claves del diccionario
    mask = df['Cuenta'].apply(lambda x: any(key in x for key in dict_historial.keys()))
    
    # Aplicar el cambio en columna 'Responsable' usando map con diccionario solo en filas que cumplen la condición
    for key in dict_historial.keys():
        df.loc[mask & df['Cuenta'].str.contains(key), 'Responsable'] = dict_historial[key]
   
    return df

def aplicar_todos_los_filtros(ruta_excel, ruta_json, ruta_salida):
    df = extraer_dataframe(ruta_salida)
    tipo_doc, cuentas_historial, otes = separar_tres_hojas(ruta_excel, ruta_json)

    if not isinstance(tipo_doc, dict) or not isinstance(cuentas_historial, dict) or not isinstance(otes, dict):
        raise ValueError("No se pudieron cargar las reglas de filtros desde Excel/JSON.")
    if not tipo_doc and not cuentas_historial and not otes:
        raise ValueError("Las reglas de filtros están vacías; el proceso no puede continuar.")

    df = filtro_tipo_doc(df, tipo_doc)
    df = filtro_historial(df, cuentas_historial)
    df = filtro_otes(df, otes)
    # Paso 4: Guardar los resultados procesados de vuelta al archivo Excel
    guardar_en_excel(df,ruta_salida)

    return ruta_salida

def guardar_en_excel(df, ruta_salida):

    try:
        # Cargar el libro de Excel existente manteniendo formato
        book = load_workbook(ruta_salida)
        sheet = book.active
        if sheet is None:
            logger.error("No se pudo acceder a la hoja activa del libro Excel")
            return
        # Iterar sobre cada fila del DataFrame
        for idx, row in df.iterrows():
            # Calcular la fila correspondiente en Excel (idx + 2 porque Excel empieza en 1 y tiene encabezado)
            excel_row = idx + 2
            # Verificar que la fila tenga la columna 'Responsable'
            if 'Responsable' in row:
                # Actualizar la celda A (columna Responsable) en la fila correspondiente
                sheet[f'A{excel_row}']= row['Responsable']
            else:
                # Registrar error si falta la columna Responsable
                logger.error(f"no se encuentra responsable en la fila {idx+1} del DataFrame")
        # Guardar los cambios en el archivo Excel
        book.save(ruta_salida)
        logger.info(f"El archivo ha sido actualizado en la hoja con los cambios realizados en 'Responsable'.")
    except Exception as e:
        # Capturar y registrar errores durante el guardado
        logger.error(f"Error al guardar en Excel: {e}")


