#!/bin/bash
set -e

echo "🔧 Reparando instalación de librerías NVIDIA..."

source venv/bin/activate

# Desinstalar paquetes conflictivos
pip uninstall -y nvidia-cudnn-cu12 nvidia-cublas-cu12 faster-whisper ctranslate2

# Reinstalar versiones compatibles
# faster-whisper 1.2.1 trae ctranslate2 4.6.1
# ctranslate2 4.6.1 funciona bien con cudnn 9.x si se configura bien
pip install nvidia-cudnn-cu12 nvidia-cublas-cu12 faster-whisper

echo "✅ Reinstalación completada."
