#!/usr/bin/env python3
"""
Limpieza del proyecto V2M - Recupera espacio en disco

¿Para qué sirve?
    Con el tiempo, tu proyecto acumula "basura": archivos temporales,
    cache de Python, logs viejos, etc. Este script los limpia de forma
    segura, liberando espacio en disco.

¿Cuánto espacio puedo recuperar?
    Depende, pero típicamente:
    - Cache de Python: 50-200 MB
    - Entorno virtual duplicado (.venv): 2-10 GB (!)
    - Logs antiguos: 10-100 MB

¿Cómo lo uso?
    # Primero, ve qué se eliminaría (sin borrar nada)
    $ python scripts/cleanup.py --dry-run --all

    # Si te parece bien, ejecuta la limpieza real
    $ python scripts/cleanup.py --all

Opciones disponibles:
    --dry-run   No borra nada, solo muestra qué haría
    --all       Limpia todo (recomendado)
    --cache     Solo archivos __pycache__ y .pyc
    --fix-venv  Solo elimina .venv si existe venv (duplicados)
    --logs      Solo logs más viejos de 7 días
    --orphans   Solo archivos huérfanos de pip

¿Es seguro?
    Sí. El script:
    - Nunca borra código fuente
    - Verifica que no estés usando .venv antes de borrarlo
    - Te muestra exactamente qué va a eliminar

    Tip: Siempre corre --dry-run primero si tienes dudas.

Para desarrolladores:
    Este script usa pathlib para manejo de rutas y shutil para
    eliminación recursiva. La clase CleanupStats trackea las
    estadísticas de limpieza para el reporte final.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# Configuración - Puedes ajustar estos valores si lo necesitas
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
VENV_PRIMARY = PROJECT_ROOT / "venv"
VENV_DUPLICATE = PROJECT_ROOT / ".venv"
LOGS_DIR = PROJECT_ROOT / "logs"
LOG_RETENTION_DAYS = 7  # Logs más viejos de esto se eliminan
ORPHAN_FILES = ["=1.0.3", "=4.5.0"]  # Archivos basura que a veces crea pip


class CleanupStats:
    """
    Lleva la cuenta de qué se ha limpiado.

    Básicamente es un contador glorificado que al final te dice:
    "Borraste X archivos y liberaste Y GB".

    Atributos:
        bytes_freed: Bytes totales liberados
        files_deleted: Cantidad de archivos borrados
        dirs_deleted: Cantidad de directorios borrados

    Example:
        >>> stats = CleanupStats()
        >>> stats.add_file(1024)
        >>> stats.add_dir(2048)
        >>> print(f"Espacio liberado: {stats.to_gb():.2f} GB")
        Espacio liberado: 0.00 GB
    """

    def __init__(self) -> None:
        """
        Arranca los contadores en cero.

        Conforme vas borrando cosas, los contadores van subiendo
        para darte un resumen al final de cuánto espacio liberaste.
        """
        self.bytes_freed = 0
        self.files_deleted = 0
        self.dirs_deleted = 0

    def add_file(self, size: int) -> None:
        """
        Suma un archivo eliminado a las estadísticas.

        Args:
            size: Tamaño del archivo en bytes (lo que pesaba antes de borrarlo).
        """
        self.bytes_freed += size
        self.files_deleted += 1

    def add_dir(self, size: int) -> None:
        """
        Suma un directorio eliminado a las estadísticas.

        Args:
            size: Tamaño total del directorio (todo lo que contenía).
        """
        self.bytes_freed += size
        self.dirs_deleted += 1

    def to_gb(self) -> float:
        """
        Te dice cuántos GB liberaste (más fácil de leer que bytes).

        Returns:
            El espacio liberado en gigabytes.
        """
        return self.bytes_freed / (1024**3)

    def report(self) -> None:
        """
        Imprime un resumen bonito de qué se limpió.

        Te muestra archivos y carpetas eliminados, y el espacio
        total que recuperaste. El premio al final de la limpieza.
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
    Calcula cuántos bytes ocupa una carpeta (incluyendo todo adentro).

    Recorre todos los archivos recursivamente y suma sus tamaños.
    Si algo falla (permisos, carpeta no existe), devuelve 0 sin explotar.

    Args:
        path: La carpeta que querés medir.

    Returns:
        El tamaño total en bytes, o 0 si hubo problemas.

    Example:
        >>> size = get_dir_size(Path("./venv"))
        >>> print(f"venv pesa {size / 1024**2:.0f} MB")
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
    Borra todas las carpetas __pycache__ y archivos .pyc/.pyo.

    El cache de Python se acumula con el tiempo y puede ocupar
    bastante espacio. Esta función limpia todo eso.

    Args:
        stats: Donde vamos sumando qué se borró.
        dry_run: Si es True, solo te dice qué borraría pero no toca nada.

    Tip:
        Corré esto periódicamente o antes de hacer commits para
        mantener el repo limpio.
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
    Elimina .venv si ya tenés venv/ en uso (el duplicado).

    A veces quedan dos entornos virtuales (venv/ y .venv/) por
    diferentes instalaciones. Esta función borra el duplicado
    SOLO si verifica que systemd está usando el otro.

    Args:
        stats: Donde vamos sumando qué se borró.
        dry_run: Si es True, solo te dice qué borraría pero no toca nada.

    ⚠️ IMPORTANTE:
        Esta función es paranoica por diseño. Verifica que el servicio
        systemd esté usando venv/ antes de borrar .venv/. Si no puede
        confirmar, no borra nada.
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
    Borra logs viejos que ya no necesitás.

    Los logs se acumulan con el tiempo. Esta función borra los que
    tienen más de X días (por defecto 7). Los recientes se quedan
    por si necesitás debuggear algo.

    Args:
        stats: Donde vamos sumando qué se borró.
        dry_run: Si es True, solo te dice qué borraría pero no toca nada.

    El período de retención está en LOG_RETENTION_DAYS al principio del archivo.
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
    Limpia archivos basura que dejó pip u otras herramientas.

    A veces pip crea archivos con nombres raros como "=1.0.3" por
    bugs en la especificación de dependencias. Esta función conoce
    esos archivos problemáticos y los elimina.

    Args:
        stats: Donde vamos sumando qué se borró.
        dry_run: Si es True, solo te dice qué borraría pero no toca nada.

    Los archivos que busca están en ORPHAN_FILES. Si encontrás
    otros, agregalos ahí.
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
    El punto de entrada. Lee los argumentos y corre las limpiezas.

    Opciones que podés pasar:
        --dry-run   Ver qué se borraría sin tocar nada (siempre corre esto primero!)
        --all       Hacer TODA la limpieza
        --cache     Solo cache de Python
        --fix-venv  Solo el .venv duplicado
        --logs      Solo rotar logs viejos
        --orphans   Solo archivos basura

    Si no pasás ninguna opción, te muestra la ayuda.

    Ejemplo:
        $ python scripts/cleanup.py --dry-run --all   # Ver qué pasaría
        $ python scripts/cleanup.py --all             # Hacer la limpieza
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
