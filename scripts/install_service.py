#!/usr/bin/env python3
"""
Instalar V2M como servicio del sistema

¿Qué hace este script?
    Configura V2M para que arranque automáticamente cuando inicies
    sesión en tu computadora. Ya no tendrás que iniciarlo manualmente.

¿Cómo lo uso?
    $ python scripts/install_service.py

    Eso es todo. El script hace el resto.

¿Qué pasa después de instalarlo?
    - V2M arranca solo cuando inicias sesión
    - Puedes controlarlo con systemctl:

      $ systemctl --user status v2m.service   # Ver si está corriendo
      $ systemctl --user restart v2m.service  # Reiniciarlo
      $ systemctl --user stop v2m.service     # Detenerlo
      $ systemctl --user disable v2m.service  # Desactivar arranque automático

¿Dónde se guarda la configuración?
    ~/.config/systemd/user/v2m.service

¿Por qué "usuario" y no "sistema"?
    Porque V2M necesita acceso a tu display (para el portapapeles)
    y a tu sesión. Los servicios de sistema no tienen eso.

Requisitos previos:
    1. Entorno virtual creado en ./venv
    2. Archivo .env con tu GEMINI_API_KEY
    3. No tener dos entornos virtuales (.venv y venv)

¿Algo salió mal?
    - Si ves errores de CUDA: ./scripts/repair_libs.sh
    - Si hay .venv duplicado: python scripts/cleanup.py --fix-venv
    - Para ver logs: journalctl --user -u v2m.service -f

Para desarrolladores:
    Este script genera dinámicamente el archivo .service detectando
    las rutas de CUDA automáticamente. También configura DISPLAY y
    XAUTHORITY para que el daemon pueda acceder al portapapeles X11.
"""

import os
import sys
from pathlib import Path
import subprocess

# Configuración del servicio
SERVICE_NAME = "v2m.service"

USER_HOME = Path.home()
"""Path: Directorio home del usuario actual."""

SYSTEMD_USER_DIR = USER_HOME / ".config/systemd/user"
"""Path: Directorio para servicios systemd de usuario."""

SOURCE_SERVICE_FILE = Path("v2m.service")
"""Path: Archivo de servicio fuente (si existe)."""


def get_cuda_paths(venv_python: Path) -> str:
    """
    Busca dónde están las librerías CUDA/cuDNN para que el servicio las encuentre.

    Cuando el daemon corre bajo systemd, no tiene acceso al PATH normal,
    así que necesitamos decirle explícitamente dónde encontrar las libs
    de NVIDIA. Esta función las busca en dos lugares:

        1. torch.cuda.lib (para PyTorch 2.9.1+)
        2. Las carpetas nvidia/* dentro del venv

    Args:
        venv_python: La ruta al Python del venv (ej: /home/user/v2m/venv/bin/python)

    Returns:
        Una cadena con las rutas separadas por ":" lista para usar en
        LD_LIBRARY_PATH. Si no encuentra nada, devuelve cadena vacía.

    Example:
        >>> paths = get_cuda_paths(Path("/home/user/v2m/venv/bin/python"))
        >>> # Devuelve algo como: "/home/user/v2m/venv/.../nvidia/cublas/lib:..."
    """
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

def install_service() -> None:
    """
    Hace toda la magia para que V2M corra como servicio systemd.

    Esta función hace un montón de cosas por vos:

        1. Crea la carpeta ~/.config/systemd/user/ si no existe
        2. Verifica que no tengas dos venvs (común después de reinstalar)
        3. Busca las librerías CUDA automáticamente
        4. Genera el archivo v2m.service con toda la config
        5. Le dice a systemd que recargue y habilite el servicio
        6. Reinicia el daemon para aplicar cambios

    Si algo sale mal (venvs duplicados, systemd falla), el script
    explota con un mensaje claro de qué pasó y cómo arreglarlo.

    Nota sobre DISPLAY y XAUTHORITY:
        El servicio necesita acceso al display de X11 para usar xclip
        (copiar al portapapeles). Detectamos esas variables del ambiente
        actual y las hardcodeamos en el servicio.
    """
    print(f"🔧 Instalando {SERVICE_NAME}...")

    # 1. Directorio de destino
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Rutas absolutas
    current_dir = Path.cwd().resolve()
    venv_python = current_dir / "venv/bin/python"

    # 2.1 Validar entornos virtuales duplicados
    venv_duplicate = current_dir / ".venv"
    if venv_duplicate.exists() and (current_dir / "venv").exists():
        print("❌ ERROR: Detectados dos entornos virtuales (.venv y venv)")
        print("   Esto puede causar consumo excesivo de disco (~10GB)")
        print(f"   Ejecuta: python3 scripts/cleanup.py --fix-venv")
        sys.exit(1)

    # 3. Calcular LD_LIBRARY_PATH
    cuda_path = get_cuda_paths(venv_python)
    env_vars = f"Environment=PYTHONPATH={current_dir}/src\n"
    env_vars += f"Environment=PYTHONUNBUFFERED=1\n"

    if cuda_path:
        print(f"✅ Librerías CUDA detectadas: {cuda_path[:50]}...")
        env_vars += f"Environment=LD_LIBRARY_PATH={cuda_path}\n"
    else:
        print("⚠️  Instalando sin soporte explícito de librerías CUDA (podría fallar si usas GPU)")

    # Detección agresiva de DISPLAY para hardcodearlo en el servicio
    display_val = os.environ.get("DISPLAY", ":0") # Default a :0 si no se detecta
    xauth_val = os.environ.get("XAUTHORITY", f"{USER_HOME}/.Xauthority")

    env_vars += f"Environment=DISPLAY={display_val}\n"
    env_vars += f"Environment=XAUTHORITY={xauth_val}\n" # Necesario para xclip/x11 a veces

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
