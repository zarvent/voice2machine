import sys
import time
import signal
import argparse
from pathlib import Path
# añadir src a la ruta para permitir importaciones
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from v2m.infrastructure.audio.recorder import AudioRecorder
from v2m.config import config

# configurar el manejo de señales
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
        print("grabación iniciada", flush=True)
    except Exception as e:
        print(f"error al iniciar la grabación {e}", file=sys.stderr)
        sys.exit(1)

    while not stop_requested:
        time.sleep(0.1)

    print("deteniendo la grabación...", flush=True)
    recorder.stop(save_path=Path(args.output))
    print(f"guardado en {args.output}", flush=True)

if __name__ == "__main__":
    main()
