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
# SCRIPT DE LIMPIEZA PARA ELIMINAR PROCESOS ZOMBIE DE V2M
# USO: ./scripts/cleanup_v2m.sh [--force]

set -euo pipefail

# colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # no color

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

echo -e "${YELLOW}🧹 script de limpieza v2m${NC}"
echo "======================================"

# 1. buscar procesos v2m
echo -e "\n${YELLOW}[1/4]${NC} buscando procesos v2m..."
PIDS=$(pgrep -f "v2m" || true)

if [[ -z "$PIDS" ]]; then
    echo -e "${GREEN}✅ no se encontraron procesos v2m corriendo${NC}"
else
    echo -e "${RED}⚠️  procesos v2m encontrados:${NC}"
    ps aux | grep "v2m" | grep -v grep | grep -v "cleanup_v2m.sh"

    if [[ "$FORCE" == "true" ]]; then
        echo -e "\n${YELLOW}matando procesos...${NC}"
        pkill -9 -f "v2m" || true
        echo -e "${GREEN}✅ procesos eliminados${NC}"
    else
        echo -e "\n${YELLOW}usa --force para eliminarlos automáticamente${NC}"
        read -p "¿matar estos procesos? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pkill -9 -f "v2m" || true
            echo -e "${GREEN}✅ procesos eliminados${NC}"
        fi
    fi
fi

# 2. limpiar socket huérfano
echo -e "\n${YELLOW}[2/4]${NC} verificando socket unix..."
if [[ -S /tmp/v2m.sock ]]; then
    echo -e "${YELLOW}socket encontrado eliminando...${NC}"
    rm -f /tmp/v2m.sock
    echo -e "${GREEN}✅ socket eliminado${NC}"
else
    echo -e "${GREEN}✅ no hay socket huérfano${NC}"
fi

# 3. limpiar pid file
echo -e "\n${YELLOW}[3/4]${NC} verificando pid file..."
if [[ -f /tmp/v2m_daemon.pid ]]; then
    echo -e "${YELLOW}pid file encontrado eliminando...${NC}"
    rm -f /tmp/v2m_daemon.pid
    echo -e "${GREEN}✅ pid file eliminado${NC}"
else
    echo -e "${GREEN}✅ no hay pid file huérfano${NC}"
fi

# 4. verificar vram
echo -e "\n${YELLOW}[4/4]${NC} verificando uso de vram..."
if command -v nvidia-smi &> /dev/null; then
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    VRAM_FREE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits)

    echo -e "vram usada: ${VRAM_USED}mib"
    echo -e "vram libre: ${VRAM_FREE}mib"

    if [[ $VRAM_USED -lt 500 ]]; then
        echo -e "${GREEN}✅ vram limpia (< 500mib)${NC}"
    else
        echo -e "${YELLOW}⚠️  vram en uso (${VRAM_USED}mib) - puede ser normal si el daemon está corriendo${NC}"
    fi
else
    echo -e "${YELLOW}nvidia-smi no disponible saltando...${NC}"
fi

echo -e "\n${GREEN}======================================"
echo -e "✅ limpieza completada${NC}"
