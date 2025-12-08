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

# lazy imports - torch es pesado (~500MB), ONNX es más ligero (~100MB)
import numpy as np
from typing import List, Optional, Callable
import threading
from pathlib import Path
from v2m.core.logging import logger
from v2m.config import config

# constantes para vad
_VAD_SAMPLE_RATE = 16000
_VAD_WINDOW_SIZE = 512  # silero vad window size para 16khz


class VADService:
    """
    SERVICIO PARA LA DETECCION DE ACTIVIDAD DE VOZ (VAD) UTILIZANDO SILERO VAD

    soporta dos backends
    - onnx runtime (recomendado): ~100mb footprint, más rápido en cpu
    - pytorch (fallback): ~500mb footprint, necesario si onnx no está disponible

    PERMITE TRUNCAR LOS SILENCIOS DEL AUDIO ANTES DE ENVIARLO A WHISPER
    mejorando la eficiencia y reduciendo el tiempo de inferencia
    """
    def __init__(self, prefer_onnx: bool = True):
        """
        INICIALIZA EL SERVICIO VAD

        ARGS
            prefer_onnx: si true, intenta usar onnx runtime primero (menor footprint)
        """
        self.model = None
        self.utils = None
        self.get_speech_timestamps: Optional[Callable] = None
        self.disabled = False
        self._prefer_onnx = prefer_onnx
        self._backend: Optional[str] = None  # 'onnx' o 'torch'
        self._onnx_session = None
        self._state: Optional[np.ndarray] = None  # Estado LSTM para ONNX

    def load_model(self, timeout_sec: float = 10.0):
        """
        CARGA EL MODELO SILERO VAD DE FORMA PEREZOSA CON TIMEOUT

        intenta cargar onnx primero (menor footprint), fallback a pytorch

        ARGS
            timeout_sec (float): tiempo maximo de espera en segundos
        """
        if self.disabled:
            return
        if self.model is not None or self._onnx_session is not None:
            return

        # intentar onnx primero si está preferido
        if self._prefer_onnx:
            try:
                self._load_onnx_model()
                return
            except Exception as e:
                logger.warning(f"ONNX VAD no disponible, intentando PyTorch: {e}")

        # fallback a pytorch
        self._load_torch_model(timeout_sec)

    def _load_onnx_model(self):
        """CARGA EL MODELO SILERO VAD USANDO ONNX RUNTIME (~100MB FOOTPRINT)"""
        import onnxruntime as ort

        # descargar modelo onnx si no existe
        model_path = self._get_onnx_model_path()

        # configurar sesión onnx optimizada
        sess_options = ort.SessionOptions()
        sess_options.inter_op_num_threads = 1
        sess_options.intra_op_num_threads = 1
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self._onnx_session = ort.InferenceSession(
            str(model_path),
            sess_options=sess_options,
            providers=['CPUExecutionProvider']
        )

        # inicializar estados lstm
        self._reset_onnx_states()
        self._backend = 'onnx'
        logger.info("✅ Silero VAD cargado (ONNX Runtime - footprint reducido)")

    def _get_onnx_model_path(self) -> Path:
        """OBTIENE LA RUTA AL MODELO ONNX DESCARGÁNDOLO SI ES NECESARIO"""
        # buscar en cache local de torch hub (subcarpeta src/silero_vad/data)
        local_cache = Path.home() / ".cache" / "torch" / "hub" / "snakers4_silero-vad_master"
        local_onnx = local_cache / "src" / "silero_vad" / "data" / "silero_vad.onnx"

        if local_onnx.exists():
            logger.debug(f"usando modelo onnx local: {local_onnx}")
            return local_onnx

        # alternativa: buscar versión anterior (files/)
        local_onnx_alt = local_cache / "files" / "silero_vad.onnx"
        if local_onnx_alt.exists():
            return local_onnx_alt

        # alternativa: buscar en el paquete silero-vad instalado
        try:
            import silero_vad
            pkg_path = Path(silero_vad.__file__).parent
            pkg_onnx = pkg_path / "data" / "silero_vad.onnx"
            if pkg_onnx.exists():
                logger.debug(f"usando modelo onnx del paquete: {pkg_onnx}")
                return pkg_onnx
        except ImportError:
            pass

        # último recurso: descargar de huggingface
        try:
            from huggingface_hub import hf_hub_download
            model_path = hf_hub_download(
                repo_id="snakers4/silero-vad",
                filename="silero_vad.onnx",
                cache_dir=None
            )
            return Path(model_path)
        except Exception as e:
            raise FileNotFoundError(f"no se encontró modelo onnx de silero vad: {e}")

    def _reset_onnx_states(self):
        """RESETEA LOS ESTADOS LSTM PARA UNA NUEVA SECUENCIA DE AUDIO"""
        # silero vad onnx: state shape [2, batch, 128]
        self._state = np.zeros((2, 1, 128), dtype=np.float32)

    def _load_torch_model(self, timeout_sec: float):
        """CARGA EL MODELO USANDO PYTORCH (FALLBACK, ~500MB FOOTPRINT)"""
        logger.info("cargando modelo silero vad (pytorch)...")

        exc_holder: list[Exception] = []

        def _do_load():
            try:
                import torch
                self.model, self.utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False
                )
            except Exception as e:
                exc_holder.append(e)

        t = threading.Thread(target=_do_load, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)

        if t.is_alive():
            self.disabled = True
            logger.warning("timeout cargando silero VAD; VAD deshabilitado para esta sesión")
            return

        if exc_holder:
            self.disabled = True
            logger.error(f"error al cargar silero vad {exc_holder[0]}")
            raise exc_holder[0]

        (self.get_speech_timestamps, _, _, _, _) = self.utils
        self._backend = 'torch'
        logger.info("✅ Silero VAD cargado (PyTorch)")

    def _vad_onnx(self, audio_chunk: np.ndarray, sr: int = 16000) -> float:
        """
        EJECUTA INFERENCIA VAD CON ONNX RUNTIME

        ARGS
            audio_chunk: chunk de audio (512 samples para 16khz)
            sr: sample rate

        RETURNS
            probabilidad de voz (0.0 - 1.0)
        """
        if len(audio_chunk) != _VAD_WINDOW_SIZE:
            # pad o truncar al tamaño correcto
            if len(audio_chunk) < _VAD_WINDOW_SIZE:
                audio_chunk = np.pad(audio_chunk, (0, _VAD_WINDOW_SIZE - len(audio_chunk)))
            else:
                audio_chunk = audio_chunk[:_VAD_WINDOW_SIZE]

        # preparar inputs según interfaz real del modelo onnx
        # input: [batch, samples], state: [2, batch, 128], sr: scalar
        audio_input = audio_chunk.astype(np.float32).reshape(1, -1)
        sr_tensor = np.array(sr, dtype=np.int64)

        # inferencia
        ort_inputs = {
            'input': audio_input,
            'state': self._state,
            'sr': sr_tensor
        }

        output, self._state = self._onnx_session.run(None, ort_inputs)
        return float(output[0][0])

    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        PROCESA EL AUDIO Y ELIMINA LOS SEGMENTOS DE SILENCIO

        ARGS
            audio (np.ndarray): array de numpy con el audio (float32)
            sample_rate (int): frecuencia de muestreo (debe ser 8000 o 16000 para silero)

        RETURNS
            np.ndarray: un nuevo array de numpy que contiene solo los segmentos de voz concatenados
            si no se detecta voz devuelve un array vacio
        """
        # si el audio está vacío, retornar de inmediato
        if audio.size == 0:
            return np.array([], dtype=np.float32)

        try:
            self.load_model()
        except Exception:
            logger.warning("vad no disponible, se usará audio sin truncar")
            return audio

        if self.disabled:
            return audio

        # usar el backend apropiado
        if self._backend == 'onnx':
            return self._process_onnx(audio, sample_rate)
        else:
            return self._process_torch(audio, sample_rate)

    def _process_onnx(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """PROCESA AUDIO USANDO ONNX BACKEND (MÁS EFICIENTE)"""
        self._reset_onnx_states()

        threshold = config.whisper.vad_parameters.threshold
        min_speech_samples = int(config.whisper.vad_parameters.min_speech_duration_ms * sample_rate / 1000)
        min_silence_samples = int(config.whisper.vad_parameters.min_silence_duration_ms * sample_rate / 1000)

        # procesar en chunks de 512 samples
        speech_timestamps = []
        is_speech = False
        speech_start = 0
        silence_samples = 0

        for i in range(0, len(audio), _VAD_WINDOW_SIZE):
            chunk = audio[i:i + _VAD_WINDOW_SIZE]
            if len(chunk) < _VAD_WINDOW_SIZE:
                chunk = np.pad(chunk, (0, _VAD_WINDOW_SIZE - len(chunk)))

            prob = self._vad_onnx(chunk, sample_rate)

            if prob >= threshold:
                if not is_speech:
                    speech_start = i
                    is_speech = True
                silence_samples = 0
            else:
                if is_speech:
                    silence_samples += _VAD_WINDOW_SIZE
                    if silence_samples >= min_silence_samples:
                        speech_end = i - silence_samples + _VAD_WINDOW_SIZE
                        if speech_end - speech_start >= min_speech_samples:
                            speech_timestamps.append({'start': speech_start, 'end': speech_end})
                        is_speech = False
                        silence_samples = 0

        # cerrar último segmento si quedó abierto
        if is_speech:
            speech_end = len(audio)
            if speech_end - speech_start >= min_speech_samples:
                speech_timestamps.append({'start': speech_start, 'end': speech_end})

        if not speech_timestamps:
            logger.info("vad (onnx): no se detectó voz")
            return np.array([], dtype=np.float32)

        # concatenar chunks de voz
        speech_chunks = [audio[ts['start']:ts['end']] for ts in speech_timestamps]
        result = np.concatenate(speech_chunks)

        original_duration = len(audio) / sample_rate
        new_duration = len(result) / sample_rate
        logger.info(f"vad (onnx): audio truncado de {original_duration:.2f}s a {new_duration:.2f}s")

        return result

    def _process_torch(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """PROCESA AUDIO USANDO PYTORCH BACKEND (FALLBACK)"""
        if self.model is None or self.get_speech_timestamps is None:
            return audio

        import torch
        audio_tensor = torch.from_numpy(audio)

        vad_threshold = config.whisper.vad_parameters.threshold
        timestamps = self.get_speech_timestamps(
            audio_tensor,
            self.model,
            sampling_rate=sample_rate,
            threshold=vad_threshold
        )

        if not timestamps:
            logger.info("vad (pytorch): no se detectó voz")
            return np.array([], dtype=np.float32)

        speech_chunks = [audio[int(ts['start']):int(ts['end'])] for ts in timestamps]

        if not speech_chunks:
            return np.array([], dtype=np.float32)

        result = np.concatenate(speech_chunks)

        original_duration = len(audio) / sample_rate
        new_duration = len(result) / sample_rate
        logger.info(f"vad (pytorch): audio truncado de {original_duration:.2f}s a {new_duration:.2f}s")

        return result
