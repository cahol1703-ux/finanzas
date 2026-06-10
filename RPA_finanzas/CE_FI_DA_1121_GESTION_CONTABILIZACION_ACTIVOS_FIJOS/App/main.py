from mainencriptador import obtener_credenciales
from Functions.descarga_informes import (
    iniciar_driver, cerrar_driver, login, navegacion,
    verificar_2A, cerrar_sesion, verficacion_carpetas,
)
from Functions.unificacion import exportar_excel
from Functions.filtros_simples import aplicar_todos_los_filtros
from Functions.verificacion import verificar_archivo_y_conexion
from Functions.filtros_complejos import lanzar_instancias
from Functions.logs_config import configurar_logger
from Functions.puntos_de_control import (
    cargar_estado, guardar_estado, vaciar_json, vaciar_json_manteniendo_excel,
)
from Functions.usar_referencia import usar_excel_referencia, eliminar_informes
from Functions.tabla_dinamica import crear_tabla_dinamica
from Functions.descarga_informes import sesion_activa
from config import (
    URL_BASE, WEB_DRIVER, NUMEROS_COMPANIA, ARCHIVOS_SALIDA,
    JSON_FILTROS, EXCEL_FILTROS, PUNTO_DE_CONTROL, LATENCIA_MAXIMA,
)

logger = configurar_logger()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de reinicio (llamados desde la GUI)
# ─────────────────────────────────────────────────────────────────────────────

def reiniciar_ejecucion() -> None:
    """Vacía completamente el checkpoint para comenzar desde cero."""
    if not vaciar_json(PUNTO_DE_CONTROL):
        raise RuntimeError(
            f"No se pudo reiniciar el checkpoint en '{PUNTO_DE_CONTROL}'. "
            "Verifique permisos de escritura."
        )
    logger.info("Proceso reiniciado completamente.")


def reiniciar_ejecucion_con_referencia() -> None:
    """Vacía el checkpoint conservando el Excel de referencia."""
    if not vaciar_json_manteniendo_excel(PUNTO_DE_CONTROL):
        raise RuntimeError(
            f"No se pudo reiniciar el checkpoint conservando la referencia en '{PUNTO_DE_CONTROL}'."
        )
    logger.info("Proceso reiniciado conservando excel_referencia.")


# ─────────────────────────────────────────────────────────────────────────────
# Proceso principal
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_proceso() -> None:  # noqa: C901  (función larga por diseño checkpoint)
    # ── Credenciales ──────────────────────────────────────────────────────────
    # Se obtienen al inicio para que estén disponibles en TODOS los pasos,
    # incluso al reanudar desde un checkpoint intermedio.
    try:
        USER, PASS = obtener_credenciales()
    except Exception as e:
        logger.error("No se pudieron cargar las credenciales: %s", e)
        print(f"ERROR: No se pudieron cargar las credenciales: {e}")
        return

    # ── Checkpoint ────────────────────────────────────────────────────────────
    estado = cargar_estado(PUNTO_DE_CONTROL)
    if estado is None:
        # cargar_estado devuelve None solo si el archivo existe pero está corrupto
        logger.error(
            "El archivo de checkpoint está corrupto. "
            "Use 'Reiniciar Proceso' desde la interfaz para comenzar desde cero."
        )
        print("ERROR: Checkpoint corrupto. Use 'Reiniciar Proceso' en la interfaz.")
        return

    paso = estado.get("paso_actual")

    # ═════════════════════════════════════════════════════════════════════════
    # PASO 1: Verificación de requisitos y omisión de registros 2A
    # ═════════════════════════════════════════════════════════════════════════
    if paso is None or paso == "inicio":
        logger.info("─── PASO 1: Inicio / verificación 2A ───")
        try:
            # Verificar archivo de filtros Y conectividad con el servidor JDE
            if not verificar_archivo_y_conexion(EXCEL_FILTROS, LATENCIA_MAXIMA, URL_BASE):
                logger.error("No se cumplen los requisitos mínimos para iniciar.")
                print("ERROR: No se cumplen los requisitos mínimos (archivo o conexión).")
                return

            driver, ruta_archivos, nombre_documento = iniciar_driver(
                ARCHIVOS_SALIDA, URL_BASE
            )

            if driver is None:
                logger.error("No se pudo iniciar el navegador. Proceso detenido.")
                print("ERROR: No se pudo iniciar el navegador.")
                return

            try:
                if sesion_activa(driver):
                    logger.info("Sesión activa detectada. Se omite login.")
                else:
                    # Texto de error multi-clave separado por | para mayor robustez
                    if not login(driver, "incorrectos|error de usuario|credenciales", USER, PASS):
                        logger.error("No se pudo iniciar sesión en JDE durante el Paso 1.")
                        print("ERROR: No se pudo iniciar sesión en JDE.")
                        return

                verificar_2A(driver)
                cerrar_sesion(driver)
            finally:
                # El driver siempre se cierra, incluso si verificar_2A lanza excepción
                cerrar_driver(driver)

            paso = "descargar_informes"
            ok = guardar_estado(estado, PUNTO_DE_CONTROL, {
                "paso_actual": "descargar_informes",
                "ruta_archivos": ruta_archivos,
                "nombre_documento": nombre_documento,
            })
            if not ok:
                logger.error("No se pudo guardar el checkpoint tras el Paso 1. El proceso continuará pero podría reiniciarse desde cero.")

            logger.info("Paso 1 completado: verificación de 2A.")
            print("Paso 1 completado: verificación de 2A.")

        except Exception as e:
            logger.error("Error en el Paso 1 (inicio/2A): %s", e, exc_info=True)
            print(f"ERROR en Paso 1: {e}")
            return

    # ═════════════════════════════════════════════════════════════════════════
    # PASO 2: Descarga de informes por compañía
    # ═════════════════════════════════════════════════════════════════════════
    if paso == "descargar_informes":
        logger.info("─── PASO 2: Descarga de informes ───")
        try:
            ruta_archivos = estado.get("ruta_archivos")
            if not ruta_archivos:
                logger.error("No se encontró 'ruta_archivos' en el checkpoint. Use 'Reiniciar Proceso'.")
                print("ERROR: ruta_archivos no encontrada en el checkpoint.")
                return

            navegacion(NUMEROS_COMPANIA, ruta_archivos, URL_BASE, USER, PASS)

            if verficacion_carpetas(ruta_archivos, NUMEROS_COMPANIA):
                paso = "unificar_excel"
                ok = guardar_estado(estado, PUNTO_DE_CONTROL, {"paso_actual": "unificar_excel"})
                if not ok:
                    logger.error("No se pudo guardar el checkpoint tras el Paso 2.")
                logger.info("Paso 2 completado: informes descargados.")
                print("Paso 2 completado: informes descargados.")
            else:
                logger.error(
                    "Faltan informes en '%s'. Algunos archivos no se descargaron correctamente. "
                    "El proceso se detuvo para evitar generar un Excel incompleto.",
                    ruta_archivos,
                )
                print("ERROR: Faltan informes. Revise los logs para más detalles.")
                return

        except Exception as e:
            logger.error("Error en el Paso 2 (descarga): %s", e, exc_info=True)
            print(f"ERROR en Paso 2: {e}")
            return

    # ═════════════════════════════════════════════════════════════════════════
    # PASO 3: Unificación de Excel y filtros simples
    # ═════════════════════════════════════════════════════════════════════════
    if paso == "unificar_excel":
        logger.info("─── PASO 3: Unificación y filtros simples ───")
        try:
            ruta_archivos = estado.get("ruta_archivos")
            nombre_documento = estado.get("nombre_documento")

            if not ruta_archivos or not nombre_documento:
                logger.error(
                    "Faltan variables en el checkpoint (ruta_archivos=%s, nombre_documento=%s). "
                    "Use 'Reiniciar Proceso'.",
                    ruta_archivos, nombre_documento,
                )
                print("ERROR: Faltan variables en el checkpoint. Use 'Reiniciar Proceso'.")
                return

            excel = exportar_excel(ruta_archivos, nombre_documento, NUMEROS_COMPANIA)
            if not excel:
                logger.error(
                    "No se pudo generar el Excel unificado. "
                    "Revise los logs para ver qué compañías fallaron."
                )
                print("ERROR: No se generó el Excel unificado.")
                return

            excel_final = aplicar_todos_los_filtros(EXCEL_FILTROS, JSON_FILTROS, excel)
            if not excel_final:
                logger.error(
                    "aplicar_todos_los_filtros no retornó una ruta válida. "
                    "Verifique que el Excel de filtros tenga las hojas esperadas."
                )
                print("ERROR: Falló la aplicación de filtros simples.")
                return

            paso = "filtros_complejos"
            ok = guardar_estado(estado, PUNTO_DE_CONTROL, {
                "paso_actual": "filtros_complejos",
                "excel_final": excel_final,
            })
            if not ok:
                logger.error("No se pudo guardar el checkpoint tras el Paso 3.")

            logger.info("Paso 3 completado: Excel unificado y filtros simples aplicados.")
            print("Paso 3 completado: unificación y filtros simples.")

            # Usar Excel de ejecución anterior como referencia si existe
            excel_referencia = estado.get("excel_referencia")
            if excel_referencia:
                import os
                if os.path.exists(excel_referencia):
                    logger.info("Aplicando Excel de referencia: %s", excel_referencia)
                    usar_excel_referencia(excel_referencia, excel_final)
                else:
                    logger.warning(
                        "El Excel de referencia '%s' ya no existe en disco. Se omite.",
                        excel_referencia,
                    )

            eliminar_informes(ruta_archivos, NUMEROS_COMPANIA)

        except Exception as e:
            logger.error("Error en el Paso 3 (unificación): %s", e, exc_info=True)
            print(f"ERROR en Paso 3: {e}")
            return

    # ═════════════════════════════════════════════════════════════════════════
    # PASO 4: Filtros complejos y tabla dinámica
    # ═════════════════════════════════════════════════════════════════════════
    if paso == "filtros_complejos":
        logger.info("─── PASO 4: Filtros complejos ───")
        try:
            excel_final = estado.get("excel_final")
            if not excel_final:
                logger.error(
                    "No se encontró 'excel_final' en el checkpoint. Use 'Reiniciar Proceso'."
                )
                print("ERROR: excel_final no encontrado en el checkpoint.")
                return

            import os
            if not os.path.exists(excel_final):
                logger.error(
                    "El archivo '%s' del checkpoint ya no existe en disco. "
                    "Use 'Reiniciar Proceso' para generar uno nuevo.",
                    excel_final,
                )
                print(f"ERROR: El archivo Excel '{excel_final}' no existe.")
                return

            lanzar_instancias(excel_final, EXCEL_FILTROS, URL_BASE, PASS, USER)
            crear_tabla_dinamica(excel_final)

            ok = guardar_estado(estado, PUNTO_DE_CONTROL, {"excel_referencia": excel_final})
            if not ok:
                logger.error("No se pudo guardar el checkpoint final. La próxima ejecución no tendrá Excel de referencia.")

            logger.info("Paso 4 completado: filtros complejos y tabla dinámica.")
            print(
                "Paso 4 completado. Proceso finalizado correctamente.\n"
                "Recuerde usar 'Reiniciar Proceso' si el resultado fue satisfactorio."
            )

        except Exception as e:
            logger.error("Error en el Paso 4 (filtros complejos): %s", e, exc_info=True)
            print(f"ERROR en Paso 4: {e}")
            return


if __name__ == "__main__":
    ejecutar_proceso()