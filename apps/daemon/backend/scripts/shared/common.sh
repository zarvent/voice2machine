#!/bin/bash

# Shared utilities for BASH scripts.
# State-of-the-Art 2026 Scripting Standards

# 1. Path Discovery (Nested Monorepo Support)
# current dir: apps/daemon/backend/scripts/shared
COMMON_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Backend Dir: /home/zarvent/developer/v2m-lab/apps/daemon/backend (2 levels up from scripts/shared)
BACKEND_DIR="$( cd "${COMMON_SCRIPT_DIR}/../.." &> /dev/null && pwd )"

# Repo Root: /home/zarvent/developer/v2m-lab (5 levels up from scripts/shared)
REPO_ROOT="$( cd "${COMMON_SCRIPT_DIR}/../../../../.." &> /dev/null && pwd )"

# Compatibility aliases
PROJECT_ROOT="${REPO_ROOT}"
PROJECT_DIR="${BACKEND_DIR}"

# 3. Virtual Environment Management
activate_venv() {
    local venv_path="${BACKEND_DIR}/venv"
    if [ -f "${venv_path}/bin/activate" ]; then
        source "${venv_path}/bin/activate"
    elif [ -f "${REPO_ROOT}/venv/bin/activate" ]; then
        # Fallback to root venv if backend one is missing
        source "${REPO_ROOT}/venv/bin/activate"
    else
        return 1
    fi
}
