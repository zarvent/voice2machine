import sys
import time
import signal
import argparse
from pathlib import Path
# Add src to path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from whisper_dictation.audio.recorder import AudioRecorder
from whisper_dictation.config import config

# Setup signal handling
stop_requested = False

def signal_handler(sig, frame):
    global stop_requested
    stop_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    recorder = AudioRecorder()
    try:
        recorder.start()
        print("Recording started", flush=True)
    except Exception as e:
        print(f"Error starting recording: {e}", file=sys.stderr)
        sys.exit(1)

    while not stop_requested:
        time.sleep(0.1)

    print("Stopping recording...", flush=True)
    recorder.stop(save_path=Path(args.output))
    print(f"Saved to {args.output}", flush=True)

if __name__ == "__main__":
    main()
