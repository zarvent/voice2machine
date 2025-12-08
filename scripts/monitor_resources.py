#!/usr/bin/env python3

# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# voice2machine is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with voice2machine.  If not, see <https://www.gnu.org/licenses/>.
"""
monitoreo de recursos - ¿cuánto consume v2m?

¿para qué sirve?
    te genera un reporte de cuánta memoria gpu y disco está usando
    v2m útil cuando
    - sientes que tu computadora está lenta
    - quieres saber cuánta vram usa el modelo
    - necesitas diagnosticar problemas de rendimiento

¿cómo lo uso?
    # ver el reporte en pantalla
    $ python scripts/monitor_resources.py

    # guardar el reporte a un archivo
    $ python scripts/monitor_resources.py --save mi-reporte.md

¿qué incluye el reporte?
    - procesos v2m activos
    - memoria del daemon
    - uso de gpu (vram utilización)
    - espacio en disco por directorio
    - cantidad de archivos de cache

¿cuántos recursos debería usar v2m?
    valores típicos
    - memoria daemon 200-500 mb (sin modelo cargado)
    - vram con modelo large-v2 ~5-6 gb
    - disco total del proyecto 3-5 gb

¿qué hago si consume demasiado?
    1 limpia el cache python scripts/cleanup.py --all
    2 revisa si hay .venv duplicado (puede ser ~10 gb extra)
    3 reinicia el daemon ./scripts/v2m-daemon.sh restart

para desarrolladores
    el script usa subprocesos para llamar a nvidia-smi ps du etc
    si nvidia-smi no está disponible simplemente omite esa sección
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Rutas del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.resolve() / "apps" / "backend"
VENV_DIR = PROJECT_ROOT / "venv"
LOGS_DIR = PROJECT_ROOT / "logs"
"""Path: Directorio de archivos de log."""


def get_process_info() -> None:
    """
    te muestra qué procesos de v2m están corriendo ahora mismo

    básicamente hace un `ps aux | grep v2m` pero más bonito
    útil para verificar que el daemon esté vivo y ver cuánto
    cpu está usando

    si no aparece ningún proceso el daemon probablemente esté
    apagado o hubo algún crash
    """
    print("## PROCESOS V2M / V2M PROCESSES\n")

    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=True
        )

        # Filtrar procesos relacionados con V2M
        v2m_processes = [line for line in result.stdout.split('\n')
                         if 'v2m' in line.lower() and 'grep' not in line]

        if v2m_processes:
            print("```")
            print(result.stdout.split('\n')[0])  # Header
            for proc in v2m_processes:
                print(proc)
            print("```\n")
        else:
            print("⚠️  No se encontraron procesos V2M activos\n")

    except Exception as e:
        print(f"❌ Error obteniendo procesos: {e}\n")


def get_daemon_memory() -> None:
    """
    consulta cuánta memoria ram está usando el daemon

    le pregunta a systemd cuál es el pid del servicio v2m.service
    y extrae el dato de memoria de ahí es la forma más precisa
    de saber si el daemon está consumiendo mucha ram

    tip
        si ves que la memoria sigue creciendo con el tiempo
        podría haber un memory leak avisanos si pasa
    """
    print("## MEMORIA DEL DAEMON / DAEMON MEMORY\n")

    try:
        # Obtener PID del daemon desde systemd
        result = subprocess.run(
            ["systemctl", "--user", "show", "v2m.service", "-p", "MainPID"],
            capture_output=True,
            text=True,
            check=True
        )

        pid = result.stdout.split('=')[1].strip()

        if pid == "0":
            print("⚠️  Daemon no está corriendo\n")
            return

        # Obtener memoria del proceso
        status_result = subprocess.run(
            ["systemctl", "--user", "status", "v2m.service", "--no-pager"],
            capture_output=True,
            text=True,
            check=False
        )

        # Extraer línea de Memory
        for line in status_result.stdout.split('\n'):
            if 'Memory:' in line:
                print(f"**PID**: {pid}")
                print(f"**{line.strip()}**\n")
                break

    except Exception as e:
        print(f"❌ Error obteniendo memoria del daemon: {e}\n")


def get_gpu_usage() -> None:
    """
    muestra cuánto de tu gpu nvidia está usando v2m

    usa nvidia-smi (la herramienta oficial de nvidia) para mostrarte
        - qué gpu tenés
        - cuánta vram está en uso (whisper puede comer bastante)
        - el porcentaje de utilización del gpu

    si no tenés gpu nvidia o nvidia-smi no está instalado
    simplemente te avisa y sigue adelante sin explotar
    """
    print("## USO DE GPU / GPU USAGE\n")

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True
        )

        gpu_info = result.stdout.strip().split(', ')

        print(f"**GPU**: {gpu_info[0]}")
        print(f"**VRAM**: {gpu_info[1]} MB / {gpu_info[2]} MB ({int(gpu_info[1])/int(gpu_info[2])*100:.1f}%)")
        print(f"**Utilización**: {gpu_info[3]}%\n")

    except FileNotFoundError:
        print("⚠️  nvidia-smi no disponible (GPU no detectada)\n")
    except Exception as e:
        print(f"❌ Error obteniendo info de GPU: {e}\n")


def get_disk_usage() -> None:
    """
    te muestra qué carpetas del proyecto ocupan más espacio

    corre `du` por debajo para calcular el tamaño de cada
    subcarpeta y te muestra las 10 más gordas útil para
    encontrar qué está llenando tu disco

    spoiler casi siempre es venv/ o algún cache
    """
    print("## USO DE DISCO / DISK USAGE\n")

    try:
        result = subprocess.run(
            ["du", "-sh", str(PROJECT_ROOT / "*")],
            capture_output=True,
            text=True,
            shell=True,
            check=False
        )

        lines = result.stdout.strip().split('\n')
        sorted_lines = sorted(lines, key=lambda x: x.split()[0], reverse=True)

        print("```")
        for line in sorted_lines[:10]:  # Top 10
            print(line)
        print("```\n")

        # Tamaño total
        total_result = subprocess.run(
            ["du", "-sh", str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            check=True
        )

        print(f"**TOTAL**: {total_result.stdout.split()[0]}\n")

    except Exception as e:
        print(f"❌ Error obteniendo uso de disco: {e}\n")


def check_cache_bloat() -> None:
    """
    revisa si hay demasiado cache de python acumulado

    cuenta los directorios __pycache__ y archivos .pyc si hay
    una cantidad ridiculosa (más de 100 dirs o 1000 archivos)
    te avisa que es hora de una limpieza

    no borra nada automáticamente solo te dice qué encontró
    para limpiar corré python scripts/cleanup.py --cache
    """
    print("## CACHE PYTHON / PYTHON CACHE\n")

    try:
        pycache_result = subprocess.run(
            ["find", str(PROJECT_ROOT), "-type", "d", "-name", "__pycache__"],
            capture_output=True,
            text=True,
            check=True
        )

        pyc_result = subprocess.run(
            ["find", str(PROJECT_ROOT), "-name", "*.pyc"],
            capture_output=True,
            text=True,
            check=True
        )

        pycache_count = len([l for l in pycache_result.stdout.strip().split('\n') if l])
        pyc_count = len([l for l in pyc_result.stdout.strip().split('\n') if l])

        print(f"**Directorios `__pycache__`**: {pycache_count}")
        print(f"**Archivos `.pyc`**: {pyc_count}")

        if pycache_count > 100 or pyc_count > 1000:
            print("\n⚠️  **ADVERTENCIA**: Cache excesivo detectado")
            print(f"   Ejecuta: `python3 scripts/cleanup.py --cache`\n")
        else:
            print("\n✓ Cache dentro de límites normales\n")

    except Exception as e:
        print(f"❌ Error contando cache: {e}\n")


def generate_report() -> None:
    """
    genera un reporte completo de recursos en formato markdown

    ejecuta todas las funciones de diagnóstico y muestra el resultado
    en un formato estructurado con secciones para cada tipo de recurso
    al final incluye una sección de acciones recomendadas

    secciones del reporte
        1 procesos v2m activos
        2 memoria del daemon
        3 uso de gpu
        4 uso de disco
        5 cache python
        6 acciones recomendadas
    """
    print("\n" + "="*70)
    print(f"# REPORTE DE RECURSOS V2M / V2M RESOURCE REPORT")
    print(f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    get_process_info()
    get_daemon_memory()
    get_gpu_usage()
    get_disk_usage()
    check_cache_bloat()

    print("="*70)
    print("## ACCIONES RECOMENDADAS / RECOMMENDED ACTIONS\n")
    print("- **Limpieza completa**: `python3 scripts/cleanup.py --all`")
    print("- **Solo cache**: `python3 scripts/cleanup.py --cache`")
    print("- **Reiniciar daemon**: `systemctl --user restart v2m.service`")
    print("- **Ver logs**: `journalctl --user -u v2m.service -n 50`")
    print("="*70 + "\n")


def main() -> None:
    """
    punto de entrada principal del script de monitoreo

    procesa los argumentos de línea de comandos y genera el reporte
    de recursos puede mostrar el reporte en pantalla o guardarlo
    en un archivo markdown

    opciones de línea de comandos
        --save FILE guarda el reporte en el archivo especificado
                    en lugar de mostrarlo en pantalla

    example
        >>> # desde línea de comandos
        >>> # python scripts/monitor_resources.py
        >>> # python scripts/monitor_resources.py --save status.md
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitoreo de recursos del proyecto V2M"
    )

    parser.add_argument("--save", type=str, metavar="FILE",
                       help="Guardar reporte en archivo markdown")

    args = parser.parse_args()

    if args.save:
        # Redirigir stdout a archivo
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            generate_report()

        output = f.getvalue()

        with open(args.save, 'w') as out:
            out.write(output)

        print(f"✓ Reporte guardado en: {args.save}")
    else:
        generate_report()


if __name__ == "__main__":
    main()
