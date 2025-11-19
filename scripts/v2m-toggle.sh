#!/bin/bash

# --- Configuración ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )"

# --- Rutas Derivadas ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/v2m/main.py"
RECORDING_FLAG="/tmp/v2m_recording.pid"

# --- Función Principal ---
run_client() {
    local command=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        notify-send "❌ Error de V2M" "Entorno virtual no encontrado en ${VENV_PATH}"
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    export PYTHONPATH="${PROJECT_DIR}/src"
    python3 "${MAIN_SCRIPT}" "${command}"
}

# --- Lógica de Conmutación ---
if [ -f "${RECORDING_FLAG}" ]; then
    run_client "STOP_RECORDING"
else
    run_client "START_RECORDING"
fi
