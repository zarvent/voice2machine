import os
import sys
from pathlib import Path
import subprocess

SERVICE_NAME = "whisper-dictation.service"
USER_HOME = Path.home()
SYSTEMD_USER_DIR = USER_HOME / ".config/systemd/user"
SOURCE_SERVICE_FILE = Path("whisper-dictation.service")

def install_service():
    print(f"Installing {SERVICE_NAME}...")

    # 1. Ensure destination directory exists
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Read template and substitute variables
    with open(SOURCE_SERVICE_FILE, "r") as f:
        content = f.read()

    # Replace %u (User) and %h (Home) explicitly if needed,
    # but systemd handles %u and %h in user units automatically usually.
    # However, for ExecStart, it's safer to use absolute paths.

    # Let's resolve the absolute path of the current directory
    current_dir = Path.cwd().resolve()
    venv_python = current_dir / "venv/bin/python"

    # We'll replace the generic ExecStart with the concrete path
    # content = content.replace("%h/whisper-dictation", str(current_dir))
    # Actually, let's just rewrite the file with the correct paths

    service_content = f"""[Unit]
Description=Whisper Dictation Daemon
After=network.target sound.target

[Service]
Type=simple
WorkingDirectory={current_dir}
ExecStart={venv_python} -m whisper_dictation.main --daemon
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
# NOTE: You need to ensure GEMINI_API_KEY is available.
# You can add Environment="GEMINI_API_KEY=xyz" here or use `systemctl --user import-environment`

[Install]
WantedBy=default.target
"""

    dest_file = SYSTEMD_USER_DIR / SERVICE_NAME
    with open(dest_file, "w") as f:
        f.write(service_content)

    print(f"Service file written to {dest_file}")

    # 3. Reload systemd
    print("Reloading systemd daemon...")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)

    # 4. Enable service
    print("Enabling service...")
    subprocess.run(["systemctl", "--user", "enable", SERVICE_NAME], check=True)

    print("\n✅ Installation Complete!")
    print(f"To start the service run: systemctl --user start {SERVICE_NAME}")
    print(f"To check status run: systemctl --user status {SERVICE_NAME}")
    print(f"To view logs run: journalctl --user -u {SERVICE_NAME} -f")

if __name__ == "__main__":
    install_service()
