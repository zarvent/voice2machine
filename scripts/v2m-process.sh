#!/bin/bash
#
# v2m-process.sh - Script de procesamiento del contenido del portapapeles
#
# DESCRIPCIÓN:
#   Este script lee el contenido actual del portapapeles y lo envía
#   a V2M para procesamiento con Gemini. Es ideal para asignar a
#   un atajo de teclado para procesamiento rápido.
#
# USO:
#   ./scripts/v2m-process.sh
#
# FLUJO DE TRABAJO:
#   1. Lee el contenido del portapapeles con xclip
#   2. Envía el texto al orquestador de V2M
#   3. El resultado procesado se copia al portapapeles
#   4. Muestra notificación de éxito o error
#
# DEPENDENCIAS:
#   - xclip: Para acceso al portapapeles
#   - notify-send: Para notificaciones de escritorio
#   - Entorno virtual de Python en ./venv
#
# INTEGRACIÓN CON ATAJOS DE TECLADO:
#   En GNOME:
#   gsettings set org.gnome.settings-daemon.plugins.media-keys \
#     custom-keybindings "['/org/gnome/.../custom0/']"
#   gsettings set ... command "$HOME/v2m/scripts/v2m-process.sh"
#
# NOTAS:
#   - Requiere sesión X11 activa para xclip
#   - Muestra error si el portapapeles está vacío
#
# AUTOR:
#   Voice2Machine Team
#
# DESDE:
#   v1.0.0
#

# --- Configuración ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )"
NOTIFY_EXPIRE_TIME=3000

# --- Rutas Derivadas ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/v2m/main.py"

# --- Función Principal ---
run_orchestrator() {
    local text_to_process=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ Error de V2M" "Entorno virtual no encontrado en ${VENV_PATH}"
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
    notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ Error" "El portapapeles está vacío."
    exit 1
fi
