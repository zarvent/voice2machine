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
# v2m-process.sh - script de procesamiento del contenido del portapapeles
#
# descripción
#   este script lee el contenido actual del portapapeles y lo envía
#   a v2m para procesamiento con gemini es ideal para asignar a
#   un atajo de teclado para procesamiento rápido
#
# uso
#   ./scripts/v2m-process.sh
#
# flujo de trabajo
#   1 lee el contenido del portapapeles con xclip
#   2 envía el texto al orquestador de v2m
#   3 el resultado procesado se copia al portapapeles
#   4 muestra notificación de éxito o error
#
# dependencias
#   - xclip para acceso al portapapeles
#   - notify-send para notificaciones de escritorio
#   - entorno virtual de python en ./venv
#
# integración con atajos de teclado
#   en gnome
#   gsettings set org.gnome.settings-daemon.plugins.media-keys \
#     custom-keybindings "['/org/gnome/.../custom0/']"
#   gsettings set ... command "$home/v2m/scripts/v2m-process.sh"
#
# notas
#   - requiere sesión x11 activa para xclip
#   - muestra error si el portapapeles está vacío
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

# --- función principal ---
run_orchestrator() {
    local text_to_process=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error de v2m" "entorno virtual no encontrado en ${VENV_PATH}"
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    export PYTHONPATH="${PROJECT_DIR}/src"
    echo "${text_to_process}" | python3 "${MAIN_SCRIPT}" "process"
}

# --- lógica principal ---
clipboard_content=$(xclip -o -selection clipboard)
if [ -n "${clipboard_content}" ]; then
    run_orchestrator "${clipboard_content}"
else
    notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error" "el portapapeles está vacío"
    exit 1
fi
