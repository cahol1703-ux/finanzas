from mainencriptador import obtener_credenciales
from Functions.descarga_informes import (
    iniciar_driver, cerrar_driver, login, navegacion, verificar_2A, cerrar_sesion, verficacion_carpetas
)
from Functions.driver_manager import validar_entorno
from Functions.unificacion import exportar_excel
from Functions.filtros_simples import aplicar_todos_los_filtros
from Functions.verificacion import verificar_archivo_y_conexion
from Functions.filtros_complejos import lanzar_instancias
from Functions.logs_config import configurar_logger
from Functions.puntos_de_control import (
    cargar_estado, guardar_estado, vaciar_json, vaciar_json_manteniendo_excel
)
from Functions.usar_referencia import usar_excel_referencia, eliminar_informes
from Functions.tabla_dinamica import crear_tabla_dinamica
from config import (
    URL_BASE, NUMEROS_COMPANIA, ARCHIVOS_SALIDA,
    JSON_FILTROS, EXCEL_FILTROS, PUNTO_DE_CONTROL, LATENCIA_MAXIMA
)

logger = configurar_logger()


def reiniciar_ejecucion():
    print(PUNTO_DE_CONTROL)
    # Vacía completamente el archivo JSON de puntos de control
    vaciar_json(PUNTO_DE_CONTROL)

def reiniciar_ejecucion_con_referencia():
    # Vacía el JSON pero mantiene la referencia del Excel anterior
    vaciar_json_manteniendo_excel(PUNTO_DE_CONTROL)

def ejecutar_proceso():
    try:
        # CORRECCIÓN 1: Las credenciales se obtienen al inicio de la función,
        # antes de cualquier bloque de paso. Así USER y PASS están disponibles
        # en TODOS los pasos, incluso cuando se reanuda desde un checkpoint.
        try:
            USER, PASS = obtener_credenciales()
        except Exception as e:
            logger.error("Error cargando credenciales: %s", e)
            print(f"Error cargando credenciales: {e}")
            return

        try:
            validar_entorno()
        except Exception as e:
            logger.error("Validación de entorno falló: %s", e)
            print("ERROR: Validación de entorno falló. Revise los logs.")
            return

        # Carga el estado actual desde el archivo de puntos de control
        estado = cargar_estado(PUNTO_DE_CONTROL) or {}
        paso = estado.get("paso_actual")

        # PASO 1: INICIO - Verificación de requisitos y Omitir 2A
        if paso is None or paso == "inicio":
            try:
                # Verifica que existan los archivos necesarios y haya conexión
                if not verificar_archivo_y_conexion(EXCEL_FILTROS, LATENCIA_MAXIMA):
                    logger.error(f"No se cumplen los requisitos minimos")
                    return
                logger.info("Se inicia el proceso de ignorar 2A")
                print("Se inicia el proceso de ignorar 2A")
                # Inicia el driver de navegador web y configura rutas
                driver, ruta_archivos, nombre_documento = iniciar_driver(ARCHIVOS_SALIDA, URL_BASE)

                #  VALIDACIÓN CRÍTICA 
                if driver is None:
                   logger.error("No se pudo iniciar el navegador. Proceso detenido.")
                   print("ERROR: No se pudo iniciar el navegador.")
                   return

                # AUTO‑LOGIN INTELIGENTE
                from Functions.descarga_informes import sesion_activa

                if sesion_activa(driver):
                   logger.info(" Sesión activa detectada. Se omite login.")
                   print("Sesión activa detectada. No se realizó login.")
                else:
                    logger.info("No hay sesión activa. Realizando login automático.")
                    print("No hay sesión activa. Realizando login.")

                login(driver, "incorrectos", USER, PASS)
                # incia proceso de Omitir 2A
                verificar_2A(driver)
                # Cierra la sesión y el driver
                cerrar_sesion(driver)
                cerrar_driver(driver)
                # Actualiza el estado para continuar con el siguiente paso
                paso = "descargar_informes"
                variables = {
                    "paso_actual": "descargar_informes",
                    "ruta_archivos": ruta_archivos,
                    "nombre_documento": nombre_documento
                }
                guardar_estado(estado, PUNTO_DE_CONTROL, variables)
                logger.info("Paso 1 completado: verificación de 2A.")
                print("Paso 1 completado: verificación de 2A.")
            except Exception as e:
                logger.error(f"Error al ejecutar el paso 'inicio': {e}")
                print(f"Error al ejecutar el paso 'verificacion de 2A': {e}")
                return

        # PASO 2: DESCARGA DE INFORMES
        if paso == "descargar_informes":
            print(f"Se inicia paso de descarga de informes")
            try:
                # Recupera la ruta de archivos del estado guardado
                ruta_archivos = estado.get("ruta_archivos") if estado else None
                # Navega por cada compañía y descarga sus informes
                # CORRECCIÓN 1 (continuación): USER y PASS ya están definidos arriba,
                # no importa si se llega aquí directamente desde el checkpoint.
                navegacion(NUMEROS_COMPANIA, ruta_archivos, URL_BASE, USER, PASS)
                # Verifica que se hayan creado todas las carpetas de compañías y se encuentren todos los informes
                if verficacion_carpetas(ruta_archivos, NUMEROS_COMPANIA):
                    # Si todo está correcto, avanza al siguiente paso
                    paso = "unificar_excel"
                    variables = {
                        "paso_actual": "unificar_excel"
                    }
                    guardar_estado(estado, PUNTO_DE_CONTROL, variables)
                else:
                    # Si faltan informes, registra error y termina
                    logger.error(f"Error: no se ha encontrado los informes, archivo final incompleto")
                    print(f"Error: no se ha encontrado los informes, archivo final incompleto")
                    return
                print(f"proceso de descarga de informes completado")
            except Exception as e:
                logger.error(f"Error al ejecutar el paso 'descargar_informes': {e}")
                print(f"Error al ejecutar el paso de descarga de informes")
                return

        # PASO 3: UNIFICACIÓN DE EXCEL Y FILTROS SIMPLES
        if paso == "unificar_excel":
            print(f"se inicia el proceso de unificar informes")
            try:
                # Recupera variables del estado
                ruta_archivos = estado.get("ruta_archivos") if estado else None
                nombre_documento = estado.get("nombre_documento") if estado else None
                # Unifica todos los informes descargados en un solo archivo Excel
                excel = exportar_excel(ruta_archivos, nombre_documento, NUMEROS_COMPANIA)
                # CORRECCIÓN 1 (continuación): Validar que el Excel se generó antes de continuar
                if not excel:
                    logger.error("No se pudo generar el Excel unificado. Proceso detenido.")
                    print("Error: No se pudo generar el Excel unificado.")
                    return
                # Aplica filtros simples al Excel unificado
                excel_final = aplicar_todos_los_filtros(EXCEL_FILTROS, JSON_FILTROS, excel)
                # Prepara para el siguiente paso
                paso = "filtros_complejos"
                variables = {
                    "paso_actual": "filtros_complejos",
                    "excel_final": excel_final
                }
                guardar_estado(estado, PUNTO_DE_CONTROL, variables)
                print("se completo correctamente el paso de unificacion y filtros simples")
                # Si existe un Excel de referencia previo, lo utiliza para comparaciones
                if estado and estado.get("excel_referencia"):
                    excel_referencia = estado.get("excel_referencia")
                    usar_excel_referencia(excel_referencia, excel_final)
                # Elimina los informes individuales para liberar espacio
                eliminar_informes(ruta_archivos, NUMEROS_COMPANIA)
            except Exception as e:
                logger.error(f"Error al ejecutar el paso 'unificar_excel': {e}")
                print(f"Error al ejecutar el paso de unificacion de informes")
                return

        # PASO 4: FILTROS COMPLEJOS Y FINALIZACIÓN
        if paso == "filtros_complejos":
            print("se incia el proceso de filtros complejos")
            try:
                # Recupera el Excel procesado del estado
                excel_final = estado.get("excel_final") if estado else None
                if not excel_final:
                    logger.error("No se encontró el Excel procesado en el estado")
                    print("Error: No se encontró el Excel procesado.")
                    return
                # Aplica filtros complejos que requieren múltiples instancias del navegador
                lanzar_instancias(excel_final, EXCEL_FILTROS, URL_BASE, PASS, USER)
                # Crea tabla dinámica(estatica) con los datos finales
                crear_tabla_dinamica(excel_final)
                # Guarda el Excel final como referencia para futuras ejecuciones
                variables = {
                    "excel_referencia": excel_final
                }
                guardar_estado(estado, PUNTO_DE_CONTROL, variables)
            except Exception as e:
                logger.error(f"Error al ejecutar el paso 'filtros_complejos': {e}")
                print(f"Error al aplicar filtros complejos: {e}")
                return
            print(f"se finalizo el proceso de filtros complejos, recuerde reiniciar los puntos de control si el resultado fue satisfacorio")
    except Exception as e:
        # Captura cualquier error no manejado en el proceso general
        logger.error(f"Error en el proceso general: {e}")


if __name__ == "__main__":
    ejecutar_proceso()
