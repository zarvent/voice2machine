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
# repair_libs.sh - script de reparación de librerías nvidia
#
# descripción
#   este script repara problemas comunes con las librerías nvidia
#   (cudnn cublas) reinstalando las versiones compatibles con
#   faster-whisper y ctranslate2
#
# uso
#   ./scripts/repair_libs.sh
#
# operaciones realizadas
#   1 desinstala paquetes conflictivos
#      - nvidia-cudnn-cu12
#      - nvidia-cublas-cu12
#      - faster-whisper
#      - ctranslate2
#   2 reinstala versiones compatibles
#      - nvidia-cudnn-cu12 (compatible con cudnn 9.x)
#      - nvidia-cublas-cu12
#      - faster-whisper (trae ctranslate2 compatible)
#
# cuándo usar
#   - error "could not load library libcudnn_ops.so.9"
#   - error "cudnn version mismatch"
#   - transcripción falla en gpu pero funciona en cpu
#   - después de actualizar drivers nvidia
#
# requisitos
#   - entorno virtual activado (source venv/bin/activate)
#   - conexión a internet para descargar paquetes
#   - ~3gb de espacio libre para descargas temporales
#
# advertencias
#   - el script usa 'set -e' se detiene ante cualquier error
#   - puede tomar varios minutos dependiendo de la conexión
#   - ejecutar desde la raíz del proyecto
#
# verificación post-reparación
#   python scripts/check_cuda.py
#   python scripts/test_whisper_standalone.py
#
# autor
#   voice2machine team
#
# desde
#   v1.0.0
#

set -e

echo "🔧 reparando instalación de librerías nvidia..."

source venv/bin/activate

# desinstalar paquetes conflictivos
pip uninstall -y nvidia-cudnn-cu12 nvidia-cublas-cu12 faster-whisper ctranslate2

# reinstalar versiones compatibles
# faster-whisper 1.2.1 trae ctranslate2 4.6.1
# ctranslate2 4.6.1 funciona bien con cudnn 9.x si se configura bien
pip install nvidia-cudnn-cu12 nvidia-cublas-cu12 faster-whisper

echo "✅ reinstalación completada"
