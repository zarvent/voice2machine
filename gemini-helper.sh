#!/bin/bash
# Script de ayuda para whisper-dictation con Gemini

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"

show_help() {
    cat << EOF
🎤 Whisper Dictation - Sistema de Dictado con IA

USO:
    $0 [comando]

COMANDOS:
    setup       - Instalar y configurar el entorno
    test        - Probar el procesador de texto con Gemini
    process     - Procesar el portapapeles actual
    config      - Mostrar la configuración actual
    logs        - Mostrar los últimos logs
    help        - Mostrar esta ayuda

EJEMPLOS:
    $0 setup              # Primera instalación
    $0 test               # Probar que Gemini funciona
    $0 process            # Procesar texto del portapapeles

CONFIGURACIÓN:
    Las variables de entorno están en: $SCRIPT_DIR/.env
    Edita ese archivo para cambiar el modelo, temperatura, etc.

EOF
}

setup_env() {
    echo "🔧 Configurando entorno virtual..."

    if [ ! -d "$VENV_PATH" ]; then
        python3 -m venv "$VENV_PATH"
        echo "✅ Entorno virtual creado"
    else
        echo "ℹ️  Entorno virtual ya existe"
    fi

    echo "📦 Instalando dependencias..."
    "$VENV_PATH/bin/pip" install -q --upgrade pip
    "$VENV_PATH/bin/pip" install -q google-genai python-dotenv tenacity

    echo "✅ Dependencias instaladas"

    # Verificar .env
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo "⚠️  No se encontró el archivo .env"
        echo "Creando plantilla..."
        cat > "$SCRIPT_DIR/.env" << 'ENVEOF'
# API de Google Gemini
GEMINI_API_KEY="TU_API_KEY_AQUI"
LLM_PROVIDER="gemini"
LLM_MODEL="models/gemini-2.5-flash"
LLM_TEMPERATURE="0.3"
LLM_MAX_TOKENS="2048"
ENVEOF
        echo "⚠️  Por favor edita $SCRIPT_DIR/.env y agrega tu GEMINI_API_KEY"
    else
        echo "✅ Archivo .env encontrado"
    fi

    echo ""
    echo "✨ Configuración completada!"
    echo "   Ejecuta: $0 test para probar el sistema"
}

test_processor() {
    echo "🧪 Probando el procesador de texto con Gemini..."
    echo ""

    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo "❌ Error: No se encontró el archivo .env"
        echo "   Ejecuta: $0 setup"
        exit 1
    fi

    TEST_TEXT="Hola esto es una prueba del sistema de procesamiento de texto con Gemini"

    echo "📝 Texto de prueba:"
    echo "   $TEST_TEXT"
    echo ""
    echo "⏳ Procesando..."

    RESULT=$(echo "$TEST_TEXT" | "$VENV_PATH/bin/python3" "$SCRIPT_DIR/llm_processor.py" 2>&1)
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "✅ Procesamiento exitoso!"
        echo "📤 Resultado:"
        echo "   $RESULT"
    else
        echo ""
        echo "❌ Error al procesar:"
        echo "$RESULT"
        exit 1
    fi
}

process_clipboard() {
    echo "📋 Procesando portapapeles..."

    CLIPBOARD=$(xclip -selection clipboard -o 2>/dev/null || echo "")

    if [ -z "$CLIPBOARD" ]; then
        echo "❌ Error: Portapapeles vacío"
        exit 1
    fi

    echo "📝 Texto original (${#CLIPBOARD} caracteres)"
    echo "⏳ Procesando con Gemini..."

    RESULT=$(echo "$CLIPBOARD" | "$VENV_PATH/bin/python3" "$SCRIPT_DIR/llm_processor.py" 2>/dev/null)
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo -n "$RESULT" | xclip -selection clipboard
        echo "✅ Texto procesado y copiado al portapapeles (${#RESULT} caracteres)"
    else
        echo "❌ Error al procesar el texto"
        exit 1
    fi
}

show_config() {
    echo "⚙️  Configuración actual:"
    echo ""

    if [ -f "$SCRIPT_DIR/.env" ]; then
        grep -v "^#" "$SCRIPT_DIR/.env" | grep -v "^$"
    else
        echo "❌ No se encontró el archivo .env"
    fi

    echo ""
    echo "📁 Ruta del entorno virtual: $VENV_PATH"
    echo "📄 Procesador: $SCRIPT_DIR/llm_processor.py"
}

show_logs() {
    LOG_FILE="$SCRIPT_DIR/logs/llm.log"

    if [ -f "$LOG_FILE" ]; then
        echo "📋 Últimos logs:"
        echo ""
        tail -n 20 "$LOG_FILE"
    else
        echo "ℹ️  No hay logs disponibles"
    fi
}

# Main
case "${1:-}" in
    setup)
        setup_env
        ;;
    test)
        test_processor
        ;;
    process)
        process_clipboard
        ;;
    config)
        show_config
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "❌ Comando desconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
