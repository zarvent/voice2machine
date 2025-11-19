#!/bin/bash

# --- Configuración ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )"

# --- Rutas Derivadas ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/whisper_dictation/main.py"
RECORDING_FLAG="/tmp/whisper_recording.pid"

# --- Función Principal ---
run_orchestrator() {
    local command=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        notify-send "❌ Error de Whisper" "Entorno virtual no encontrado en ${VENV_PATH}"
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    python3 "${MAIN_SCRIPT}" "${command}"
}

# --- Lógica de Conmutación ---
if [ -f "${RECORDING_FLAG}" ]; then
    run_orchestrator "STOP_RECORDING"
else
    run_orchestrator "START_RECORDING"
fi
