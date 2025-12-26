#!/bin/bash
# Script to resolve V2M secure paths for shell scripts
# Usage: source resolve_paths.sh

get_secure_runtime_dir() {
    local app_name="v2m"
    local runtime_dir=""

    if [[ -n "$XDG_RUNTIME_DIR" ]]; then
        runtime_dir="$XDG_RUNTIME_DIR/$app_name"
    else
        local uid=$(id -u)
        runtime_dir="/tmp/${app_name}_${uid}"
    fi
    echo "$runtime_dir"
}

V2M_RUNTIME_DIR=$(get_secure_runtime_dir)
V2M_SOCKET="$V2M_RUNTIME_DIR/v2m.sock"
V2M_PID_FILE="$V2M_RUNTIME_DIR/v2m_daemon.pid"
V2M_RECORDING_FLAG="$V2M_RUNTIME_DIR/v2m_recording.pid"
V2M_LOG_FILE="$V2M_RUNTIME_DIR/v2m_daemon.log"
