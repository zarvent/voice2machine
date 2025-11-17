"""
Módulo que implementa el servicio de transcripción utilizando `faster-whisper`.

Esta es la implementación concreta de la interfaz `TranscriptionService`. Se encarga
de la lógica de bajo nivel para:
-   Interactuar con el sistema de audio (PulseAudio) a través de `parecord` y `pactl`.
-   Gestionar el proceso de grabación de audio.
-   Cargar el modelo de WHISPER.
-   Realizar la transcripción del archivo de audio grabado.
"""

import time
import subprocess
from pathlib import Path
from typing import Optional
from faster_whisper import WhisperModel
from whisper_dictation.application.transcription_service import TranscriptionService
from whisper_dictation.config import config
from whisper_dictation.domain.errors import MicrophoneNotFoundError, RecordingError
from whisper_dictation.core.logging import logger

class WhisperTranscriptionService(TranscriptionService):
    """
    Implementación del `TranscriptionService` que usa `faster-whisper` y `parecord`.
    """
    def __init__(self) -> None:
        """
        Inicializa el servicio de transcripción.

        Configura las rutas para el archivo de audio temporal y el archivo "flag"
        que indica si una grabación está en curso. No carga el modelo de WHISPER
        en este punto para acelerar el inicio de la aplicación.
        """
        self._model: Optional[WhisperModel] = None
        self._paths = config['paths']
        self._recording_flag = Path(self._paths['recording_flag'])
        self._audio_file = Path(self._paths['audio_file'])

    @property
    def model(self) -> WhisperModel:
        """
        Carga el modelo de `faster-whisper` de forma perezosa (lazy loading).

        El modelo solo se carga en memoria la primera vez que se accede a esta
        propiedad. Esto evita un consumo de recursos innecesario si solo se
        inicia la grabación sin completarla.

        Returns:
            La instancia del modelo de WHISPER cargado.
        """
        if self._model is None:
            logger.info("cargando modelo de WHISPER...")
            whisper_config = config['whisper']
            self._model = WhisperModel(
                whisper_config['model'],
                device=whisper_config['device'],
                compute_type=whisper_config['compute_type'],
                device_index=whisper_config['device_index'],
                num_workers=whisper_config['num_workers']
            )
            logger.info("modelo de WHISPER cargado")
        return self._model

    def start_recording(self) -> None:
        """
        Inicia la grabación de audio.

        Realiza los siguientes pasos:
        1.  Verifica que no haya otra grabación en curso.
        2.  Detecta el micrófono por defecto usando `pactl`.
        3.  Asegura que el micrófono no esté silenciado y tenga el volumen al 100%.
        4.  Inicia un proceso `parecord` en segundo plano para grabar el audio.
        5.  Crea un archivo "flag" que contiene el PID (Process ID) del proceso
            de grabación para poder detenerlo más tarde.

        Raises:
            RecordingError: Si ya hay una grabación en proceso.
            MicrophoneNotFoundError: Si no se puede detectar un micrófono.
        """
        if self._recording_flag.exists():
            raise RecordingError("ya hay una grabación en proceso")

        if self._audio_file.exists():
            self._audio_file.unlink()

        # --- detección de micrófono ---
        source = subprocess.getoutput("pactl get-default-source")
        if not source:
            source = subprocess.getoutput("pactl list sources short | grep -v monitor | head -1 | awk '{print $2}'")

        if not source:
            raise MicrophoneNotFoundError("no se detectó ningún micrófono")

        # --- inicio del proceso de grabación ---
        subprocess.run(["pactl", "set-source-mute", source, "0"])
        subprocess.run(["pactl", "set-source-volume", source, "100%"])

        process = subprocess.Popen([
            "parecord",
            f"--device={source}",
            "--format=s16le",
            "--rate=16000",
            "--channels=1",
            str(self._audio_file)
        ], stderr=subprocess.DEVNULL)

        with open(self._recording_flag, 'w') as f:
            f.write(str(process.pid))
        logger.info("grabación iniciada")

    def stop_and_transcribe(self) -> str:
        """
        Detiene la grabación y transcribe el audio.

        Realiza los siguientes pasos:
        1.  Lee el PID del proceso de grabación desde el archivo "flag".
        2.  Envía señales `SIGINT` y `SIGKILL` para detener el proceso `parecord`.
        3.  Elimina el archivo "flag".
        4.  Verifica que se haya grabado un archivo de audio válido.
        5.  Utiliza el modelo de WHISPER para transcribir el audio.
        6.  Limpia el archivo de audio temporal.

        Returns:
            El texto transcrito.

        Raises:
            RecordingError: Si no hay una grabación activa o si el archivo de
                            audio grabado es inválido.
        """
        if not self._recording_flag.exists():
            raise RecordingError("no hay ninguna grabación activa")

        with open(self._recording_flag, 'r') as f:
            pid = int(f.read())

        # --- detención del proceso de grabación ---
        try:
            subprocess.run(["kill", "-SIGINT", str(pid)])
            time.sleep(1) # da tiempo a que el proceso se cierre correctamente
            subprocess.run(["kill", "-9", str(pid)]) # fuerza el cierre si sigue activo
        except ProcessLookupError:
            # el proceso ya no existía lo cual es aceptable
            pass

        self._recording_flag.unlink()
        time.sleep(0.5)

        if not self._audio_file.exists() or self._audio_file.stat().st_size < 1000:
            raise RecordingError("no se grabó audio o el archivo es muy pequeño")

        # --- transcripción con whisper ---
        logger.info("transcribiendo audio...")
        whisper_config = config['whisper']
        segments, _ = self.model.transcribe(
            str(self._audio_file),
            language=whisper_config['language'],
            beam_size=whisper_config['beam_size'],
            best_of=whisper_config['best_of'],
            temperature=whisper_config['temperature'],
            vad_filter=whisper_config['vad_filter'],
            vad_parameters=config['whisper']['vad_parameters']
        )
        text = " ".join([segment.text.strip() for segment in segments])
        logger.info("transcripción completada")

        self._audio_file.unlink()
        return text
