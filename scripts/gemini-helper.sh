#!/bin/bash

# --- Configuración ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )"

# --- Rutas Derivadas ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/whisper_dictation/main.py"

# --- Función Principal ---
run_orchestrator() {
    local text_to_process=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        echo "❌ Error: Entorno virtual no encontrado en ${VENV_PATH}" >&2
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    echo "${text_to_process}" | python3 "${MAIN_SCRIPT}" "process"
}

# --- Lógica Principal ---
if [ -n "$1" ]; then
    run_orchestrator "$1"
else
    echo "Usage: $0 \"<text to process>\"" >&2
    exit 1
fi
