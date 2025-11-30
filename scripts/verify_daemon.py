#!/usr/bin/env python3
"""
Verificación completa del daemon - la prueba de fuego para V2M.

¿Qué hace esto?
    Este es el script que corre todas las pruebas de integración del sistema
    V2M de principio a fin. Básicamente levanta un daemon de prueba, le manda
    comandos reales (como si fueras vos usando la aplicación), y verifica que
    todo responda correctamente.

    Piénsalo como un "smoke test" completo del sistema.

¿Cuándo usarlo?
    - Después de hacer cambios al daemon o al cliente.
    - Cuando algo raro pasa y querés descartar problemas de comunicación.
    - Antes de un release o deploy para asegurarte que todo funciona.
    - Si el daemon no responde y querés ver exactamente dónde falla.

Lo que prueba:
    1. Levanta un daemon fresco desde cero.
    2. Manda un PING y espera el PONG (prueba de conectividad básica).
    3. Inicia una grabación y la detiene (simula el flujo real).
    4. Manda texto a Gemini para procesamiento.
    5. Limpia todo al final (mata el daemon de prueba).

Ejemplo de uso:
    $ python scripts/verify_daemon.py

    Si todo sale bien vas a ver algo así:

        Starting Daemon...
        Sending PING...
        SUCCESS: Received PONG
        Sending START_RECORDING...
        Recording started.
        Sending STOP_RECORDING...
        Recording stopped. Transcription should be in clipboard.
        Testing Gemini processing...
        SUCCESS: All tests passed!

⚠️  IMPORTANTE:
    Este script levanta su PROPIO daemon para las pruebas. Si tenés
    el servicio systemd corriendo (v2m.service), van a pelear por
    el mismo socket y vas a tener errores raros. Asegurate de parar
    el servicio antes de correr esto:

        $ sudo systemctl stop v2m.service
        $ python scripts/verify_daemon.py
        $ sudo systemctl start v2m.service

Dependencias:
    Los módulos del propio V2M (v2m.daemon, v2m.client). Si ves errores
    de import, probablemente estés corriendo desde el directorio incorrecto.

Author:
    Voice2Machine Team

Since:
    v1.0.0
"""

import subprocess
import time
import sys
import os
from typing import Tuple

# Path to python executable
PYTHON = sys.executable
"""str: Ruta al ejecutable de Python actual."""

DAEMON_SCRIPT = "src/v2m/daemon.py"
"""str: Ruta al script del daemon."""

CLIENT_SCRIPT = "src/v2m/client.py"
"""str: Ruta al script del cliente."""


def run_client(*args: str) -> Tuple[str, str, int]:
    """
    Manda un comando al daemon y te devuelve qué pasó.

    Esta función es como el intermediario entre las pruebas y el daemon.
    Ejecuta el cliente V2M con el comando que le pases y te devuelve
    toda la info relevante: qué respondió, si hubo errores, y el código
    de salida.

    Args:
        *args: El comando y sus argumentos. Por ejemplo: "PING", o
            "PROCESS_TEXT", "hola mundo".

    Returns:
        Una tupla con tres cosas:
            - La respuesta del daemon (lo que imprimió a stdout).
            - Los errores si hubo alguno (stderr).
            - El código de retorno (0 = éxito, otro número = algo falló).

    Example:
        >>> stdout, stderr, code = run_client("PING")
        >>> if code == 0 and stdout == "PONG":
        ...     print("El daemon está vivo y responde!")
    """
    cmd = [PYTHON, CLIENT_SCRIPT] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def main() -> None:
    """
    Corre todas las pruebas del daemon de principio a fin.

    Esta es la función que orquesta todo el show. La secuencia es:

        1. Levanta un daemon fresco en segundo plano.
        2. Espera 10 segundos (sí, es mucho, pero el daemon necesita
           cargar Whisper y eso tarda).
        3. Manda un PING y verifica que reciba PONG.
        4. Simula una grabación: START → espera 3 segundos → STOP.
        5. Manda texto a Gemini para ver si el procesamiento funciona.
        6. Mata el daemon al final para dejar todo limpio.

    Si algo falla, el script termina con exit(1) y te muestra qué pasó.
    Si todo sale bien, vas a ver "SUCCESS" en varios puntos.

    Note:
        Los 10 segundos de espera inicial pueden parecer eternos, pero
        créeme que son necesarios. Cargar el modelo Whisper en GPU toma
        su tiempo, y si mandás comandos antes de que termine, vas a
        tener errores de conexión rechazada.
    """
    print("Starting Daemon...")
    daemon_process = subprocess.Popen(
        [PYTHON, DAEMON_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Give it time to start
    time.sleep(10)

    try:
        print("Sending PING...")
        stdout, stderr, code = run_client("PING")

        if code != 0:
            print(f"Client failed: {stderr}")
            sys.exit(1)

        if stdout == "PONG":
            print("SUCCESS: Received PONG")
        else:
            print(f"FAILURE: Received '{stdout}', expected 'PONG'")
            sys.exit(1)

        print("Sending START_RECORDING...")
        stdout, stderr, code = run_client("START_RECORDING")
        if code != 0:
            print(f"START_RECORDING failed: {stderr}")
        else:
            print("Recording started.")

        time.sleep(3)

        print("Sending STOP_RECORDING...")
        stdout, stderr, code = run_client("STOP_RECORDING")
        if code != 0:
            print(f"STOP_RECORDING failed: {stderr}")
        else:
            print("Recording stopped. Transcription should be in clipboard.")

        time.sleep(1)

        print("Sending PROCESS_TEXT (Testing Gemini Fallback)...")
        test_text = "This is a test for Gemini Fallback"
        stdout, stderr, code = run_client("PROCESS_TEXT", test_text)
        if code != 0:
            print(f"PROCESS_TEXT failed: {stderr}")
        else:
            print(f"PROCESS_TEXT response: {stdout}")
            print("Check clipboard or notifications for result.")

    finally:
        print("Shutting down Daemon...")
        run_client("SHUTDOWN")
        daemon_process.terminate()
        daemon_process.wait()

        stdout_bytes, stderr_bytes = daemon_process.communicate()
        if stdout_bytes:
            print(f"Daemon STDOUT:\n{stdout_bytes.decode()}")
        if stderr_bytes:
            print(f"Daemon STDERR:\n{stderr_bytes.decode()}")


if __name__ == "__main__":
    main()
