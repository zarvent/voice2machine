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
# v2m-toggle.sh - Script de conmutación de grabación por voz
#
# DESCRIPCIÓN:
#   Este es el script principal para control por voz. Alterna entre
#   iniciar y detener la grabación de audio. Diseñado para asignarse
#   a un atajo de teclado (recomendado: Ctrl+Shift+Space).
#
# USO:
#   ./scripts/v2m-toggle.sh
#
# FLUJO DE TRABAJO:
#   Primera ejecución:
#     1. Verifica/inicia el daemon si no está corriendo
#     2. Inicia la grabación de audio
#     3. Crea archivo de bandera /tmp/v2m_recording.pid
#
#   Segunda ejecución:
#     1. Detecta que hay una grabación en curso
#     2. Detiene la grabación
#     3. Transcribe el audio con Whisper
#     4. Copia el resultado al portapapeles
#     5. Elimina el archivo de bandera
#
# CONFIGURACIÓN DE ATAJO EN GNOME:
#   # Crear atajo personalizado
#   KEYBINDING_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/whisper0/"
#   gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
#     "['$KEYBINDING_PATH']"
#   gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEYBINDING_PATH \
#     name 'V2M Toggle'
#   gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEYBINDING_PATH \
#     command '$HOME/v2m/scripts/v2m-toggle.sh'
#   gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEYBINDING_PATH \
#     binding '<Control><Shift>space'
#
# DEPENDENCIAS:
#   - v2m-daemon.sh: Para gestión del daemon
#   - notify-send: Para notificaciones de escritorio
#   - Entorno virtual de Python en ./venv
#
# ARCHIVOS:
#   /tmp/v2m_recording.pid - Bandera de grabación activa
#
# NOTAS:
#   - El daemon se inicia automáticamente si no está corriendo
#   - Las notificaciones indican el estado de la operación
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
RECORDING_FLAG="/tmp/v2m_recording.pid"
DAEMON_SCRIPT="${SCRIPT_DIR}/v2m-daemon.sh"

# --- Función Principal ---
ensure_daemon() {
    "${DAEMON_SCRIPT}" status > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        if command -v notify-send > /dev/null 2>&1; then
            notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "🎙️ V2M" "Iniciando servicio en segundo plano..."
        fi

        "${DAEMON_SCRIPT}" start
        if [ $? -ne 0 ]; then
            if command -v notify-send > /dev/null 2>&1; then
                notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ Error de V2M" "No se pudo iniciar el daemon"
            fi
            exit 1
        fi
    fi
}

run_client() {
    local command=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        if command -v notify-send > /dev/null 2>&1; then
            notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ Error de V2M" "Entorno virtual no encontrado en ${VENV_PATH}"
        fi
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    export PYTHONPATH="${PROJECT_DIR}/src"
    python3 "${MAIN_SCRIPT}" "${command}"
}

# --- Lógica de Conmutación ---
ensure_daemon

if [ -f "${RECORDING_FLAG}" ]; then
    run_client "STOP_RECORDING"
else
    run_client "START_RECORDING"
fi
