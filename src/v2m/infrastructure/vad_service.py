# Lazy imports - torch es pesado (~500MB), ONNX es más ligero (~100MB)
import numpy as np
from typing import List, Optional, Callable
import threading
from pathlib import Path
from v2m.core.logging import logger
from v2m.config import config

# Constantes para VAD
_VAD_SAMPLE_RATE = 16000
_VAD_WINDOW_SIZE = 512  # Silero VAD window size para 16kHz


class VADService:
    """
    servicio para la detección de actividad de voz (vad) utilizando silero vad

    soporta dos backends
    - onnx runtime (recomendado) ~100mb footprint más rápido en cpu
    - pytorch (fallback) ~500mb footprint necesario si onnx no está disponible

    permite truncar los silencios del audio antes de enviarlo a whisper
    mejorando la eficiencia y reduciendo el tiempo de inferencia
    """
    def __init__(self, prefer_onnx: bool = True):
        """
        inicializa el servicio vad

        args:
            prefer_onnx: si true intenta usar onnx runtime primero (menor footprint)
        """
        self.model = None
        self.utils = None
        self.get_speech_timestamps: Optional[Callable] = None
        self.disabled = False

        # Determinar preferencia desde config
        backend_config = config.whisper.vad_parameters.backend
        self._prefer_onnx = (backend_config == "onnx")
        if prefer_onnx is False: # Override manual si se pasa en init
             self._prefer_onnx = False

        self._backend: Optional[str] = None  # 'onnx' o 'torch'
        self._onnx_session = None
        self._state: Optional[np.ndarray] = None  # Estado LSTM para ONNX

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        normaliza el audio (peak normalization) para mejorar la detección del vad
        si el volumen es muy bajo lo amplifica hasta un nivel seguro (0.9)
        """
        max_val = np.max(np.abs(audio))
        if max_val == 0:
            return audio

        # Solo normalizar si el audio es bajo (< 0.5) para evitar distorsión en audio ya fuerte
        # O siempre normalizar a un target seguro?
        # Estrategia: Peak Normalization a 0.9 si el max es bajo.
        target = 0.9
        if max_val < target:
            gain = target / max_val
            # Limitar ganancia máxima para no amplificar solo ruido de fondo excesivamente
            # e.g., max 10x (20dB)
            gain = min(gain, 10.0)

            logger.debug(f"VAD Normalization: gain={gain:.2f}x (original max={max_val:.3f})")
            return np.clip(audio * gain, -1.0, 1.0)

        return audio

    def load_model(self, timeout_sec: float = 10.0):
        """
        carga el modelo silero vad de forma perezosa con timeout

        intenta cargar onnx primero (menor footprint) fallback a pytorch

        args:
            timeout_sec: tiempo máximo de espera en segundos
        """
        if self.disabled:
            return
        if self.model is not None or self._onnx_session is not None:
            return

        # Intentar ONNX primero si está preferido
        if self._prefer_onnx:
            try:
                self._load_onnx_model()
                return
            except Exception as e:
                logger.warning(f"ONNX VAD no disponible, intentando PyTorch: {e}")

        # Fallback a PyTorch
        self._load_torch_model(timeout_sec)

    def _load_onnx_model(self):
        """
        carga el modelo silero vad usando onnx runtime (~100mb footprint)
        """
        import onnxruntime as ort

        # Descargar modelo ONNX si no existe
        model_path = self._get_onnx_model_path()

        # Configurar sesión ONNX optimizada
        sess_options = ort.SessionOptions()
        sess_options.inter_op_num_threads = 1
        sess_options.intra_op_num_threads = 1
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self._onnx_session = ort.InferenceSession(
            str(model_path),
            sess_options=sess_options,
            providers=['CPUExecutionProvider']
        )

        # Inicializar estados LSTM
        self._reset_onnx_states()
        self._backend = 'onnx'
        logger.info("✅ Silero VAD cargado (ONNX Runtime - footprint reducido)")

    def _get_onnx_model_path(self) -> Path:
        """
        obtiene la ruta al modelo onnx descargándolo si es necesario
        """
        # Buscar en cache local de torch hub (subcarpeta src/silero_vad/data)
        local_cache = Path.home() / ".cache" / "torch" / "hub" / "snakers4_silero-vad_master"
        local_onnx = local_cache / "src" / "silero_vad" / "data" / "silero_vad.onnx"

        if local_onnx.exists():
            logger.debug(f"Usando modelo ONNX local: {local_onnx}")
            return local_onnx

        # Alternativa: buscar versión anterior (files/)
        local_onnx_alt = local_cache / "files" / "silero_vad.onnx"
        if local_onnx_alt.exists():
            return local_onnx_alt

        # Alternativa: buscar en el paquete silero-vad instalado
        try:
            import silero_vad
            pkg_path = Path(silero_vad.__file__).parent
            pkg_onnx = pkg_path / "data" / "silero_vad.onnx"
            if pkg_onnx.exists():
                logger.debug(f"Usando modelo ONNX del paquete: {pkg_onnx}")
                return pkg_onnx
        except ImportError:
            pass

        # Último recurso: descargar de HuggingFace
        try:
            from huggingface_hub import hf_hub_download
            model_path = hf_hub_download(
                repo_id="snakers4/silero-vad",
                filename="silero_vad.onnx",
                cache_dir=None
            )
            return Path(model_path)
        except Exception as e:
            raise FileNotFoundError(f"No se encontró modelo ONNX de Silero VAD: {e}")

    def _reset_onnx_states(self):
        """
        resetea los estados lstm para una nueva secuencia de audio
        """
        # Silero VAD ONNX: state shape [2, batch, 128]
        self._state = np.zeros((2, 1, 128), dtype=np.float32)

    def _load_torch_model(self, timeout_sec: float):
        """
        carga el modelo usando pytorch (fallback ~500mb footprint)
        """
        logger.info("cargando modelo silero vad (PyTorch)...")

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
        ejecuta inferencia vad con onnx runtime

        args:
            audio_chunk: chunk de audio (512 samples para 16khz)
            sr: sample rate

        returns:
            probabilidad de voz (0.0 - 1.0)
        """
        if len(audio_chunk) != _VAD_WINDOW_SIZE:
            # Pad o truncar al tamaño correcto
            if len(audio_chunk) < _VAD_WINDOW_SIZE:
                audio_chunk = np.pad(audio_chunk, (0, _VAD_WINDOW_SIZE - len(audio_chunk)))
            else:
                audio_chunk = audio_chunk[:_VAD_WINDOW_SIZE]

        # Preparar inputs según interfaz real del modelo ONNX
        # input: [batch, samples], state: [2, batch, 128], sr: scalar
        audio_input = audio_chunk.astype(np.float32).reshape(1, -1)
        sr_tensor = np.array(sr, dtype=np.int64)

        # Inferencia
        ort_inputs = {
            'input': audio_input,
            'state': self._state,
            'sr': sr_tensor
        }

        output, self._state = self._onnx_session.run(None, ort_inputs)
        return float(output[0][0])

    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        procesa el audio y elimina los segmentos de silencio

        args:
            audio: array de numpy con el audio (float32)
            sample_rate: frecuencia de muestreo (debe ser 8000 o 16000 para silero)

        returns:
            un nuevo array de numpy que contiene solo los segmentos de voz concatenados
            si no se detecta voz devuelve un array vacío
        """
        # si el audio está vacío, retornar de inmediato
        if audio.size == 0:
            return np.array([], dtype=np.float32)

        # Normalizar audio antes de VAD para mejorar detección en volúmenes bajos
        audio = self._normalize_audio(audio)

        try:
            self.load_model()
        except Exception:
            logger.warning("VAD no disponible, se usará audio sin truncar")
            return audio

        if self.disabled:
            return audio

        # Usar el backend apropiado
        if self._backend == 'onnx':
            return self._process_onnx(audio, sample_rate)
        else:
            return self._process_torch(audio, sample_rate)

    def _process_onnx(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        procesa audio usando onnx backend (optimizado para latencia)
        """
        self._reset_onnx_states()

        # Pre-calcular constantes (evita acceso a config en cada iteración)
        threshold = config.whisper.vad_parameters.threshold
        min_speech_samples = int(config.whisper.vad_parameters.min_speech_duration_ms * sample_rate / 1000)
        min_silence_samples = int(config.whisper.vad_parameters.min_silence_duration_ms * sample_rate / 1000)

        audio_len = len(audio)
        n_chunks = (audio_len + _VAD_WINDOW_SIZE - 1) // _VAD_WINDOW_SIZE

        # Pre-allocar array de probabilidades para evitar append
        probs = np.empty(n_chunks, dtype=np.float32)

        # Procesar chunks - el loop es necesario por el estado LSTM
        for i in range(n_chunks):
            start = i * _VAD_WINDOW_SIZE
            end = min(start + _VAD_WINDOW_SIZE, audio_len)
            chunk = audio[start:end]

            if len(chunk) < _VAD_WINDOW_SIZE:
                chunk = np.pad(chunk, (0, _VAD_WINDOW_SIZE - len(chunk)))

            probs[i] = self._vad_onnx(chunk, sample_rate)

        # Detectar timestamps usando operaciones vectorizadas
        is_speech_mask = probs >= threshold
        speech_timestamps = []
        is_speech = False
        speech_start = 0
        silence_chunks = 0
        min_silence_chunks = min_silence_samples // _VAD_WINDOW_SIZE
        min_speech_chunks = min_speech_samples // _VAD_WINDOW_SIZE

        for i, is_chunk_speech in enumerate(is_speech_mask):
            sample_pos = i * _VAD_WINDOW_SIZE
            if is_chunk_speech:
                if not is_speech:
                    speech_start = sample_pos
                    is_speech = True
                silence_chunks = 0
            elif is_speech:
                silence_chunks += 1
                if silence_chunks >= min_silence_chunks:
                    speech_end = sample_pos - (silence_chunks - 1) * _VAD_WINDOW_SIZE
                    speech_len_chunks = (speech_end - speech_start) // _VAD_WINDOW_SIZE
                    if speech_len_chunks >= min_speech_chunks:
                        speech_timestamps.append({'start': speech_start, 'end': speech_end})
                    is_speech = False
                    silence_chunks = 0

        # Cerrar último segmento si quedó abierto
        if is_speech:
            speech_end = audio_len
            if (speech_end - speech_start) >= min_speech_samples:
                speech_timestamps.append({'start': speech_start, 'end': speech_end})

        if not speech_timestamps:
            logger.info("VAD (ONNX): no se detectó voz")
            return np.array([], dtype=np.float32)

        # Concatenar chunks de voz
        speech_chunks = [audio[ts['start']:ts['end']] for ts in speech_timestamps]
        result = np.concatenate(speech_chunks)

        original_duration = audio_len / sample_rate
        new_duration = len(result) / sample_rate
        logger.info(f"VAD (ONNX): audio truncado de {original_duration:.2f}s a {new_duration:.2f}s")

        return result

    def _process_torch(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        procesa audio usando pytorch backend (fallback)
        """
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
            logger.info("VAD (PyTorch): no se detectó voz")
            return np.array([], dtype=np.float32)

        speech_chunks = [audio[int(ts['start']):int(ts['end'])] for ts in timestamps]

        if not speech_chunks:
            return np.array([], dtype=np.float32)

        result = np.concatenate(speech_chunks)

        original_duration = len(audio) / sample_rate
        new_duration = len(result) / sample_rate
        logger.info(f"VAD (PyTorch): audio truncado de {original_duration:.2f}s a {new_duration:.2f}s")

        return result
