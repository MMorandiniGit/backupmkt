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
import paramiko

# Configuración del logging
logging.basicConfig(
    filename="backup_router.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Define las variables globales para usuario y contraseña
USERNAME = os.getenv(
    "SSH_USERNAME", ""
)  # Reemplaza con la variable de entorno adecuada
PASSWORD = os.getenv(
    "SSH_PASSWORD", ""
)  # Reemplaza con la variable de entorno adecuada
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
        ssh.connect(ip_address, port=22, username=USERNAME, password=PASSWORD)
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


def descargar_archivo(sftp_client, archivo, backup_path, router_name, current_time):
    """
    Descarga un archivo específico del router y lo guarda en el directorio de respaldo.

    Args:
        sftp_client: Cliente SFTP para la transferencia de archivos.
        archivo (str): Nombre del archivo que se desea descargar.
        backup_path (str): Ruta local donde se guardará el archivo.
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
        sftp_client.get(f"/{archivo}", os.path.join(backup_path, nuevo_nombre_archivo))
        logging.info(
            "Archivo %s descargado correctamente para el router %s.",
            archivo,
            router_name,
        )
    except FileNotFoundError as fnf_error:
        logging.error("Archivo no encontrado: %s", fnf_error)
    except PermissionError as perm_error:
        logging.error("Permiso denegado al descargar archivo: %s", perm_error)
    except paramiko.SSHException as ssh_error:
        logging.error("Error SSH al descargar el archivo %s: %s", archivo, ssh_error)
    except OSError as os_error:
        logging.error("Error de sistema al descargar archivo %s: %s", archivo, os_error)


def descargar_archivos(ssh_client, router_name, backup_path):
    """
    Descarga los archivos 'latest.rsc' y 'latest.backup' del router.

    Args:
        ssh_client: Conexión SSH al router.
        router_name (str): Nombre del router desde el cual se descargan los archivos.
        backup_path (str): Ruta local donde se guardarán los archivos descargados.
    """
    try:
        current_time = time.strftime("%Y%m%d")
        archivos_deseados = ["latest.rsc", "latest.backup"]

        # Obtener la lista de archivos en el directorio remoto
        with ssh_client.open_sftp() as sftp_client:
            archivos_remotos = sftp_client.listdir(".")
            for archivo in archivos_deseados:
                if archivo in archivos_remotos:
                    descargar_archivo(
                        sftp_client, archivo, backup_path, router_name, current_time
                    )
                else:
                    logging.warning(
                        "Archivo %s no encontrado en el router %s.",
                        archivo,
                        router_name,
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


def renombrar_backups_antiguos(backup_path):
    """
    Renombra los archivos de respaldo antiguos agregando el sufijo '-old'.

    Args:
        backup_path (str): Ruta local donde se encuentran los archivos de respaldo.
    """
    ahora = time.time()
    for archivo in os.listdir(backup_path):
        ruta_archivo = os.path.join(backup_path, archivo)
        try:
            if archivo.endswith((".rsc", ".backup")) and not archivo.endswith(
                ("-old.rsc", "-old.backup")
            ):
                fecha_creacion = os.path.getctime(ruta_archivo)
                antiguedad_dias = (ahora - fecha_creacion) / (24 * 3600)
                if antiguedad_dias > DIAS_MAXIMOS:
                    nuevo_nombre = archivo.replace(".rsc", "-old.rsc").replace(
                        ".backup", "-old.backup"
                    )
                    os.rename(ruta_archivo, os.path.join(backup_path, nuevo_nombre))
                    logging.info("Archivo %s renombrado a %s.", archivo, nuevo_nombre)
        except FileNotFoundError as fnf_error:
            logging.error("Archivo no encontrado: %s", fnf_error)
        except PermissionError as perm_error:
            logging.error("Permiso denegado al renombrar archivo: %s", perm_error)
        except OSError as os_error:
            logging.error(
                "Error de sistema al renombrar archivo %s: %s", archivo, os_error
            )


def respaldar_router(ip_address, router_name, backup_path):
    """
    Función que maneja la conexión al router y descarga sus archivos de respaldo.

    Args:
        ip_address (str): Dirección IP del router.
        router_name (str): Nombre del router.
        backup_path (str): Ruta local donde se guardarán los archivos descargados.
    """
    ssh_client = conectar_ssh(ip_address)
    if ssh_client:
        descargar_archivos(ssh_client, router_name, backup_path)


if __name__ == "__main__":
    directorio_actual = os.getcwd()
    ruta_respaldo_principal = directorio_actual

    # Lee la lista de routers a respaldar en el archivo rt.csv
    with open("rt.csv", "r", encoding="utf-8") as f:
        lector_csv = csv.reader(f)
        # Ejecutar hilos de forma controlada con un máximo de 4 hilos simultáneos
        with ThreadPoolExecutor(max_workers=4) as executor:
            for fila in lector_csv:
                ip_router, nombre_router_interno = fila[0], fila[1]
                executor.submit(
                    respaldar_router,
                    ip_router,
                    nombre_router_interno,
                    ruta_respaldo_principal,
                )

    # Renombrar backups con más de 7 días de antigüedad.
    renombrar_backups_antiguos(ruta_respaldo_principal)
