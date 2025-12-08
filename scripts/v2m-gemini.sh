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
# v2m-gemini.sh - SCRIPT DE PROCESAMIENTO DE TEXTO CON GEMINI
#
# DESCRIPCIÓN
#   este script envía texto directamente al procesador de v2m para
#   ser procesado por gemini ai útil para pruebas rápidas o
#   integración con otros scripts
#
# USO
#   ./scripts/v2m-gemini.sh "<texto a procesar>"
#
# PARÁMETROS
#   $1 - texto a procesar con gemini (requerido)
#
# EJEMPLOS
#   # procesar un texto simple
#   ./scripts/v2m-gemini.sh "corrige este texto con errores"
#
#   # procesar desde una variable
#   texto="mi texto"
#   ./scripts/v2m-gemini.sh "$texto"
#
# DEPENDENCIAS
#   - entorno virtual de python configurado en ./venv
#   - variable gemini_api_key configurada en .env
#
# NOTAS
#   - el resultado se envía al portapapeles automáticamente
#   - requiere conexión a internet para la api de gemini
#
# AUTOR
#   voice2machine team
#
# DESDE
#   v1.0.0
#

# --- CONFIGURACIÓN ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "${SCRIPT_DIR}" )/apps/backend"

# --- RUTAS DERIVADAS ---
VENV_PATH="${PROJECT_DIR}/venv"
MAIN_SCRIPT="${PROJECT_DIR}/src/v2m/main.py"

# --- FUNCIÓN PRINCIPAL ---
run_orchestrator() {
    local text_to_process=$1

    if [ ! -f "${VENV_PATH}/bin/activate" ]; then
        echo "❌ error: entorno virtual no encontrado en ${VENV_PATH}" >&2
        exit 1
    fi

    source "${VENV_PATH}/bin/activate"
    echo "${text_to_process}" | python3 "${MAIN_SCRIPT}" "process"
}

# --- LÓGICA PRINCIPAL ---
if [ -n "$1" ]; then
    run_orchestrator "$1"
else
    echo "usage: $0 \"<text to process>\"" >&2
    exit 1
fi
