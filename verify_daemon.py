import subprocess
import time
import sys
import os

# Path to python executable
PYTHON = sys.executable
DAEMON_SCRIPT = "src/whisper_dictation/daemon.py"
CLIENT_SCRIPT = "src/whisper_dictation/client.py"

def run_client(*args):
    cmd = [PYTHON, CLIENT_SCRIPT] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

print("Starting Daemon...")
daemon_process = subprocess.Popen(
    [PYTHON, DAEMON_SCRIPT],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Give it time to start
time.sleep(10)

try:
    print("Sending PING...")
    stdout, stderr, code = run_client("PING")

    if code != 0:
        print(f"Client failed: {stderr}")
        sys.exit(1)

    if stdout == "PONG":
        print("SUCCESS: Received PONG")
    else:
        print(f"FAILURE: Received '{stdout}', expected 'PONG'")
        sys.exit(1)

    print("Sending START_RECORDING...")
    stdout, stderr, code = run_client("START_RECORDING")
    if code != 0:
        print(f"START_RECORDING failed: {stderr}")
    else:
        print("Recording started.")

    time.sleep(3)

    print("Sending STOP_RECORDING...")
    stdout, stderr, code = run_client("STOP_RECORDING")
    if code != 0:
        print(f"STOP_RECORDING failed: {stderr}")
    else:
        print("Recording stopped. Transcription should be in clipboard.")

    time.sleep(1)

    print("Sending PROCESS_TEXT (Testing Gemini Fallback)...")
    test_text = "This is a test for Gemini Fallback"
    stdout, stderr, code = run_client("PROCESS_TEXT", test_text)
    if code != 0:
        print(f"PROCESS_TEXT failed: {stderr}")
    else:
        print(f"PROCESS_TEXT response: {stdout}")
        print("Check clipboard or notifications for result.")

finally:
    print("Shutting down Daemon...")
    run_client("SHUTDOWN")
    daemon_process.terminate()
    daemon_process.wait()

    stdout, stderr = daemon_process.communicate()
    if stdout: print(f"Daemon STDOUT:\n{stdout.decode()}")
    if stderr: print(f"Daemon STDERR:\n{stderr.decode()}")
