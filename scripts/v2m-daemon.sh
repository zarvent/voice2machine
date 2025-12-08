#!/bin/bash

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
#
# v2m-daemon.sh - script de gestión del daemon voice2machine
#
# descripción
#   este script proporciona una interfaz de línea de comandos para
#   gestionar el daemon de v2m que corre en segundo plano permite
#   iniciar detener reiniciar y verificar el estado del daemon
#
# uso
#   ./scripts/v2m-daemon.sh [start|stop|restart|status|logs]
#
# comandos
#   start    - inicia el daemon en segundo plano
#   stop     - detiene el daemon de forma segura
#   restart  - reinicia el daemon (stop + start)
#   status   - muestra el estado actual y prueba conectividad
#   logs     - muestra los logs del daemon
#
# archivos
#   /tmp/v2m_daemon.log  - archivo de logs del daemon
#   /tmp/v2m_daemon.pid  - archivo con el pid del proceso
#
# variables de entorno
#   ld_library_path - se configura automáticamente para cuda/cudnn
#   pythonpath      - se configura para incluir src/
#
# dependencias
#   - python 3.12+ con entorno virtual en ./venv
#   - librerías nvidia en el venv (opcional para gpu)
#
# ejemplos
#   # iniciar el daemon
#   ./scripts/v2m-daemon.sh start
#
#   # ver estado y probar conectividad
#   ./scripts/v2m-daemon.sh status
#
#   # ver logs en tiempo real
#   ./scripts/v2m-daemon.sh logs
#
# notas
#   - el daemon usa un socket unix para comunicación ipc
#   - los logs se rotan automáticamente con cleanup.py
#   - si cuda no está disponible usa cpu automáticamente
#
# autor
#   voice2machine team
#
# desde
#   v1.0.0
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )/apps/backend"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"
LOG_FILE="/tmp/v2m_daemon.log"
PID_FILE="/tmp/v2m_daemon.pid"

start_daemon() {
    if [ -f "${PID_FILE}" ]; then
        PID=$(cat "${PID_FILE}")
        if ps -p "${PID}" > /dev/null 2>&1; then
            echo "❌ Daemon ya está corriendo (PID: ${PID})"
            return 1
        else
            echo "⚠️  PID file existe pero proceso no está corriendo. Limpiando..."
            rm -f "${PID_FILE}"
        fi
    fi

    echo "🚀 iniciando daemon de v2m..."

    cd "${PROJECT_DIR}"
    export PYTHONPATH="${PROJECT_DIR}/src"

    # --- configurar ld_library_path para cuda/cudnn ---
    # buscar librerías nvidia en el venv (necesario para whisper y llama-cpp-python)
    VENV_LIB="${PROJECT_DIR}/venv/lib/python3.12/site-packages/nvidia"
    CUDA_PATHS=""

    if [ -d "${VENV_LIB}" ]; then
        # paquetes nvidia que contienen libs necesarias para cuda
        NVIDIA_PACKAGES=(
            "cuda_runtime"
            "cudnn"
            "cublas"
            "cufft"
            "curand"
            "cusolver"
            "cusparse"
            "nvjitlink"
        )

        for pkg in "${NVIDIA_PACKAGES[@]}"; do
            lib_path="${VENV_LIB}/${pkg}/lib"
            if [ -d "$lib_path" ]; then
                if [ -z "${CUDA_PATHS}" ]; then
                    CUDA_PATHS="$lib_path"
                else
                    CUDA_PATHS="${CUDA_PATHS}:${lib_path}"
                fi
            fi
        done
    fi

    # agregar al ld_library_path existente
    if [ -n "${CUDA_PATHS}" ]; then
        export LD_LIBRARY_PATH="${CUDA_PATHS}:${LD_LIBRARY_PATH:-}"
        echo "🔧 ld_library_path configurado con librerías nvidia del venv"
    else
        echo "⚠️  no se encontraron librerías nvidia en el venv cuda podría fallar"
    fi

    "${VENV_PYTHON}" -m v2m.main --daemon > "${LOG_FILE}" 2>&1 &

    DAEMON_PID=$!
    echo "${DAEMON_PID}" > "${PID_FILE}"

    # esperar un momento para verificar que arrancó correctamente
    sleep 2

    if ps -p "${DAEMON_PID}" > /dev/null 2>&1; then
        echo "✅ daemon iniciado correctamente (pid: ${DAEMON_PID})"
        echo "📋 logs en: ${LOG_FILE}"
    else
        echo "❌ el daemon falló al iniciar ver logs:"
        tail -20 "${LOG_FILE}"
        rm -f "${PID_FILE}"
        return 1
    fi
}

stop_daemon() {
    if [ ! -f "${PID_FILE}" ]; then
        echo "⚠️  No se encontró PID file. Buscando proceso manualmente..."
        PID=$(ps aux | grep "python.*v2m.main --daemon" | grep -v grep | awk '{print $2}' | head -1)
        if [ -z "${PID}" ]; then
            echo "❌ Daemon no está corriendo"
            return 1
        fi
    else
        PID=$(cat "${PID_FILE}")
    fi

    echo "🛑 Deteniendo daemon (PID: ${PID})..."
    kill -TERM "${PID}" 2>/dev/null

    # Esperar hasta 5 segundos para que termine gracefully
    for i in {1..10}; do
        if ! ps -p "${PID}" > /dev/null 2>&1; then
            echo "✅ Daemon detenido correctamente"
            rm -f "${PID_FILE}"
            return 0
        fi
        sleep 0.5
    done

    # Si no terminó, force kill
    echo "⚠️  Daemon no respondió a SIGTERM, forzando..."
    kill -9 "${PID}" 2>/dev/null
    rm -f "${PID_FILE}"
    echo "✅ Daemon forzadamente detenido"
}

status_daemon() {
    if [ -f "${PID_FILE}" ]; then
        PID=$(cat "${PID_FILE}")
        if ps -p "${PID}" > /dev/null 2>&1; then
            echo "✅ Daemon corriendo (PID: ${PID})"

            # Mostrar info del proceso
            ps -p "${PID}" -o pid,ppid,user,%cpu,%mem,etime,cmd

            # Test de ping
            echo ""
            echo "🔍 Probando conectividad..."
            cd "${PROJECT_DIR}"
            export PYTHONPATH="${PROJECT_DIR}/src"
            PING_RESULT=$("${VENV_PYTHON}" -c "import asyncio; from v2m.client import send_command; print(asyncio.run(send_command('PING')))" 2>&1)

            if echo "${PING_RESULT}" | grep -q "PONG"; then
                echo "✅ Daemon respondiendo correctamente"
            else
                echo "⚠️  Daemon no responde a PING:"
                echo "${PING_RESULT}"
            fi

            return 0
        else
            echo "❌ PID file existe pero proceso no está corriendo"
            rm -f "${PID_FILE}"
            return 1
        fi
    else
        echo "❌ Daemon no está corriendo (no se encontró PID file)"
        return 1
    fi
}

show_logs() {
    if [ ! -f "${LOG_FILE}" ]; then
        echo "❌ No se encontró archivo de logs: ${LOG_FILE}"
        return 1
    fi

    if command -v less > /dev/null 2>&1; then
        less +G "${LOG_FILE}"
    else
        tail -50 "${LOG_FILE}"
    fi
}

# --- MAIN ---
case "${1:-}" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        stop_daemon
        sleep 1
        start_daemon
        ;;
    status)
        status_daemon
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "USO: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Comandos:"
        echo "  start    - Inicia el daemon"
        echo "  stop     - Detiene el daemon"
        echo "  restart  - Reinicia el daemon"
        echo "  status   - Muestra el estado del daemon"
        echo "  logs     - Muestra los logs del daemon"
        exit 1
        ;;
esac
