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
#--------------------------------------------------------------------------------
#
# v2m-llm.sh - SCRIPT PARA PROCESAR TEXTO DEL PORTAPAPELES CON LLM
#
# DESCRIPCIÓN
#   este script lee el contenido del portapapeles y lo envía al daemon
#   de v2m para procesamiento con el llm configurado (local o gemini)
#   el backend se determina automáticamente desde config.toml
#
# USO
#   ./scripts/v2m-llm.sh
#
# FLUJO DE TRABAJO
#   1 lee el contenido del portapapeles con xclip
#   2 envía el comando process_text al daemon via ipc
#   3 el daemon procesa con el llm según config.toml [llm.backend]
#   4 el resultado refinado se copia automáticamente al portapapeles
#
# BACKEND LLM
#   - si config.toml tiene [llm] backend = "local" → usa qwen local
#   - si config.toml tiene [llm] backend = "gemini" → usa gemini api
#
# DEPENDENCIAS
#   - xclip para acceso al portapapeles
#   - notify-send para notificaciones de escritorio
#   - v2m daemon debe estar corriendo (systemctl start v2m-daemon)
#
# INTEGRACIÓN CON ATAJOS DE TECLADO
#   gnome (gsettings)
#     gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ \
#       name 'v2m process text'
#     gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ \
#       command "$home/v2m/scripts/v2m-llm.sh"
#     gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ \
#       binding '<super><shift>p'
#
#   kde plasma
#     configuración del sistema → atajos → atajos personalizados → editar → nuevo → comando global de atajo
#
# NOTAS
#   - requiere sesión x11 activa para xclip
#   - el daemon debe estar corriendo antes de ejecutar este script
#   - muestra error si el portapapeles está vacío
#
# AUTOR
#   voice2machine team
#
# DESDE
#   v2.0.0
#

set -euo pipefail

# --- CONFIGURACIÓN ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )/apps/backend"
NOTIFY_EXPIRE_TIME=3000

# --- RUTAS DERIVADAS ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/v2m/main.py"

# --- VERIFICACIONES PREVIAS ---
if ! command -v xclip &> /dev/null; then
    notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error de dependencia" "xclip no está instalado instálalo con: sudo apt install xclip"
    echo "error: xclip is not installed" >&2
    exit 1
fi

if [ ! -f "${MAIN_SCRIPT}" ]; then
     notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error crítico" "no se encontró el script principal en: ${MAIN_SCRIPT}"
     echo "error: main script not found at ${MAIN_SCRIPT}" >&2
     exit 1
fi

# --- FUNCIÓN PARA NOTIFICACIONES CON AUTO-DISMISS VIA DBUS ---
# replica el comportamiento de linuxnotificationservice de python
# resuelve el bug de unity/gnome que ignora --expire-time de notify-send
auto_dismiss_notify() {
    local title="$1"
    local message="$2"
    local expire_time="${3:-3000}"  # default 3 segundos

    # enviar notificación via dbus y capturar el id
    local notify_output
    notify_output=$(gdbus call --session \
        --dest org.freedesktop.Notifications \
        --object-path /org/freedesktop/Notifications \
        --method org.freedesktop.Notifications.Notify \
        "v2m" 0 "" "$title" "$message" "[]" "{}" "$expire_time" 2>/dev/null)

    # extraer notification_id de salida: "(uint32 123,)"
    if [[ $notify_output =~ uint32\ ([0-9]+) ]]; then
        local notification_id="${BASH_REMATCH[1]}"

        # programar cierre automático en background
        (
            sleep $(awk "BEGIN {print $expire_time/1000}")
            gdbus call --session \
                --dest org.freedesktop.Notifications \
                --object-path /org/freedesktop/Notifications \
                --method org.freedesktop.Notifications.CloseNotification \
                "$notification_id" &>/dev/null
        ) &
    else
        # fallback a notify-send si dbus falla
        notify-send --expire-time="$expire_time" "$title" "$message" 2>/dev/null || true
    fi
}

# --- FUNCIÓN PARA ENVIAR COMANDO AL DAEMON ---
send_to_daemon() {
    local text_to_process="$1"

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error de v2m" "entorno virtual no encontrado en ${VENV_PATH}"
        echo "error: virtual environment not found at ${VENV_PATH}" >&2
        exit 1
    fi

    # activar entorno y enviar comando process_text al daemon
    # usamos subshell para aislar variables de entorno
    (
        source "${VENV_PATH}/bin/activate"
        export PYTHONPATH="${PROJECT_DIR}/src"

        # usar el cliente ipc para comunicarse con el daemon
        if ! python3 "${MAIN_SCRIPT}" PROCESS_TEXT "${text_to_process}"; then
            echo "error executing python script" >&2
            exit 1
        fi
    )
}

# --- LÓGICA PRINCIPAL ---
# leer contenido del portapapeles
# '|| true' previene fallo si xclip devuelve error (ej. selección vacía en algunos casos)
clipboard_content=$(xclip -o -selection clipboard 2>/dev/null || true)

if [ -n "${clipboard_content}" ]; then
    # notificar inicio del procesamiento (se auto-elimina en 1 segundo)
    auto_dismiss_notify "🧠 procesando..." "refinando texto con llm..." 1000

    # enviar al daemon para procesamiento
    if ! send_to_daemon "${clipboard_content}"; then
        notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "❌ error" "falló el procesamiento del texto"
        exit 1
    fi
else
    notify-send --expire-time=${NOTIFY_EXPIRE_TIME} "⚠️ portapapeles vacío" "copia texto antes de usar este atajo"
    exit 1
fi
