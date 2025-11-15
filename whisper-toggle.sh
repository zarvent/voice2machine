#!/bin/bash

# Configuración
RECORDING_FLAG="/tmp/whisper_recording.pid"
AUDIO_FILE="/tmp/whisper_audio.wav"
VENV_PATH="$HOME/whisper-dictation/venv"
LOG_FILE="/tmp/whisper_debug.log"

# Función: Iniciar grabación
start_recording() {
    if [ -f "$RECORDING_FLAG" ]; then
        notify-send "⚠️ Whisper" "Ya hay una grabación en proceso"
        exit 1
    fi
    
    rm -f "$AUDIO_FILE"
    
    # Detectar micrófono con múltiples métodos de respaldo
    SOURCE=$(pactl get-default-source 2>/dev/null)
    
    if [ -z "$SOURCE" ]; then
        SOURCE=$(pactl list sources short | grep -v monitor | head -1 | awk '{print $2}')
    fi
    
    if [ -z "$SOURCE" ]; then
        notify-send "❌ Whisper" "No se detectó micrófono\nConfigura en Configuración → Sonido"
        exit 1
    fi
    
    # Asegurar que el micrófono NO esté silenciado
    pactl set-source-mute "$SOURCE" 0 2>/dev/null
    
    # Subir volumen al 100% para micrófono USB
    pactl set-source-volume "$SOURCE" 100% 2>/dev/null
    
    # Usar parecord directamente (más confiable que parec+ffmpeg)
    parecord --device="$SOURCE" --format=s16le --rate=16000 --channels=1 "$AUDIO_FILE" 2>/dev/null &
    
    echo $! > "$RECORDING_FLAG"
    
    notify-send "🎤 Whisper" "Grabación iniciada\nPresiona el atajo nuevamente para transcribir"
}

# Función: Detener y transcribir
stop_and_transcribe() {
    if [ ! -f "$RECORDING_FLAG" ]; then
        notify-send "⚠️ Whisper" "No hay grabación activa"
        exit 1
    fi
    
    # Detener grabación
    PID=$(cat "$RECORDING_FLAG")
    kill -SIGINT $PID 2>/dev/null
    sleep 1
    kill -9 $PID 2>/dev/null
    rm "$RECORDING_FLAG"
    
    # Esperar a que se escriba el archivo
    sleep 0.5
    
    # Validar que hay audio grabado
    if [ ! -f "$AUDIO_FILE" ]; then
        notify-send "❌ Whisper" "Error: Archivo de audio no existe"
        exit 1
    fi
    
    FILE_SIZE=$(stat -c%s "$AUDIO_FILE" 2>/dev/null || echo 0)
    if [ "$FILE_SIZE" -lt 1000 ]; then
        notify-send "❌ Whisper" "Error: No se grabó audio\nTamaño: ${FILE_SIZE} bytes\nSube el volumen del micrófono"
        exit 1
    fi
    
    notify-send "⚡ Whisper GPU" "Procesando con RTX 3060...\n(Esto tomará 3-10 segundos)"
    
    # Activar entorno y transcribir
    source "$VENV_PATH/bin/activate"
    
    # Script de transcripción optimizado para RTX 3060
    TEMP_SCRIPT="/tmp/whisper_transcribe.py"
    cat > "$TEMP_SCRIPT" << 'PYTHON_EOF'
import sys
import time
from faster_whisper import WhisperModel

audio_file = sys.argv[1]

# Cargar modelo en GPU (RTX 3060)
model = WhisperModel(
    "large-v2",
    device="cuda",
    compute_type="float16",  # Óptimo para RTX 3060
    device_index=0,
    num_workers=4  # Aprovechar tu i7-11800H
)

start_time = time.time()

# Transcribir con configuración optimizada
segments, info = model.transcribe(
    audio_file,
    language="es",
    beam_size=5,
    best_of=5,
    temperature=0.0,
    vad_filter=True,  # Filtrar silencios
    vad_parameters=dict(
        threshold=0.5,
        min_speech_duration_ms=250,
        min_silence_duration_ms=500
    )
)

# Juntar segmentos
text = " ".join([segment.text.strip() for segment in segments])

elapsed = time.time() - start_time

# Imprimir resultado y tiempo
print(text)
print(f"[TIEMPO: {elapsed:.2f}s]", file=sys.stderr)
PYTHON_EOF
    
    # Ejecutar transcripción y capturar tiempo
    TRANSCRIPTION=$(python3 "$TEMP_SCRIPT" "$AUDIO_FILE" 2>&1 | tee "$LOG_FILE" | grep -v "^\[TIEMPO:")
    ELAPSED=$(grep "^\[TIEMPO:" "$LOG_FILE" | sed 's/.*TIEMPO: \(.*\)s\].*/\1/')
    
    if [ -z "$TRANSCRIPTION" ]; then
        notify-send "❌ Whisper" "No se detectó voz en el audio"
        rm -f "$AUDIO_FILE" "$TEMP_SCRIPT" "$LOG_FILE"
        exit 1
    fi
    
    # Copiar al portapapeles
    echo -n "$TRANSCRIPTION" | xclip -selection clipboard
    
    # Notificación con preview y tiempo
    PREVIEW=$(echo "$TRANSCRIPTION" | head -c 80)
    if [ -n "$ELAPSED" ]; then
        notify-send "✅ Whisper - Copiado (${ELAPSED}s)" "$PREVIEW..."
    else
        notify-send "✅ Whisper - Copiado" "$PREVIEW..."
    fi
    
    # Limpiar
    rm -f "$AUDIO_FILE" "$TEMP_SCRIPT" "$LOG_FILE"
}

# Toggle: grabar o transcribir
if [ -f "$RECORDING_FLAG" ]; then
    stop_and_transcribe
else
    start_recording
fi
