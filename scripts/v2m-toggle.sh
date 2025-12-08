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
# v2m-toggle.sh - script de conmutación de grabación por voz
#
# descripción
#   este es el script principal para control por voz alterna entre
#   iniciar y detener la grabación de audio diseñado para asignarse
#   a un atajo de teclado (recomendado ctrl+shift+space)
#
# uso
#   ./scripts/v2m-toggle.sh
#
# flujo de trabajo
#   primera ejecución
#     1 verifica/inicia el daemon si no está corriendo
#     2 inicia la grabación de audio
#     3 crea archivo de bandera /tmp/v2m_recording.pid
#
#   segunda ejecución
#     1 detecta que hay una grabación en curso
#     2 detiene la grabación
#     3 transcribe el audio con whisper
#     4 copia el resultado al portapapeles
#     5 elimina el archivo de bandera
#
# configuración de atajo en gnome
#   # crear atajo personalizado
#   keybinding_path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/whisper0/"
#   gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
#     "['$keybinding_path']"
#   gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$keybinding_path \
#     name 'v2m toggle'
#   gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$keybinding_path \
#     command '$home/v2m/scripts/v2m-toggle.sh'
#   gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$keybinding_path \
#     binding '<control><shift>space'
#
# dependencias
#   - v2m-daemon.sh para gestión del daemon
#   - notify-send para notificaciones de escritorio
#   - entorno virtual de python en ./venv
#
# archivos
#   /tmp/v2m_recording.pid - bandera de grabación activa
#
# notas
#   - el daemon se inicia automáticamente si no está corriendo
#   - las notificaciones indican el estado de la operación
#
# autor
#   voice2machine team
#
# desde
#   v1.0.0
#

# --- configuración ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )/apps/backend"
NOTIFY_EXPIRE_TIME=3000

# --- rutas derivadas ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/v2m/main.py"
RECORDING_FLAG="/tmp/v2m_recording.pid"
DAEMON_SCRIPT="${SCRIPT_DIR}/v2m-daemon.sh"

# --- función principal ---
ensure_daemon() {
    "${DAEMON_SCRIPT}" status > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        if command -v notify-send > /dev/null 2>&1; then
            notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "🎙️ v2m" "iniciando servicio en segundo plano..."
        fi

        "${DAEMON_SCRIPT}" start
        if [ $? -ne 0 ]; then
            if command -v notify-send > /dev/null 2>&1; then
                notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error de v2m" "no se pudo iniciar el daemon"
            fi
            exit 1
        fi
    fi
}

run_client() {
    local command=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        if command -v notify-send > /dev/null 2>&1; then
            notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error de v2m" "entorno virtual no encontrado en ${VENV_PATH}"
        fi
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    export PYTHONPATH="${PROJECT_DIR}/src"
    python3 "${MAIN_SCRIPT}" "${command}"
}

# --- lógica de conmutación ---
ensure_daemon

if [ -f "${RECORDING_FLAG}" ]; then
    run_client "STOP_RECORDING"
else
    run_client "START_RECORDING"
fi
