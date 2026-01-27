#!/usr/bin/env python3

"""
Health check para procesos v2m.

Detecta procesos zombie que consumen VRAM y los elimina automáticamente.
También verifica el estado del daemon via HTTP y proporciona métricas de sistema.

Uso:
    python scripts/health_check.py [--kill-zombies] [--restart-daemon]
"""

import sys
import argparse
import subprocess
import urllib.request
import json
from pathlib import Path
from typing import List, Tuple

import psutil

# Colores ANSI
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

DEFAULT_PORT = 8765

def get_v2m_processes() -> List[psutil.Process]:
    """Encuentra todos los procesos relacionados con v2m."""
    v2m_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'v2m' in cmdline and 'health_check' not in cmdline:
                v2m_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return v2m_procs


def get_gpu_memory() -> Tuple[int, int]:
    """Obtiene memoria GPU usada y libre en MiB."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used,memory.free', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            check=True
        )
        used, free = map(int, result.stdout.strip().split(','))
        return used, free
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return 0, 0


def is_daemon_responsive() -> bool:
    """Verifica si el daemon responde a HTTP GET /health."""
    try:
        url = f"http://127.0.0.1:{DEFAULT_PORT}/health"
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data.get("status") == "ok"
    except Exception:
        pass
    return False


def kill_zombies(procs: List[psutil.Process]) -> int:
    """Mata procesos zombie y retorna cuántos fueron eliminados."""
    killed = 0
    for proc in procs:
        try:
            print(f"{Colors.YELLOW}  🧹 Matando proceso zombie PID {proc.pid}...{Colors.NC}")
            proc.kill()
            proc.wait(timeout=5)
            killed += 1
            print(f"{Colors.GREEN}  ✅ Proceso {proc.pid} eliminado{Colors.NC}")
        except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied) as e:
            print(f"{Colors.RED}  ❌ Error eliminando {proc.pid}: {e}{Colors.NC}")
    return killed


def main():
    parser = argparse.ArgumentParser(description="Health check para v2m")
    parser.add_argument('--kill-zombies', action='store_true',
                        help='Eliminar automáticamente procesos zombie')
    parser.add_argument('--restart-daemon', action='store_true',
                        help='Reiniciar daemon después de cleanup')
    args = parser.parse_args()

    print(f"{Colors.BLUE}{'=' * 50}")
    print(f"🏥 V2M Health Check")
    print(f"{'=' * 50}{Colors.NC}\n")

    # 1. Verificar procesos
    print(f"{Colors.YELLOW}[1/3] Verificando procesos...{Colors.NC}")
    procs = get_v2m_processes()

    daemon_running = False
    if not procs:
        print(f"{Colors.GREEN}✅ No hay procesos v2m corriendo{Colors.NC}")
    else:
        print(f"{Colors.YELLOW}⚠️  {len(procs)} proceso(s) v2m encontrado(s):{Colors.NC}")
        for proc in procs:
            mem_mb = proc.memory_info().rss / 1024 / 1024
            cmdline_short = ' '.join(proc.cmdline()[:3])
            print(f"  PID {proc.pid}: {cmdline_short}... (RAM: {mem_mb:.0f}MB)")
            # Asumimos que si hay un proceso python v2m, es el daemon
            if "python" in cmdline_short and "v2m" in cmdline_short:
                daemon_running = True

    # 2. Verificar API HTTP
    print(f"\n{Colors.YELLOW}[2/3] Verificando API HTTP (Port {DEFAULT_PORT})...{Colors.NC}")
    api_responsive = is_daemon_responsive()

    if api_responsive:
        print(f"{Colors.GREEN}✅ API responde correctamente en puerto {DEFAULT_PORT}{Colors.NC}")
        daemon_running = True # Confirmado por HTTP
    else:
        if daemon_running:
             print(f"{Colors.RED}❌ Proceso corriendo pero API NO responde (posible bloqueo){Colors.NC}")
        else:
             print(f"{Colors.YELLOW}⚠️  API no disponible (daemon detenido){Colors.NC}")

    # 3. Verificar VRAM
    print(f"\n{Colors.YELLOW}[3/3] Verificando VRAM...{Colors.NC}")
    vram_used, vram_free = get_gpu_memory()
    if vram_used > 0:
        vram_total = vram_used + vram_free
        vram_pct = (vram_used / vram_total) * 100 if vram_total > 0 else 0
        print(f"  VRAM Usada: {vram_used}MiB / {vram_total}MiB ({vram_pct:.1f}%)")

        if vram_used > 1000 and not daemon_running:
            print(f"{Colors.RED}🚨 ALERTA: Alta VRAM sin daemon activo - posible leak!{Colors.NC}")
        elif vram_used < 500:
            print(f"{Colors.GREEN}✅ VRAM limpia{Colors.NC}")
        else:
            print(f"{Colors.YELLOW}⚠️  VRAM en uso (puede ser normal si daemon está activo){Colors.NC}")
    else:
        print(f"{Colors.YELLOW}⚠️  nvidia-smi no disponible{Colors.NC}")

    # ACCIONES
    print(f"\n{Colors.BLUE}{'=' * 50}{Colors.NC}")

    # Detección de zombies
    zombie_detected = False
    if daemon_running and not api_responsive:
        # Proceso existe pero no responde HTTP
        print(f"{Colors.RED}🚨 ZOMBIE DETECTADO: Proceso colgado (sin respuesta HTTP){Colors.NC}")
        zombie_detected = True
    elif vram_used > 1000 and not daemon_running:
        print(f"{Colors.RED}🚨 ZOMBIE DETECTADO: VRAM alta sin daemon{Colors.NC}")
        zombie_detected = True

    if zombie_detected or (args.kill_zombies and procs and not api_responsive):
        if args.kill_zombies:
            print(f"\n{Colors.YELLOW}Eliminando procesos zombie...{Colors.NC}")
            killed = kill_zombies(procs)
            print(f"{Colors.GREEN}✅ {killed} proceso(s) eliminado(s){Colors.NC}")
        else:
            print(f"{Colors.YELLOW}💡 Usa --kill-zombies para eliminar automáticamente{Colors.NC}")

    if args.restart_daemon and (not daemon_running or zombie_detected):
        print(f"\n{Colors.YELLOW}Reiniciando daemon...{Colors.NC}")
        # Aquí podríamos agregar lógica para reiniciar
        print(f"{Colors.YELLOW}💡 Ejecuta manualmente: python -m v2m.main &{Colors.NC}")

    print(f"\n{Colors.GREEN}✅ Health check completado{Colors.NC}")

    # Exit code
    if zombie_detected and not args.kill_zombies:
        sys.exit(1)  # Indicar que hay problema


if __name__ == "__main__":
    main()
