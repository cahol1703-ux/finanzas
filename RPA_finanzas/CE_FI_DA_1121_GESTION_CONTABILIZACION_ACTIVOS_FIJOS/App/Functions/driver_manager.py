import os
import platform
import re
import shutil
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Permitir a webdriver-manager resolver descargas en entornos con SSL restringido.
# Esto corresponde a: os.environ['WDM_SSL_VERIFY'] = '0'
os.environ.setdefault("WDM_SSL_VERIFY", "0")

from .logs_config import configurar_logger

logger = configurar_logger("CE1121.driver")
CHROME_DOWNLOAD_URL = "https://www.google.com/chrome/"
CHROMEDRIVER_DOWNLOAD_URL = "https://chromedriver.chromium.org/downloads"


class DriverException(Exception):
    """Base exception for driver creation and validation errors."""


class DriverFatalError(DriverException):
    """Non-recoverable error that should abort processing."""


class DriverRetryableError(DriverException):
    """Transient Selenium error that may be retried."""


class EnvironmentValidationError(DriverFatalError):
    """Environment is not ready for browser automation."""


def _parse_version(output: str) -> str | None:
    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output)
    return match.group(1) if match else None


def _run_process(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.debug("Error ejecutando comando %s: %s", command, exc)
        return None


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _ensure_executable(path: str) -> None:
    if not os.path.exists(path):
        return
    if _is_windows():
        return
    try:
        current_mode = os.stat(path).st_mode
        if not (current_mode & stat.S_IXUSR):
            os.chmod(path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            logger.debug("Se agregaron permisos de ejecución a ChromeDriver: %s", path)
    except OSError as exc:
        logger.warning("No se pudieron ajustar permisos de ejecución para ChromeDriver %s: %s", path, exc)


def _find_chrome_executable() -> str | None:
    candidates: list[str] = []
    env_chrome = os.environ.get("CHROME_BIN") or os.environ.get("GOOGLE_CHROME_BIN")
    if env_chrome:
        candidates.append(env_chrome)

    candidates.extend([
        shutil.which("chrome"),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ])

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)

    logger.debug("No se encontró Google Chrome. Candidatos evaluados: %s", candidates)
    return None


def obtener_version_chrome() -> str | None:
    chrome_path = _find_chrome_executable()

    if not chrome_path:
        return None

    try:
        result = subprocess.run(
            f'"{chrome_path}" --version',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )

        salida = result.stdout.strip() or result.stderr.strip()

        logger.info(f"Versión detectada de Chrome: {salida}")

        return _parse_version(salida)

    except Exception as e:
        logger.error(f"Error obteniendo versión de Chrome: {e}")
        return None


def obtener_version_chromedriver(driver_path: str) -> str | None:
    salida = _run_process([driver_path, "--version"])
    if salida:
        return _parse_version(salida)
    return None


def _crear_opciones(download_dir: str | None = None, headless: bool = False) -> Options:
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--remote-allow-origins=*")

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    if download_dir:
        options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        })

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


def _es_incompatibilidad(error: WebDriverException) -> bool:
    mensaje = str(error).lower()
    return (
        "only supports chrome version" in mensaje
        or "current browser version is" in mensaje
        or "session not created" in mensaje
        or "driver executable" in mensaje
        or "executable may have wrong architecture" in mensaje
    )


def validar_entorno() -> bool:
    chrome_path = _find_chrome_executable()
    if not chrome_path:
        raise EnvironmentValidationError(
            "No se encontró una instalación de Google Chrome. Instale Google Chrome o configure CHROME_BIN/GOOGLE_CHROME_BIN con la ruta de chrome.exe."
        )

    chrome_version = obtener_version_chrome()
    if not chrome_version:
        raise EnvironmentValidationError(
            "No se pudo determinar la versión de Google Chrome instalada."
        )

    try:
        driver_path = ChromeDriverManager().install()
        
    except Exception as exc:
        raise EnvironmentValidationError(
            f"No se pudo descargar o resolver ChromeDriver: {exc}. Compruebe acceso a internet y permisos."
        ) from exc

    if not os.path.exists(driver_path):
        raise EnvironmentValidationError(
            "ChromeDriver descargado no existe en la ruta esperada."
        )

    if not _is_windows() and driver_path.lower().endswith(".exe"):
        raise EnvironmentValidationError(
            "ChromeDriver resuelto es un ejecutable de Windows en un sistema no Windows. "
            "Verifique la configuración del entorno o elimine overrides manuales de chromedriver."
        )

    _ensure_executable(driver_path)
    chromedriver_version = obtener_version_chromedriver(driver_path)
    logger.info("Validación de entorno: Chrome=%s ChromeDriver=%s", chrome_version, chromedriver_version)
    return True


def crear_driver(download_dir: str | None = None, headless: bool = False) -> webdriver.Chrome:
    try:
        # No fijar una versión de chromedriver; dejar que webdriver-manager resuelva
        # la versión compatible con el navegador instalado o la que esté disponible.
        driver_path = ChromeDriverManager().install()
        if not os.path.exists(driver_path):
            raise DriverFatalError(
                f"ChromeDriver no encontrado después de la instalación: {driver_path}"
            )

        if not _is_windows() and driver_path.lower().endswith(".exe"):
            raise DriverFatalError(
                "ChromeDriver resuelto es un ejecutable de Windows en un sistema no Windows. "
                "Verifique que no haya un override manual de chromedriver y que webdriver-manager resuelva la versión correcta."
            )

        _ensure_executable(driver_path)
        service = Service(driver_path)
        options = _crear_opciones(download_dir=download_dir, headless=headless)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(120)
        return driver

    except SessionNotCreatedException as exc:
        mensaje = str(exc)
        chrome_version = obtener_version_chrome()
        chromedriver_version = obtener_version_chromedriver(driver_path) if 'driver_path' in locals() else None
        logger.error(
            "SessionNotCreatedException: chrome=%s chromedriver=%s error=%s",
            chrome_version,
            chromedriver_version,
            mensaje,
        )
        raise DriverFatalError(
            "Incompatibilidad entre la versión de Chrome y ChromeDriver. "
            f"Chrome={chrome_version} ChromeDriver={chromedriver_version}. "
            "Verifique que el navegador y el driver sean compatibles. "
            f"{CHROMEDRIVER_DOWNLOAD_URL}"
        ) from exc

    except WebDriverException as exc:
        if _es_incompatibilidad(exc):
            chrome_version = obtener_version_chrome()
            chromedriver_version = obtener_version_chromedriver(driver_path) if 'driver_path' in locals() else None
            logger.error(
                "Incompatibilidad detectada al iniciar driver: chrome=%s chromedriver=%s error=%s",
                chrome_version,
                chromedriver_version,
                exc,
            )
            raise DriverFatalError(
                "Incompatibilidad entre Chrome y ChromeDriver detectada. "
                f"Chrome={chrome_version} ChromeDriver={chromedriver_version}. "
                f"{CHROMEDRIVER_DOWNLOAD_URL}"
            ) from exc
        raise DriverRetryableError(
            "Error transitorio al iniciar el driver de Selenium.",
        ) from exc

    except Exception as exc:
        logger.exception("Error inesperado creando el Chrome driver")
        raise DriverRetryableError(
            "Error inesperado al crear el driver de Selenium."
        ) from exc


def cerrar_driver(driver: webdriver.Chrome | None) -> None:
    if not driver:
        return
    try:
        driver.quit()
    except WebDriverException as exc:
        logger.warning("Error cerrando el driver de Selenium: %s", exc)


@contextmanager
def driver_context(download_dir: str | None = None, headless: bool = False) -> Iterator[webdriver.Chrome]:
    driver = crear_driver(download_dir=download_dir, headless=headless)
    try:
        yield driver
    finally:
        cerrar_driver(driver)
