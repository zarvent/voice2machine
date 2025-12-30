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
# Script de limpieza para eliminar procesos zombie de v2m
# Uso: ./scripts/cleanup_v2m.sh [--force]

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

echo -e "${YELLOW}🧹 V2M Cleanup Script${NC}"
echo "======================================"

# --- RUTAS SEGURAS ---
if [ -n "${XDG_RUNTIME_DIR}" ]; then
    RUNTIME_DIR="${XDG_RUNTIME_DIR}/v2m"
else
    # Fallback seguro a /tmp/v2m_<uid>
    UID_VAL=$(id -u)
    RUNTIME_DIR="/tmp/v2m_${UID_VAL}"
fi

# 1. Buscar procesos v2m
echo -e "\n${YELLOW}[1/4]${NC} Buscando procesos v2m..."
# Excluir este script para no matarse a sí mismo (pgrep -f busca en cmdline)
PIDS=$(pgrep -f "v2m" | grep -v "$$" || true)

if [[ -z "$PIDS" ]]; then
    echo -e "${GREEN}✅ No se encontraron procesos v2m corriendo${NC}"
else
    echo -e "${RED}⚠️  Procesos v2m encontrados:${NC}"
    ps aux | grep "v2m" | grep -v grep | grep -v "cleanup_v2m.sh"

    if [[ "$FORCE" == "true" ]]; then
        echo -e "\n${YELLOW}Matando procesos...${NC}"
        # Usar kill en lugar de pkill para ser más preciso con los PIDs encontrados
        echo "$PIDS" | xargs kill -9 || true
        echo -e "${GREEN}✅ Procesos eliminados${NC}"
    else
        echo -e "\n${YELLOW}Usa --force para eliminarlos automáticamente${NC}"
        read -p "¿Matar estos procesos? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$PIDS" | xargs kill -9 || true
            echo -e "${GREEN}✅ Procesos eliminados${NC}"
        fi
    fi
fi

# 2. Limpiar socket huérfano (incluyendo ruta segura y legacy)
echo -e "\n${YELLOW}[2/4]${NC} Verificando sockets Unix..."

# Limpiar ruta segura
SOCKET_PATH="${RUNTIME_DIR}/v2m.sock"
if [[ -S "${SOCKET_PATH}" ]]; then
    echo -e "${YELLOW}Socket encontrado en ${SOCKET_PATH}, eliminando...${NC}"
    rm -f "${SOCKET_PATH}"
fi

# Limpiar ruta legacy (por si acaso hubo una actualización desde versión vulnerable)
if [[ -S /tmp/v2m.sock ]]; then
    echo -e "${YELLOW}Socket LEGACY encontrado en /tmp/v2m.sock, eliminando...${NC}"
    rm -f /tmp/v2m.sock
fi

echo -e "${GREEN}✅ Sockets limpios${NC}"

# 3. Limpiar PID file (seguro y legacy)
echo -e "\n${YELLOW}[3/4]${NC} Verificando PID files..."

PID_PATH="${RUNTIME_DIR}/v2m_daemon.pid"
if [[ -f "${PID_PATH}" ]]; then
    echo -e "${YELLOW}PID file encontrado en ${PID_PATH}, eliminando...${NC}"
    rm -f "${PID_PATH}"
fi

if [[ -f /tmp/v2m_daemon.pid ]]; then
    echo -e "${YELLOW}PID file LEGACY encontrado en /tmp/v2m_daemon.pid, eliminando...${NC}"
    rm -f /tmp/v2m_daemon.pid
fi

echo -e "${GREEN}✅ PID files limpios${NC}"

# 4. Verificar VRAM
echo -e "\n${YELLOW}[4/4]${NC} Verificando uso de VRAM..."
if command -v nvidia-smi &> /dev/null; then
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    VRAM_FREE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits)

    echo -e "VRAM Usada: ${VRAM_USED}MiB"
    echo -e "VRAM Libre: ${VRAM_FREE}MiB"

    if [[ $VRAM_USED -lt 500 ]]; then
        echo -e "${GREEN}✅ VRAM limpia (< 500MiB)${NC}"
    else
        echo -e "${YELLOW}⚠️  VRAM en uso (${VRAM_USED}MiB) - puede ser normal si el daemon está corriendo${NC}"
    fi
else
    echo -e "${YELLOW}nvidia-smi no disponible, saltando...${NC}"
fi

echo -e "\n${GREEN}======================================"
echo -e "✅ Limpieza completada${NC}"
