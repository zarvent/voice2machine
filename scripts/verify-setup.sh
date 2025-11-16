#!/bin/bash

echo "🔍 Verificando setup de Whisper..."
echo "=================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES=0

# 1. Verificar venv
echo -n "✓ Entorno virtual: "
if [ -d "$HOME/whisper-dictation/venv" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALLO${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 2. Verificar faster-whisper
echo -n "✓ Faster-Whisper instalado: "
if source "$HOME/whisper-dictation/venv/bin/activate" 2>/dev/null && python3 -c "import faster_whisper" 2>/dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALLO${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 3. Verificar CUDA
echo -n "✓ CUDA disponible: "
if source "$HOME/whisper-dictation/venv/bin/activate" 2>/dev/null && python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}NO (Verificar CUDA)${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 4. Verificar LD_LIBRARY_PATH
echo -n "✓ LD_LIBRARY_PATH configurado: "
if source "$HOME/whisper-dictation/venv/bin/activate" 2>/dev/null && [ -n "$LD_LIBRARY_PATH" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}VACIO (Se configurará al activar)${NC}"
fi

# 5. Verificar script principal
echo -n "✓ Script whisper-toggle.sh: "
if [ -x "$HOME/whisper-dictation/whisper-toggle.sh" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALLO${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 6. Verificar atajo de teclado
echo -n "✓ Atajo de teclado Ctrl+Shift+Space: "
if gsettings get org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/whisper0/ command 2>/dev/null | grep -q "whisper-toggle.sh"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}NO CONFIGURADO${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 7. Verificar micrófono
echo -n "✓ Micrófono detectado: "
if pactl info | grep -q "Default Source"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}NO O NO CONFIGURADO${NC}"
fi

# 8. Verificar ffmpeg
echo -n "✓ FFmpeg instalado: "
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALLO${NC}"
    ISSUES=$((ISSUES + 1))
fi

# 9. Verificar xclip
echo -n "✓ xclip instalado: "
if command -v xclip &> /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FALLO${NC}"
    ISSUES=$((ISSUES + 1))
fi

echo "=================================="

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✨ ¡Setup completamente funcional!${NC}"
    echo ""
    echo "Próximos pasos:"
    echo "1. Presiona Ctrl+Shift+Space para grabar"
    echo "2. Habla claramente en español"
    echo "3. Presiona Ctrl+Shift+Space nuevamente para transcribir"
    echo "4. Ctrl+V para pegar el resultado"
else
    echo -e "${RED}⚠️  Se encontraron $ISSUES problema(s)${NC}"
    echo ""
    echo "Para reinstalar:"
    echo "cd ~/whisper-dictation"
    echo "rm -rf venv/"
    echo "python3 -m venv venv"
    echo "source venv/bin/activate"
    echo "pip install --upgrade pip setuptools wheel"
    echo "pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 faster-whisper"
fi
