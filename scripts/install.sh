#!/usr/bin/env bash
# =============================================================================
# install.sh - Voice2Machine automated setup script
# =============================================================================
# Automates:
#   1. OS detection (Linux only for now)
#   2. System dependencies via apt
#   3. Python venv creation
#   4. pip install from requirements.txt
#   5. .env configuration for GEMINI_API_KEY
#   6. GPU verification
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
# 1. OS detection
# -----------------------------------------------------------------------------
check_os() {
    log_info "checking operating system..."

    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "this script only supports Linux for now."
        log_warn "detected: $OSTYPE"
        log_warn "for macOS/Windows, see docs/en/installation.md for manual setup."
        exit 1
    fi

    log_success "linux detected"
}

# -----------------------------------------------------------------------------
# 2. system dependencies
# -----------------------------------------------------------------------------
install_system_deps() {
    log_info "installing system dependencies..."

    local deps=(ffmpeg xclip pulseaudio-utils python3-venv build-essential python3-dev)
    local missing=()

    for dep in "${deps[@]}"; do
        if ! dpkg -l "$dep" &>/dev/null; then
            missing+=("$dep")
        fi
    done

    if [[ ${#missing[@]} -eq 0 ]]; then
        log_success "all system dependencies installed"
        return
    fi

    log_info "installing: ${missing[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y "${missing[@]}"

    log_success "system dependencies installed"
}

# -----------------------------------------------------------------------------
# 3. python virtual environment
# -----------------------------------------------------------------------------
setup_venv() {
    log_info "setting up python virtual environment..."

    if [[ -d "venv" ]]; then
        log_warn "venv already exists, skipping creation"
    else
        python3 -m venv venv
        log_success "venv created"
    fi

    # shellcheck disable=SC1091
    source venv/bin/activate
    log_success "venv activated"
}

# -----------------------------------------------------------------------------
# 4. python dependencies
# -----------------------------------------------------------------------------
install_python_deps() {
    log_info "installing python dependencies..."

    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    log_success "python dependencies installed"
}

# -----------------------------------------------------------------------------
# 5. configure .env
# -----------------------------------------------------------------------------
configure_env() {
    log_info "configuring environment variables..."

    if [[ -f ".env" ]]; then
        log_warn ".env already exists, skipping"
        return
    fi

    echo ""
    echo -e "${YELLOW}===========================================${NC}"
    echo -e "${YELLOW}  Google Gemini API Key Setup${NC}"
    echo -e "${YELLOW}===========================================${NC}"
    echo ""
    echo "get your free API key at: https://aistudio.google.com/"
    echo ""
    read -rp "enter your GEMINI_API_KEY (or press Enter to skip): " api_key

    if [[ -z "$api_key" ]]; then
        log_warn "skipped API key setup - you can add it later to .env"
        cp .env.example .env 2>/dev/null || echo "GEMINI_API_KEY=" > .env
    else
        echo "GEMINI_API_KEY=$api_key" > .env
        log_success ".env configured"
    fi
}

# -----------------------------------------------------------------------------
# 6. verify GPU
# -----------------------------------------------------------------------------
verify_gpu() {
    log_info "verifying GPU acceleration..."

    if python scripts/check_cuda.py 2>/dev/null; then
        log_success "GPU acceleration available"
    else
        log_warn "GPU not detected - whisper will run on CPU (slower)"
        log_warn "for NVIDIA GPU support, install CUDA drivers"
    fi
}

# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Voice2Machine Installer${NC}"
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
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "next steps:"
    echo "  1. activate venv:  source venv/bin/activate"
    echo "  2. run daemon:     python scripts/v2m-daemon.sh"
    echo "  3. bind shortcuts: see docs/instalacion.md"
    echo ""
}

main "$@"
