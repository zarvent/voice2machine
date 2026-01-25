"""Workflow de Grabación y Transcripción.

Coordina el flujo desde que el usuario presiona el atajo hasta que el texto
llega al portapapeles.
"""

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, Protocol

from v2m.shared.config import config
from v2m.shared.logging import logger

if TYPE_CHECKING:
    from v2m.api.schemas import StatusResponse, ToggleResponse
    from v2m.features.audio.recorder import AudioRecorder
    from v2m.features.audio.streaming_transcriber import StreamingTranscriber
    from v2m.features.desktop.linux_adapters import LinuxClipboardAdapter
    from v2m.features.desktop.notification_service import LinuxNotificationService
    from v2m.features.transcription.persistent_model import PersistentWhisperWorker


class BroadcastFn(Protocol):
    """Protocolo para funciones que emiten eventos a través de WebSocket."""

    async def __call__(self, event_type: str, data: dict[str, Any]) -> None:
        """Emite un evento con su tipo y datos asociados."""
        ...


class WebSocketSessionAdapter:
    """Adaptador que envuelve una función de broadcast para emitir eventos."""

    def __init__(self, broadcast_fn: BroadcastFn | None = None) -> None:
        """Inicializa el adaptador.

        Args:
            broadcast_fn: Función opcional para emitir eventos.
        """
        self._broadcast_fn = broadcast_fn

    async def emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emite un evento usando la función de broadcast configurada."""
        if self._broadcast_fn:
            await self._broadcast_fn(event_type, data)


class RecordingWorkflow:
    """Orquestador para el flujo de grabación y transcripción asíncrona."""

    def __init__(self, broadcast_fn: BroadcastFn | None = None) -> None:
        """Inicializa el workflow.

        Args:
            broadcast_fn: Función opcional para emitir actualizaciones de estado.
        """
        self._is_recording = False
        self._model_loaded = False
        self._broadcast_fn = broadcast_fn

        self._worker: PersistentWhisperWorker | None = None
        self._recorder: AudioRecorder | None = None
        self._transcriber: StreamingTranscriber | None = None
        self._clipboard: LinuxClipboardAdapter | None = None
        self._notifications: LinuxNotificationService | None = None

    @property
    def worker(self):
        if self._worker is None:
            from v2m.features.transcription.persistent_model import PersistentWhisperWorker

            whisper_cfg = config.transcription.whisper
            self._worker = PersistentWhisperWorker(
                model_size=whisper_cfg.model,
                device=whisper_cfg.device,
                compute_type=whisper_cfg.compute_type,
                device_index=whisper_cfg.device_index,
                num_workers=whisper_cfg.num_workers,
                keep_warm=whisper_cfg.keep_warm,
            )
        return self._worker

    @property
    def recorder(self):
        if self._recorder is None:
            from v2m.features.audio.recorder import AudioRecorder

            whisper_cfg = config.transcription.whisper
            self._recorder = AudioRecorder(
                sample_rate=16000,
                channels=1,
                device_index=whisper_cfg.audio_device_index,
            )
        return self._recorder

    @property
    def transcriber(self):
        if self._transcriber is None:
            from v2m.features.audio.streaming_transcriber import StreamingTranscriber

            session_adapter = WebSocketSessionAdapter(self._broadcast_fn)
            self._transcriber = StreamingTranscriber(
                worker=self.worker,
                session_manager=session_adapter,
                recorder=self.recorder,
            )
        return self._transcriber

    @property
    def clipboard(self):
        if self._clipboard is None:
            from v2m.features.desktop.linux_adapters import LinuxClipboardAdapter

            self._clipboard = LinuxClipboardAdapter()
        return self._clipboard

    @property
    def notifications(self):
        if self._notifications is None:
            from v2m.features.desktop.notification_service import LinuxNotificationService

            self._notifications = LinuxNotificationService()
        return self._notifications

    async def warmup(self) -> None:
        if self._model_loaded:
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.worker.initialize_sync)
            self._model_loaded = True
            logger.info("✅ Modelo Whisper precargado en VRAM")
        except Exception as e:
            logger.error(f"❌ Error en warmup del modelo: {e}")

    async def toggle(self) -> "ToggleResponse":
        if not self._is_recording:
            return await self.start()
        return await self.stop()

    async def start(self) -> "ToggleResponse":
        from v2m.api.schemas import ToggleResponse

        if self._is_recording:
            return ToggleResponse(status="recording", message="⚠️ Ya está grabando")
        try:
            await self.transcriber.start()
            self._is_recording = True
            config.paths.recording_flag.touch()
            self.notifications.notify("🎤 voice2machine", "grabación iniciada...")
            logger.info("🎙️ Grabación iniciada")
            return ToggleResponse(status="recording", message="🎙️ Grabando...")
        except Exception as e:
            logger.error(f"Error iniciando grabación: {e}")
            return ToggleResponse(status="error", message=f"❌ Error: {e}")

    async def stop(self) -> "ToggleResponse":
        from v2m.api.schemas import ToggleResponse

        if not self._is_recording:
            return ToggleResponse(status="idle", message="⚠️ No hay grabación en curso")
        try:
            self._is_recording = False
            if config.paths.recording_flag.exists():
                config.paths.recording_flag.unlink()
            self.notifications.notify("⚡ v2m procesando", "procesando...")
            transcription = await self.transcriber.stop()
            if not transcription or not transcription.strip():
                # Diagnóstico mejorado: reportar estado de la cola y duración de grabación
                try:
                    queue_size = self.transcriber._audio_queue.qsize()
                    logger.warning(
                        f"Transcripción vacía: audio_queue_size={queue_size}, "
                        f"verificar logs de VAD y Whisper para diagnóstico detallado"
                    )
                except Exception as diag_err:
                    logger.debug(f"Error obteniendo diagnóstico: {diag_err}")

                self.notifications.notify("❌ whisper", "no se detectó voz en el audio")
                return ToggleResponse(status="idle", message="❌ No se detectó voz", text=None)
            self.clipboard.copy(transcription)
            preview = transcription[:80]
            self.notifications.notify("✅ whisper - copiado", f"{preview}...")
            logger.info(f"✅ Transcripción completada: {len(transcription)} chars")
            return ToggleResponse(status="idle", message="✅ Copiado al portapapeles", text=transcription)
        except Exception as e:
            logger.error(f"Error deteniendo grabación: {e}")
            self._is_recording = False
            return ToggleResponse(status="error", message=f"❌ Error: {e}")

    def get_status(self) -> "StatusResponse":
        from v2m.api.schemas import StatusResponse

        state = "recording" if self._is_recording else "idle"
        return StatusResponse(state=state, recording=self._is_recording, model_loaded=self._model_loaded)

    async def shutdown(self) -> None:
        """Apaga el workflow, deteniendo grabaciones y descargando modelos."""
        if self._is_recording:
            with contextlib.suppress(Exception):
                await self.stop()

        if self._worker:
            with contextlib.suppress(Exception):
                await self._worker.unload()

        if self._notifications:
            self._notifications.shutdown(wait=False)
