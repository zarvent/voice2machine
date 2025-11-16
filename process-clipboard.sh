#!/bin/bash
set -euo pipefail  # Mejor práctica: fallar rápido

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"
PYTHON_PROCESSOR="$SCRIPT_DIR/llm_processor.py"
LOG_FILE="$SCRIPT_DIR/logs/process.log"

# Asegurarse que el archivo de log exista
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 1. Notificar inicio
notify-send "🧠 Procesando texto..." "Llamando a la API de Gemini..." -t 2000

# 2. Leer portapapeles
CLIPBOARD_CONTENT=$(xclip -selection clipboard -o 2>/dev/null || echo "")

if [ -z "$CLIPBOARD_CONTENT" ]; then
    log "ERROR: Portapapeles vacío"
    notify-send "❌ Error" "El portapapeles está vacío."
    exit 1
fi

log "Texto original (${#CLIPBOARD_CONTENT} caracteres)"

# 3. Activar venv y procesar
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    log "ERROR: El entorno virtual no se encuentra en $VENV_PATH"
    notify-send "❌ Error de Configuración" "No se encontró el entorno virtual."
    exit 1
fi
source "$VENV_PATH/bin/activate"

TMP_ERR=$(mktemp)
EXIT_CODE=0
REFINED_TEXT=$(python3 "$PYTHON_PROCESSOR" "$CLIPBOARD_CONTENT" 2>"$TMP_ERR") || EXIT_CODE=$?

if [ -s "$TMP_ERR" ]; then
    log "STDERR python: $(cat "$TMP_ERR")"
fi
rm -f "$TMP_ERR"

if [ $EXIT_CODE -ne 0 ]; then
    log "ERROR: El script de Python falló con código $EXIT_CODE"
    log "Salida de error: $REFINED_TEXT"
    notify-send "❌ Error de LLM" "Falló el script de Python. Revisa $LOG_FILE" -t 5000
    exit 1
fi

# 4. Copiar al portapapeles
echo -n "$REFINED_TEXT" | xclip -selection clipboard

# 5. Notificar éxito
PREVIEW=$(echo "$REFINED_TEXT" | head -c 100)
log "Procesamiento exitoso (${#REFINED_TEXT} caracteres)"
notify-send "✅ Texto Refinado" "$PREVIEW..." -t 3000
