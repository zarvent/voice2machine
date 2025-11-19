#!/bin/bash

# --- Configuración ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )"

# --- Rutas Derivadas ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/v2m/main.py"

# --- Función Principal ---
run_orchestrator() {
    local text_to_process=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        notify-send "❌ Error de V2M" "Entorno virtual no encontrado en ${VENV_PATH}"
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    export PYTHONPATH="${PROJECT_DIR}/src"
    echo "${text_to_process}" | python3 "${MAIN_SCRIPT}" "process"
}

# --- Lógica Principal ---
clipboard_content=$(xclip -o -selection clipboard)
if [ -n "${clipboard_content}" ]; then
    run_orchestrator "${clipboard_content}"
else
    notify-send "❌ Error" "El portapapeles está vacío."
    exit 1
fi
