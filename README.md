
# Backup Router Script 🖥️📂

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![SSH](https://img.shields.io/badge/SSH-Paramiko-yellow.svg)](http://www.paramiko.org/)

## Descripción del Proyecto 🚀

Este proyecto es un script en Python que automatiza la **copia de seguridad** de archivos de configuración de routers mediante **conexiones SSH**. El script se conecta a una lista de routers, descarga archivos específicos, y renombra los respaldos antiguos. Se ejecuta utilizando múltiples hilos para optimizar el tiempo de ejecución y gestiona conexiones SSH de manera segura.

## Características 🛠️

- 📂 **Descarga automática** de archivos de configuración (`.rsc` y `.backup`) desde routers.
- 🔒 **Conexión SSH segura** utilizando la biblioteca **Paramiko**.
- 🧵 **Uso de múltiples hilos** para respaldar varios routers simultáneamente.
- ⏳ **Renombra archivos antiguos** agregando un sufijo `-old` después de un tiempo especificado.
- 📝 **Registro detallado** de las actividades y errores mediante el sistema de logs de Python.

## Estructura del Código 📝

El código se organiza en varias funciones que realizan las tareas de conexión, descarga, y administración de archivos de respaldo.

### Funciones Principales

1. **`conectar_ssh(ip_address)`**:
   - Establece una conexión SSH segura con el router en la dirección IP especificada.
   - Utiliza el usuario y la contraseña proporcionados como variables de entorno para mayor seguridad.

2. **`descargar_archivo(sftp_client, archivo, backup_path, router_name, current_time)`**:
   - Descarga un archivo específico desde el router y lo guarda en el directorio local con un nuevo nombre basado en el nombre del router y la fecha actual.

3. **`descargar_archivos(ssh_client, router_name, backup_path)`**:
   - Utiliza el cliente SSH para obtener una lista de archivos en el router y descarga aquellos que coincidan con los nombres `latest.rsc` o `latest.backup`.

4. **`renombrar_backups_antiguos(backup_path)`**:
   - Renombra los archivos de respaldo que sean más antiguos que el número de días especificado (`DIAS_MAXIMOS`), agregando el sufijo `-old`.

5. **`respaldar_router(ip_address, router_name, backup_path)`**:
   - Función que combina la conexión SSH y la descarga de archivos para un router específico. Se ejecuta en un hilo separado para permitir respaldos concurrentes.

## Requisitos del Sistema ⚙️

- **Python 3.7+**
- **Paramiko**: Se utiliza para gestionar las conexiones SSH.

Puedes instalar las dependencias ejecutando el siguiente comando:

```bash
pip install paramiko
```

## Uso 🖥️

### 1. Clona este repositorio

```bash
git clone [https://github.com/tu_usuario/tu_repositorio.git](https://github.com/MMorandiniGit/backupmkt)]
cd backupmkt
```

### 2. Configura tus credenciales SSH

Asegúrate de tener las variables de entorno `SSH_USERNAME` y `SSH_PASSWORD` configuradas:

```bash
export SSH_USERNAME="nombre_de_usuario"
export SSH_PASSWORD="tu_contraseña_secreta"
```

### 3. Crea un archivo `rt.csv`

El archivo `rt.csv` debe contener la lista de routers a los cuales deseas conectarte, en el siguiente formato:

```csv
192.168.1.1,Router1
192.168.1.2,Router2
```

### 4. Ejecuta el Script

Para ejecutar el script y realizar los respaldos, utiliza:

```bash
python backup_mkt_fin.py
```

El script comenzará a conectarse a los routers y descargará los archivos de configuración, registrando el progreso en un archivo de log (`backup_router.log`).

## Licencia 📄

Este proyecto está licenciado bajo los términos de la licencia MIT. Consulta el archivo [LICENSE](LICENSE) para obtener más información.

---

Hecho por [Martin Morandini](https://github.com/MMorandiniGit)

