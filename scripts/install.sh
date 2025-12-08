#!/usr/bin/env bash
# =============================================================================
# install.sh - SCRIPT DE INSTALACIÓN AUTOMATIZADA DE VOICE2MACHINE
# =============================================================================
# AUTOMATIZA
#   1. detección del so (solo linux por ahora)
#   2. dependencias del sistema via apt
#   3. creación del entorno virtual de python
#   4. instalación de pip desde requirements.txt
#   5. configuración de .env para gemini_api_key
#   6. verificación de gpu
# =============================================================================

set -euo pipefail

# colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # no color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# -----------------------------------------------------------------------------
# 1. DETECCIÓN DEL SO
# -----------------------------------------------------------------------------
check_os() {
    log_info "verificando sistema operativo..."

    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "este script solo soporta linux por ahora"
        log_warn "detectado: $OSTYPE"
        log_warn "para macos/windows ver docs/en/installation.md para instalación manual"
        exit 1
    fi

    log_success "linux detectado"
}

# -----------------------------------------------------------------------------
# 2. DEPENDENCIAS DEL SISTEMA
# -----------------------------------------------------------------------------
install_system_deps() {
    log_info "instalando dependencias del sistema..."

    local deps=(ffmpeg xclip pulseaudio-utils python3-venv build-essential python3-dev)
    local missing=()

    for dep in "${deps[@]}"; do
        if ! dpkg -l "$dep" &>/dev/null; then
            missing+=("$dep")
        fi
    done

    if [[ ${#missing[@]} -eq 0 ]]; then
        log_success "todas las dependencias del sistema instaladas"
        return
    fi

    log_info "instalando: ${missing[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y "${missing[@]}"

    log_success "dependencias del sistema instaladas"
}

# -----------------------------------------------------------------------------
# 3. ENTORNO VIRTUAL DE PYTHON
# -----------------------------------------------------------------------------
setup_venv() {
    log_info "configurando entorno virtual de python..."

    if [[ -d "venv" ]]; then
        log_warn "el venv ya existe saltando creación"
    else
        python3 -m venv venv
        log_success "venv creado"
    fi

    # shellcheck disable=SC1091
    source venv/bin/activate
    log_success "venv activado"
}

# -----------------------------------------------------------------------------
# 4. DEPENDENCIAS DE PYTHON
# -----------------------------------------------------------------------------
install_python_deps() {
    log_info "instalando dependencias de python..."

    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    log_success "dependencias de python instaladas"
}

# -----------------------------------------------------------------------------
# 5. CONFIGURAR .ENV
# -----------------------------------------------------------------------------
configure_env() {
    log_info "configurando variables de entorno..."

    if [[ -f ".env" ]]; then
        log_warn ".env ya existe saltando"
        return
    fi

    echo ""
    echo -e "${YELLOW}===========================================${NC}"
    echo -e "${YELLOW}  configuración de api key de google gemini${NC}"
    echo -e "${YELLOW}===========================================${NC}"
    echo ""
    echo "obtén tu api key gratuita en: https://aistudio.google.com/"
    echo ""
    read -rp "ingresa tu GEMINI_API_KEY (o presiona enter para saltar): " api_key

    if [[ -z "$api_key" ]]; then
        log_warn "saltando configuración de api key - puedes agregarla después en .env"
        cp .env.example .env 2>/dev/null || echo "GEMINI_API_KEY=" > .env
    else
        echo "GEMINI_API_KEY=$api_key" > .env
        log_success ".env configurado"
    fi
}

# -----------------------------------------------------------------------------
# 6. VERIFICAR GPU
# -----------------------------------------------------------------------------
verify_gpu() {
    log_info "verificando aceleración por gpu..."

    if python scripts/check_cuda.py 2>/dev/null; then
        log_success "aceleración por gpu disponible"
    else
        log_warn "gpu no detectada - whisper correrá en cpu (más lento)"
        log_warn "para soporte de nvidia gpu instala drivers cuda"
    fi
}

# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  instalador de voice2machine${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    check_os
    install_system_deps
    setup_venv
    install_python_deps
    configure_env
    verify_gpu

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  instalación completa${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "siguientes pasos:"
    echo "  1. activar venv:  source venv/bin/activate"
    echo "  2. ejecutar daemon:     python scripts/v2m-daemon.sh"
    echo "  3. asignar atajos: ver docs/instalacion.md"
    echo ""
}

main "$@"
