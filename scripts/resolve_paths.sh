#!/bin/bash
# resolve_paths.sh - Sets up secure runtime paths matching Python backend

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

# Get current user ID
CURRENT_UID=$(id -u)

# 1. Determine base runtime dir
if [ -n "${XDG_RUNTIME_DIR}" ]; then
    export V2M_RUNTIME_DIR="${XDG_RUNTIME_DIR}/v2m"
else
    export V2M_RUNTIME_DIR="/tmp/v2m_${CURRENT_UID}"
fi

# 2. Create and secure directory
if [ ! -d "${V2M_RUNTIME_DIR}" ]; then
    mkdir -p "${V2M_RUNTIME_DIR}"
    chmod 700 "${V2M_RUNTIME_DIR}"
else
    # Verify ownership
    # Use stat to get owner UID. Compatible with GNU stat.
    OWNER=$(stat -c '%u' "${V2M_RUNTIME_DIR}" 2>/dev/null)

    if [ "$?" -ne 0 ]; then
         # Fallback for systems where stat might fail or differ
         echo "⚠️ Warning: Could not verify ownership of ${V2M_RUNTIME_DIR}" >&2
    elif [ "${OWNER}" != "${CURRENT_UID}" ]; then
        echo "❌ CRITICAL SECURITY ERROR: Runtime directory ${V2M_RUNTIME_DIR} is owned by user ${OWNER}, but you are ${CURRENT_UID}." >&2
        echo "   This could be a security attack (symlink/pre-creation)." >&2
        exit 1
    fi

    # Enforce 700 permissions
    chmod 700 "${V2M_RUNTIME_DIR}"
fi

# 3. Export specific paths
export V2M_LOG_FILE="${V2M_RUNTIME_DIR}/v2m_daemon.log"
export V2M_PID_FILE="${V2M_RUNTIME_DIR}/v2m_daemon.pid"
export V2M_SOCKET_FILE="${V2M_RUNTIME_DIR}/v2m.sock"
export V2M_RECORDING_FLAG="${V2M_RUNTIME_DIR}/v2m_recording.pid"
export V2M_AUDIO_FILE="${V2M_RUNTIME_DIR}/v2m_audio.wav"
