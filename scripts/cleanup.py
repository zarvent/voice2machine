#!/usr/bin/env python3
"""
Script de limpieza automática para el proyecto Voice2Machine (V2M).

Este módulo proporciona funcionalidades para mantener limpio el proyecto,
eliminando archivos temporales, cache de Python, entornos virtuales
duplicados, logs antiguos y archivos huérfanos.

Características principales:
    - Limpieza de cache Python (__pycache__, .pyc, .pyo)
    - Eliminación de entornos virtuales duplicados (.venv vs venv)
    - Rotación de logs antiguos (configurable, por defecto 7 días)
    - Eliminación de archivos huérfanos generados por pip

Ejemplo de uso:
    $ python scripts/cleanup.py --dry-run    # Ver qué se eliminaría
    $ python scripts/cleanup.py --all        # Limpieza completa
    $ python scripts/cleanup.py --cache      # Solo cache Python
    $ python scripts/cleanup.py --fix-venv   # Solo .venv duplicado

Dependencias:
    - pathlib: Para manejo de rutas de archivos.
    - shutil: Para eliminación recursiva de directorios.
    - subprocess: Para verificar configuración de systemd.

Notas:
    El script verifica que el venv primario esté en uso por systemd
    antes de eliminar el .venv duplicado, por seguridad.

Author:
    Voice2Machine Team

Since:
    v1.0.0
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# CONFIGURACIÓN / CONFIGURATION
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
VENV_PRIMARY = PROJECT_ROOT / "venv"
VENV_DUPLICATE = PROJECT_ROOT / ".venv"
LOGS_DIR = PROJECT_ROOT / "logs"
LOG_RETENTION_DAYS = 7
ORPHAN_FILES = ["=1.0.3", "=4.5.0"]

class CleanupStats:
    """
    Clase para rastrear estadísticas de operaciones de limpieza.

    Esta clase mantiene un registro del espacio liberado y la cantidad
    de archivos y directorios eliminados durante las operaciones de limpieza.

    Attributes:
        bytes_freed (int): Total de bytes liberados durante la limpieza.
        files_deleted (int): Número total de archivos eliminados.
        dirs_deleted (int): Número total de directorios eliminados.

    Example:
        >>> stats = CleanupStats()
        >>> stats.add_file(1024)
        >>> stats.add_dir(2048)
        >>> print(f"Espacio liberado: {stats.to_gb():.2f} GB")
        Espacio liberado: 0.00 GB
    """

    def __init__(self) -> None:
        """
        Inicializa las estadísticas de limpieza en cero.

        Todos los contadores comienzan en 0 y se van incrementando
        conforme se realizan las operaciones de limpieza.
        """
        self.bytes_freed = 0
        self.files_deleted = 0
        self.dirs_deleted = 0

    def add_file(self, size: int):-> None:
        """
        Registra la eliminación de un archivo.

        Args:
            size: Tamaño del archivo eliminado en bytes.
        """
        self.bytes_freed += size
        self.files_deleted += 1

    def add_dir(self, size: int) -> None:
        """
        Registra la eliminación de un directorio.

        Args:
            size: Tamaño total del directorio eliminado en bytes.
        """
        self.bytes_freed += size
        self.dirs_deleted += 1

    def to_gb(self) -> float:
        """
        Convierte los bytes liberados a gigabytes.

        Returns:
            float: Espacio liberado expresado en gigabytes.
        """
        return self.bytes_freed / (1024**3)

    def report(self) -> None:-> None:
        """
        Muestra un reporte formateado de las estadísticas de limpieza.

        Imprime en consola un resumen visual con el número de archivos
        y directorios eliminados, así como el espacio total liberado
        en gigabytes.
        """
        print(f"\n{'='*60}")
        print(f"📊 REPORTE DE LIMPIEZA / CLEANUP REPORT")
        print(f"{'='*60}")
        print(f"Archivos eliminados: {self.files_deleted}")
        print(f"Directorios eliminados: {self.dirs_deleted}")
        print(f"Espacio liberado: {self.to_gb():.2f} GB")
        print(f"{'='*60}\n")


def get_dir_size(path: Path) -> int:
    """
    Calcula el tamaño total de un directorio recursivamente.

    Recorre todos los archivos dentro del directorio especificado
    y suma sus tamaños para obtener el tamaño total.

    Args:
        path: Ruta al directorio cuyo tamaño se desea calcular.

    Returns:
        int: Tamaño total del directorio en bytes. Retorna 0 si
             el directorio no existe o no se puede acceder.

    Example:
        >>> from pathlib import Path
        >>> size = get_dir_size(Path("/home/user/proyecto"))
        >>> print(f"Tamaño: {size / 1024**2:.2f} MB")
    """
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except (PermissionError, OSError):
        pass
    return total


def clean_pycache(stats: CleanupStats, dry_run: bool = False) -> None:
    """
    Elimina todos los directorios __pycache__ y archivos .pyc/.pyo.

    Busca recursivamente en el proyecto todos los artefactos de cache
    de Python y los elimina para liberar espacio en disco.

    Args:
        stats: Objeto CleanupStats para registrar las estadísticas
               de los archivos y directorios eliminados.
        dry_run: Si es True, solo muestra qué se eliminaría sin
                 hacer cambios reales. Por defecto es False.

    Note:
        Los errores de permisos o acceso se muestran como advertencias
        pero no detienen la ejecución del script.
    """
    print("🧹 Limpiando cache de Python...")

    pycache_dirs = list(PROJECT_ROOT.rglob("__pycache__"))
    pyc_files = list(PROJECT_ROOT.rglob("*.pyc"))
    pyo_files = list(PROJECT_ROOT.rglob("*.pyo"))

    total_items = len(pycache_dirs) + len(pyc_files) + len(pyo_files)

    if total_items == 0:
        print("   ✓ No hay cache Python para eliminar")
        return

    print(f"   → Encontrados {len(pycache_dirs)} dirs __pycache__, {len(pyc_files)} .pyc, {len(pyo_files)} .pyo")

    if dry_run:
        print(f"   [DRY-RUN] Se eliminarían {total_items} items")
        return

    # Eliminar directorios __pycache__
    for pycache in pycache_dirs:
        size = get_dir_size(pycache)
        try:
            shutil.rmtree(pycache)
            stats.add_dir(size)
        except Exception as e:
            print(f"   ⚠️  Error eliminando {pycache}: {e}")

    # Eliminar archivos .pyc y .pyo
    for pyc in pyc_files + pyo_files:
        try:
            size = pyc.stat().st_size
            pyc.unlink()
            stats.add_file(size)
        except Exception as e:
            print(f"   ⚠️  Error eliminando {pyc}: {e}")

    print(f"   ✓ Cache Python eliminado: {stats.dirs_deleted} dirs, {stats.files_deleted} archivos")


def clean_duplicate_venv(stats: CleanupStats, dry_run: bool = False) -> None:
    """
    Elimina el entorno virtual duplicado .venv si venv está en uso.

    Verifica que el entorno virtual primario (venv/) esté siendo
    utilizado por el servicio systemd antes de eliminar el duplicado
    (.venv/) para evitar eliminar accidentalmente el entorno activo.

    Args:
        stats: Objeto CleanupStats para registrar las estadísticas
               del directorio eliminado.
        dry_run: Si es True, solo muestra qué se eliminaría sin
                 hacer cambios reales. Por defecto es False.

    Warning:
        Esta función verifica la configuración de systemd antes de
        eliminar. Si no puede verificar o el venv primario no está
        en uso, no elimina nada por seguridad.
    """
    print("\n🔧 Validando entornos virtuales...")

    if not VENV_DUPLICATE.exists():
        print("   ✓ No existe .venv duplicado")
        return

    if not VENV_PRIMARY.exists():
        print("   ⚠️  ADVERTENCIA: venv primario no existe, conservando .venv")
        return

    # Verificar que venv está en uso por systemd
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "v2m.service", "-p", "ExecStart"],
            capture_output=True,
            text=True,
            check=False
        )
        if str(VENV_PRIMARY) not in result.stdout:
            print(f"   ⚠️  ADVERTENCIA: v2m.service no usa {VENV_PRIMARY}")
            print(f"      Saltando eliminación de .venv por seguridad")
            return
    except Exception as e:
        print(f"   ⚠️  No se pudo verificar systemd service: {e}")
        print(f"      Saltando eliminación de .venv por seguridad")
        return

    size = get_dir_size(VENV_DUPLICATE)
    size_gb = size / (1024**3)

    print(f"   → .venv duplicado encontrado: {size_gb:.2f} GB")

    if dry_run:
        print(f"   [DRY-RUN] Se eliminaría .venv ({size_gb:.2f} GB)")
        return

    try:
        shutil.rmtree(VENV_DUPLICATE)
        stats.add_dir(size)
        print(f"   ✓ .venv eliminado: {size_gb:.2f} GB liberados")
    except Exception as e:
        print(f"   ❌ Error eliminando .venv: {e}")


def rotate_logs(stats: CleanupStats, dry_run: bool = False) -> None:
    """
    Elimina archivos de log más antiguos que el período de retención.

    Busca en el directorio de logs todos los archivos .log cuya fecha
    de modificación sea anterior al período de retención configurado
    (por defecto 7 días) y los elimina.

    Args:
        stats: Objeto CleanupStats para registrar las estadísticas
               de los archivos eliminados.
        dry_run: Si es True, solo muestra qué se eliminaría sin
                 hacer cambios reales. Por defecto es False.

    Note:
        El período de retención está definido por la constante
        LOG_RETENTION_DAYS al inicio del módulo.
    """
    print(f"\n📋 Rotando logs (retención: {LOG_RETENTION_DAYS} días)...")

    if not LOGS_DIR.exists():
        print("   ✓ Directorio de logs no existe")
        return

    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    old_logs = []

    for log_file in LOGS_DIR.glob("*.log"):
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff_date:
            old_logs.append(log_file)

    if not old_logs:
        print("   ✓ No hay logs antiguos para eliminar")
        return

    print(f"   → Encontrados {len(old_logs)} logs antiguos")

    if dry_run:
        for log in old_logs:
            print(f"   [DRY-RUN] Se eliminaría: {log.name}")
        return

    for log in old_logs:
        try:
            size = log.stat().st_size
            log.unlink()
            stats.add_file(size)
            print(f"   ✓ Eliminado: {log.name}")
        except Exception as e:
            print(f"   ⚠️  Error eliminando {log.name}: {e}")


def remove_orphans(stats: CleanupStats, dry_run: bool = False) -> None:
    """
    Elimina archivos huérfanos conocidos del proyecto.

    Busca y elimina archivos que fueron creados erróneamente por
    pip u otras herramientas. Los nombres de archivos huérfanos
    están definidos en la constante ORPHAN_FILES.

    Args:
        stats: Objeto CleanupStats para registrar las estadísticas
               de los archivos eliminados.
        dry_run: Si es True, solo muestra qué se eliminaría sin
                 hacer cambios reales. Por defecto es False.

    Example:
        Archivos huérfanos típicos incluyen:
        - "=1.0.3": Generado por instalaciones pip incorrectas
        - "=4.5.0": Residuos de dependencias mal especificadas
    """
    print("\n🗑️  Eliminando archivos huérfanos...")

    found_orphans = []
    for orphan in ORPHAN_FILES:
        orphan_path = PROJECT_ROOT / orphan
        if orphan_path.exists():
            found_orphans.append(orphan_path)

    if not found_orphans:
        print("   ✓ No hay archivos huérfanos")
        return

    print(f"   → Encontrados {len(found_orphans)} archivos huérfanos")

    for orphan in found_orphans:
        size = orphan.stat().st_size if orphan.is_file() else get_dir_size(orphan)

        if dry_run:
            print(f"   [DRY-RUN] Se eliminaría: {orphan.name}")
            continue

        try:
            if orphan.is_file():
                orphan.unlink()
                stats.add_file(size)
            else:
                shutil.rmtree(orphan)
                stats.add_dir(size)
            print(f"   ✓ Eliminado: {orphan.name}")
        except Exception as e:
            print(f"   ⚠️  Error eliminando {orphan.name}: {e}")


def main() -> None:
    """
    Punto de entrada principal del script de limpieza.

    Procesa los argumentos de línea de comandos y ejecuta las
    operaciones de limpieza correspondientes según las opciones
    especificadas por el usuario.

    Opciones disponibles:
        --dry-run: Mostrar qué se eliminaría sin hacer cambios.
        --all: Ejecutar todas las operaciones de limpieza.
        --cache: Limpiar solo cache Python.
        --fix-venv: Eliminar solo .venv duplicado.
        --logs: Rotar solo logs antiguos.
        --orphans: Eliminar solo archivos huérfanos.

    Example:
        >>> # Desde línea de comandos:
        >>> # python scripts/cleanup.py --all
        >>> # python scripts/cleanup.py --dry-run --cache
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Script de limpieza automática para V2M",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 scripts/cleanup.py --dry-run    # Ver qué se eliminaría
  python3 scripts/cleanup.py --all        # Limpieza completa
  python3 scripts/cleanup.py --cache      # Solo cache Python
  python3 scripts/cleanup.py --fix-venv   # Solo .venv duplicado
        """
    )

    parser.add_argument("--dry-run", action="store_true",
                       help="Mostrar qué se eliminaría sin hacer cambios")
    parser.add_argument("--all", action="store_true",
                       help="Ejecutar todas las operaciones de limpieza")
    parser.add_argument("--cache", action="store_true",
                       help="Limpiar solo cache Python (__pycache__, .pyc)")
    parser.add_argument("--fix-venv", action="store_true",
                       help="Eliminar solo .venv duplicado")
    parser.add_argument("--logs", action="store_true",
                       help="Rotar solo logs antiguos")
    parser.add_argument("--orphans", action="store_true",
                       help="Eliminar solo archivos huérfanos")

    args = parser.parse_args()

    # Si no se especifica nada, mostrar ayuda
    if not any([args.all, args.cache, args.fix_venv, args.logs, args.orphans]):
        parser.print_help()
        return

    stats = CleanupStats()

    print("\n" + "="*60)
    print("🧹 LIMPIEZA V2M / V2M CLEANUP")
    if args.dry_run:
        print("   [MODO DRY-RUN - NO SE HARÁN CAMBIOS]")
    print("="*60 + "\n")

    # Ejecutar operaciones seleccionadas
    if args.all or args.cache:
        clean_pycache(stats, args.dry_run)

    if args.all or args.fix_venv:
        clean_duplicate_venv(stats, args.dry_run)

    if args.all or args.logs:
        rotate_logs(stats, args.dry_run)

    if args.all or args.orphans:
        remove_orphans(stats, args.dry_run)

    # Reporte final
    if not args.dry_run:
        stats.report()
    else:
        print("\n[DRY-RUN] Ejecuta sin --dry-run para aplicar cambios\n")


if __name__ == "__main__":
    main()
