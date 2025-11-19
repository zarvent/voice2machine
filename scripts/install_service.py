import os
import sys
from pathlib import Path
import subprocess

SERVICE_NAME = "v2m.service"
USER_HOME = Path.home()
SYSTEMD_USER_DIR = USER_HOME / ".config/systemd/user"
SOURCE_SERVICE_FILE = Path("v2m.service")

def get_cuda_paths(venv_python):
    """Calcula LD_LIBRARY_PATH consultando las librerías instaladas en el venv."""
    paths = []

    # 1. Intenta torch.cuda.lib (torch 2.9.1+)
    try:
        cmd = [
            str(venv_python),
            "-c",
            "import torch.cuda; import os; "
            "cuda_lib_path = os.path.join(os.path.dirname(torch.__file__), 'lib'); "
            "print(cuda_lib_path if os.path.exists(cuda_lib_path) else '')"
        ]
        result = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        if result:
            paths.append(result)
    except Exception:
        pass

    # 2. Buscar nvidia libs directamente en el venv
    venv_dir = Path(venv_python).parent.parent
    nvidia_base = venv_dir / "lib" / "python3.12" / "site-packages" / "nvidia"

    for lib_name in ["cublas", "cudnn"]:
        lib_dir = nvidia_base / lib_name / "lib"
        if lib_dir.exists():
            paths.append(str(lib_dir))

    if paths:
        # Eliminar duplicados manteniendo orden
        unique_paths = []
        for p in paths:
            if p not in unique_paths:
                unique_paths.append(p)
        return ':'.join(unique_paths)

    print("⚠️  Advertencia: No se pudieron detectar librerías NVIDIA automáticamente")
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
    env_vars = f"Environment=PYTHONPATH={current_dir}/src\n"
    env_vars += f"Environment=PYTHONUNBUFFERED=1\n"

    if cuda_path:
        print(f"✅ Librerías CUDA detectadas: {cuda_path[:50]}...")
        env_vars += f"Environment=LD_LIBRARY_PATH={cuda_path}\n"
    else:
        print("⚠️  Instalando sin soporte explícito de librerías CUDA (podría fallar si usas GPU)")

    # 4. Contenido del servicio
    service_content = f"""[Unit]
Description=Voice2Machine Daemon
After=network.target sound.target

[Service]
Type=simple
WorkingDirectory={current_dir}
{env_vars}ExecStart={venv_python} -m v2m.main --daemon
Restart=on-failure
RestartSec=5

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
