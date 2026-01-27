#!/usr/bin/env python3

"""
verificación completa del daemon - la prueba de fuego para v2m (Edición HTTP)

¿qué hace esto?
    este es el script que corre todas las pruebas de integración del sistema
    v2m de principio a fin básicamente levanta un daemon de prueba (FastAPI)
    y le manda requests HTTP para verificar que todo responda correctamente.

    piénsalo como un "smoke test" completo del sistema

¿cuándo usarlo?
    - después de hacer cambios al daemon
    - cuando algo raro pasa y querés descartar problemas de comunicación
    - antes de un release o deploy para asegurarte que todo funciona

lo que prueba
    1 levanta un daemon fresco desde cero
    2 manda un health check (prueba de conectividad básica)
    3 inicia una grabación y la detiene (simula el flujo real)
    4 manda texto para procesamiento
    5 limpia todo al final (mata el daemon de prueba)

ejemplo de uso
    $ python scripts/verify_daemon.py

⚠️ importante
    este script levanta su propio daemon en puerto 8765. Asegúrate de que
    el puerto esté libre.
"""

import subprocess
import time
import sys
import os
import requests
from pathlib import Path

# Path to python executable
PYTHON = sys.executable

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parents[1]
# Now we run v2m.main which starts the FastAPI server
DAEMON_CMD = [PYTHON, "-m", "v2m.main"]

BASE_URL = "http://127.0.0.1:8765"

def check_server_health(retries=10, delay=2):
    """Espera a que el servidor esté vivo."""
    print("Waiting for server to be healthy...")
    for i in range(retries):
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=1)
            if resp.status_code == 200:
                print("✅ Server is UP!")
                return True
        except requests.RequestException:
            pass
        print(f"Server not ready, retrying ({i+1}/{retries})...")
        time.sleep(delay)
    return False

def main() -> None:
    print("Starting Daemon (FastAPI)...")
    # Set PYTHONPATH to include src
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR / "src")

    daemon_process = subprocess.Popen(
        DAEMON_CMD,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        if not check_server_health():
            print("❌ Server failed to start.")
            sys.exit(1)

        # 1. Health Check
        print("\n--- Testing /health ---")
        try:
            resp = requests.get(f"{BASE_URL}/health")
            print(f"Status: {resp.status_code}, Body: {resp.json()}")
            if resp.status_code == 200:
                print("✅ Health Check Passed")
            else:
                print("❌ Health Check Failed")
        except Exception as e:
            print(f"❌ Exception: {e}")

        # 2. Toggle Recording (Start)
        print("\n--- Testing /start ---")
        try:
            resp = requests.post(f"{BASE_URL}/start")
            print(f"Status: {resp.status_code}, Body: {resp.json()}")
            if resp.status_code == 200:
                print("✅ Recording Started")
            else:
                print(f"❌ Failed to start recording: {resp.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

        print("Recording for 3 seconds...")
        time.sleep(3)

        # 3. Toggle Recording (Stop)
        print("\n--- Testing /stop ---")
        try:
            resp = requests.post(f"{BASE_URL}/stop")
            print(f"Status: {resp.status_code}, Body: {resp.json()}")
            if resp.status_code == 200:
                print("✅ Recording Stopped")
            else:
                print(f"❌ Failed to stop recording: {resp.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

        # 4. LLM Process
        print("\n--- Testing /llm/process ---")
        try:
            payload = {"text": "Hello world test message"}
            resp = requests.post(f"{BASE_URL}/llm/process", json=payload)
            print(f"Status: {resp.status_code}, Body: {resp.json()}")
            if resp.status_code == 200:
                print("✅ LLM Process Passed")
            else:
                print(f"❌ LLM Process Failed: {resp.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

    finally:
        print("\nShutting down Daemon...")
        daemon_process.terminate()
        try:
            daemon_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            daemon_process.kill()

        # Print logs if failed
        stdout_bytes, stderr_bytes = daemon_process.communicate()
        if stdout_bytes:
            print(f"Daemon STDOUT:\n{stdout_bytes.decode()}")
        if stderr_bytes:
            print(f"Daemon STDERR:\n{stderr_bytes.decode()}")

if __name__ == "__main__":
    main()
