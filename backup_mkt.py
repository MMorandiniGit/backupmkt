"""
Este módulo realiza la copia de seguridad de los routers
usando SSH para descargar archivos de configuración y renombrar
respaldos antiguos. Utiliza múltiples hilos para optimizar el proceso de descarga.
"""

import csv
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependencia opcional
    load_dotenv = lambda: None

import paramiko

# Configuración del logging
logging.basicConfig(
    filename="backup_router.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

# Define las variables globales para usuario y contraseña
USERNAME = os.getenv("SSH_USERNAME", "")
PASSWORD = os.getenv("SSH_PASSWORD", "")
DIAS_MAXIMOS = 6  # Número de días tras los cuales un respaldo se considera antiguo


def conectar_ssh(ip_address):
    """
    Crea una conexión SSH al router.

    Args:
        ip_address (str): La dirección IP del router al que conectarse.

    Returns:
        ssh: Un objeto de conexión SSH si la conexión es exitosa, de lo contrario None.
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            ip_address,
            port=22,
            username=USERNAME,
            password=PASSWORD,
            timeout=10,
        )
        return ssh
    except paramiko.AuthenticationException:
        logging.error("Error de autenticación al conectar al router %s", ip_address)
    except paramiko.SSHException as ssh_exception:
        logging.error(
            "Error SSH al conectar al router %s: %s", ip_address, ssh_exception
        )
    except OSError as os_error:
        logging.error(
            "Error de sistema al conectar al router %s: %s", ip_address, os_error
        )
    return None


def descargar_archivo(sftp_client, archivo, backup_path: Path, router_name, current_time):
    """
    Descarga un archivo específico del router y lo guarda en el directorio de respaldo.

    Args:
        sftp_client: Cliente SFTP para la transferencia de archivos.
        archivo (str): Nombre del archivo que se desea descargar.
        backup_path (Path): Ruta local donde se guardará el archivo.
        router_name (str): Nombre del router desde el cual se descarga el archivo.
        current_time (str): Cadena de tiempo actual utilizada para nombrar el archivo descargado.

    Raises:
        FileNotFoundError: Si el archivo no se encuentra en el servidor.
        PermissionError: Si hay problemas de permisos al intentar descargar el archivo.
        paramiko.SSHException: Si hay un error en la conexión SSH.
        OSError: Si hay un error en el sistema operativo.
    """
    try:
        nuevo_nombre_archivo = f"{router_name}_{current_time}_{archivo}"
        destino = backup_path / nuevo_nombre_archivo
        sftp_client.get(archivo, str(destino))
        logging.info(
            "Archivo %s descargado correctamente para el router %s.",
            archivo,
            router_name,
        )
    except FileNotFoundError:
        logging.warning("Archivo %s no encontrado en el servidor", archivo)
    except PermissionError as perm_error:
        logging.error("Permiso denegado al descargar archivo: %s", perm_error)
    except paramiko.SSHException:
        logging.exception("Error SSH al descargar el archivo %s", archivo)
    except OSError:
        logging.exception("Error de sistema al descargar archivo %s", archivo)


def descargar_archivos(ssh_client, router_name, backup_path: Path):
    """
    Descarga los archivos 'latest.rsc' y 'latest.backup' del router.

    Args:
        ssh_client: Conexión SSH al router.
        router_name (str): Nombre del router desde el cual se descargan los archivos.
        backup_path (Path): Ruta local donde se guardarán los archivos descargados.
    """
    try:
        current_time = time.strftime("%Y%m%d")
        archivos_deseados = ["latest.rsc", "latest.backup"]

        with ssh_client.open_sftp() as sftp_client:
            for archivo in archivos_deseados:
                descargar_archivo(
                    sftp_client, archivo, backup_path, router_name, current_time
                )

    except paramiko.SSHException as e:
        logging.error(
            "Error de conexión SSH al descargar archivos para el router %s: %s",
            router_name,
            e,
        )
    except OSError as os_error:
        logging.error(
            "Error de sistema al descargar archivos para el router %s: %s",
            router_name,
            os_error,
        )
    finally:
        if ssh_client:
            ssh_client.close()


def renombrar_backups_antiguos(backup_path: Path):
    """
    Renombra los archivos de respaldo antiguos agregando el sufijo '-old'.

    Args:
        backup_path (Path): Ruta local donde se encuentran los archivos de respaldo.
    """
    ahora = time.time()
    for ruta_archivo in backup_path.iterdir():
        archivo = ruta_archivo.name
        try:
            if ruta_archivo.suffix in {".rsc", ".backup"} and not archivo.endswith(
                "-old" + ruta_archivo.suffix
            ):
                fecha_creacion = ruta_archivo.stat().st_mtime
                antiguedad_dias = (ahora - fecha_creacion) / (24 * 3600)
                if antiguedad_dias > DIAS_MAXIMOS:
                    nuevo_nombre = ruta_archivo.with_name(
                        f"{ruta_archivo.stem}-old{ruta_archivo.suffix}"
                    )
                    ruta_archivo.rename(nuevo_nombre)
                    logging.info(
                        "Archivo %s renombrado a %s.", archivo, nuevo_nombre.name
                    )
        except FileNotFoundError as fnf_error:
            logging.error("Archivo no encontrado: %s", fnf_error)
        except PermissionError as perm_error:
            logging.error("Permiso denegado al renombrar archivo: %s", perm_error)
        except OSError:
            logging.exception(
                "Error de sistema al renombrar archivo %s", archivo
            )


def respaldar_router(ip_address, router_name, backup_path):
    """
    Función que maneja la conexión al router y descarga sus archivos de respaldo.

    Args:
        ip_address (str): Dirección IP del router.
        router_name (str): Nombre del router.
        backup_path (Path): Ruta local donde se guardarán los archivos descargados.
    """
    ssh_client = conectar_ssh(ip_address)
    if ssh_client:
        descargar_archivos(ssh_client, router_name, backup_path)
    else:
        logging.error("No se pudo establecer conexión con el router %s", router_name)


if __name__ == "__main__":
    ruta_respaldo_principal = Path.cwd()
    max_workers = int(os.getenv("MAX_WORKERS", "4"))

    try:
        with open("rt.csv", "r", encoding="utf-8") as f:
            lector_csv = csv.reader(f)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for fila in lector_csv:
                    if not fila:
                        continue
                    ip_router, nombre_router_interno = fila[0], fila[1]
                    executor.submit(
                        respaldar_router,
                        ip_router,
                        nombre_router_interno,
                        ruta_respaldo_principal,
                    )
    except FileNotFoundError:
        logging.error("Archivo rt.csv no encontrado.")

    renombrar_backups_antiguos(ruta_respaldo_principal)
