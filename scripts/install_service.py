import os
import sys
from pathlib import Path
import subprocess

SERVICE_NAME = "whisper-dictation.service"
USER_HOME = Path.home()
SYSTEMD_USER_DIR = USER_HOME / ".config/systemd/user"
SOURCE_SERVICE_FILE = Path("whisper-dictation.service")

def get_cuda_paths(venv_python):
    """Calcula LD_LIBRARY_PATH consultando las librerías instaladas en el venv."""
    try:
        # Script inline para preguntar a los paquetes de nvidia dónde están
        cmd = [
            str(venv_python),
            "-c",
            "import nvidia.cublas.lib, nvidia.cudnn.lib, os; "
            "print(os.path.dirname(nvidia.cublas.lib.__file__) + ':' + "
            "os.path.dirname(nvidia.cudnn.lib.__file__))"
        ]
        # Ejecutamos y limpiamos el output
        return subprocess.check_output(cmd, text=True).strip()
    except Exception as e:
        print(f"⚠️  Advertencia: No se pudieron detectar librerías NVIDIA automáticamente: {e}")
        return ""

def install_service():
    print(f"🔧 Instalando {SERVICE_NAME}...")

    # 1. Directorio de destino
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Rutas absolutas
    current_dir = Path.cwd().resolve()
    venv_python = current_dir / "venv/bin/python"

    # 3. Calcular LD_LIBRARY_PATH
    cuda_path = get_cuda_paths(venv_python)
    env_vars = f"Environment=PYTHONUNBUFFERED=1\n"

    if cuda_path:
        print(f"✅ Librerías CUDA detectadas: {cuda_path[:50]}...")
        env_vars += f"Environment=LD_LIBRARY_PATH={cuda_path}\n"
    else:
        print("⚠️  Instalando sin soporte explícito de librerías CUDA (podría fallar si usas GPU)")

    # 4. Contenido del servicio
    service_content = f"""[Unit]
Description=Whisper Dictation Daemon
After=network.target sound.target

[Service]
Type=simple
WorkingDirectory={current_dir}
ExecStart={venv_python} -m whisper_dictation.main --daemon
Restart=on-failure
RestartSec=5
{env_vars}
# Cargar variables (API Key) desde .env
EnvironmentFile={current_dir}/.env

[Install]
WantedBy=default.target
"""

    # 5. Escribir archivo
    dest_file = SYSTEMD_USER_DIR / SERVICE_NAME
    with open(dest_file, "w") as f:
        f.write(service_content)

    print(f"📄 Archivo de servicio escrito en: {dest_file}")

    # 6. Recargar y Habilitar
    print("🔄 Recargando systemd...")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", SERVICE_NAME], check=True)

    # 7. Reiniciar para aplicar cambios
    print("🚀 Reiniciando servicio...")
    subprocess.run(["systemctl", "--user", "restart", SERVICE_NAME], check=True)

    print("\n✅ ¡Instalación Completada! Prueba dictar ahora.")

if __name__ == "__main__":
    install_service()
