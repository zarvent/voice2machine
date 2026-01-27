//! Orquestador del pipeline de transcripcion.
//!
//! Conecta todos los componentes: captura de audio, VAD, buffer de speech,
//! transcripcion con Whisper, y salida al clipboard.
//!
//! Emite eventos Tauri para comunicar cambios de estado al frontend.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};
use tokio::sync::Mutex as TokioMutex;

use crate::audio::{play_sound_if_enabled, AudioCapture, AudioResampler, CaptureConfig, SoundCue};
use crate::config::{AppConfig, RecordingState};
use crate::output::ClipboardManager;
use crate::transcription::WhisperTranscriber;
use crate::vad::{SpeechBuffer, VadDetector, VadEvent, VadStateMachine};

/// Eventos emitidos por el pipeline para actualizar la UI
/// Estos payloads se serializan y envian al frontend via Tauri events
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PipelineEvent {
    /// El estado de grabacion cambio
    StateChanged { state: RecordingState },
    /// Speech detectado, comenzando captura
    SpeechStarted,
    /// Speech finalizado, procesando
    SpeechEnded { duration_ms: u64 },
    /// Transcripcion completada exitosamente
    TranscriptionComplete {
        text: String,
        audio_duration_s: f32,
        processing_time_ms: u64,
    },
    /// Texto copiado al clipboard
    CopiedToClipboard { text: String },
    /// Error durante el pipeline
    Error { message: String },
}

/// Configuracion del pipeline
#[derive(Debug, Clone)]
pub struct PipelineConfig {
    /// Configuracion de la aplicacion
    pub app_config: AppConfig,
    /// Duracion maxima de grabacion en segundos
    pub max_recording_duration_s: f32,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        Self {
            app_config: AppConfig::default(),
            max_recording_duration_s: 30.0,
        }
    }
}

/// Resultado de la fase de captura de audio
enum CaptureResult {
    /// Audio capturado exitosamente
    Success {
        audio: Vec<f32>,
        duration_s: f32,
    },
    /// Cancelado por el usuario
    Cancelled,
    /// No se detecto speech suficiente
    NoSpeech,
}

/// Orquestador del pipeline de transcripcion
pub struct Pipeline {
    /// Handle de la aplicacion Tauri para emitir eventos
    app_handle: Option<AppHandle>,
    /// Estado actual
    state: Arc<std::sync::Mutex<RecordingState>>,
    /// Flag para cancelar grabacion
    cancel_flag: Arc<AtomicBool>,
    /// Flag para indicar si hay una tarea de grabacion en ejecucion
    /// Esto evita race conditions cuando toggle se llama multiples veces rapido
    is_running: Arc<AtomicBool>,
    /// Timestamp del ultimo toggle para debouncing (evita doble invocacion)
    last_toggle_time: Arc<std::sync::Mutex<std::time::Instant>>,
    /// Transcriptor de Whisper (lazy-loaded, compartido con Arc)
    transcriber: Arc<TokioMutex<Option<WhisperTranscriber>>>,
    /// Configuracion
    config: Arc<std::sync::Mutex<PipelineConfig>>,
}

impl Pipeline {
    /// Crea un nuevo pipeline
    pub fn new(config: PipelineConfig) -> Self {
        // Inicializar el timestamp en el pasado para que el primer toggle pase
        let past_time = std::time::Instant::now()
            .checked_sub(std::time::Duration::from_secs(10))
            .unwrap_or(std::time::Instant::now());

        Self {
            app_handle: None,
            state: Arc::new(std::sync::Mutex::new(RecordingState::Idle)),
            cancel_flag: Arc::new(AtomicBool::new(false)),
            is_running: Arc::new(AtomicBool::new(false)),
            last_toggle_time: Arc::new(std::sync::Mutex::new(past_time)),
            transcriber: Arc::new(TokioMutex::new(None)),
            config: Arc::new(std::sync::Mutex::new(config)),
        }
    }

    /// Configura el AppHandle para emitir eventos al frontend
    pub fn set_app_handle(&mut self, app_handle: AppHandle) {
        self.app_handle = Some(app_handle);
    }

    /// Emite un evento al frontend via Tauri
    fn emit_event(&self, event: PipelineEvent) {
        if let Some(app) = &self.app_handle {
            if let Err(e) = app.emit("pipeline-event", &event) {
                log::error!("Error emitiendo evento pipeline: {}", e);
            }
        }
    }

    /// Carga el modelo de Whisper si no esta cargado
    pub async fn ensure_model_loaded(&mut self) -> anyhow::Result<()> {
        let mut transcriber_lock = self.transcriber.lock().await;

        if transcriber_lock.is_some() {
            return Ok(());
        }

        let model_path = crate::config::get_model_path()?;
        if !model_path.exists() {
            return Err(anyhow::anyhow!(
                "Modelo no encontrado. Ejecuta la descarga primero."
            ));
        }

        let language = {
            let config = self.config.lock().unwrap();
            config.app_config.language.clone()
        };

        let transcriber = WhisperTranscriber::new(&model_path, &language)?;
        *transcriber_lock = Some(transcriber);

        log::info!("Modelo Whisper cargado exitosamente");
        Ok(())
    }

    /// Verifica si el modelo esta cargado
    pub fn is_model_loaded(&self) -> bool {
        // Para verificacion sincronica, usamos try_lock
        self.transcriber
            .try_lock()
            .map(|guard| guard.is_some())
            .unwrap_or(false)
    }

    /// Actualiza la configuracion
    pub fn update_config(&mut self, new_config: AppConfig) {
        let mut config = self.config.lock().unwrap();
        config.app_config = new_config.clone();

        // Actualizar idioma del transcriptor si esta cargado
        // Esto se hara en el proximo uso del transcriptor
    }

    /// Retorna el estado actual
    pub fn state(&self) -> RecordingState {
        *self.state.lock().unwrap()
    }

    fn set_state(&self, new_state: RecordingState) {
        *self.state.lock().unwrap() = new_state;
        self.emit_event(PipelineEvent::StateChanged { state: new_state });
    }

    /// Alterna el estado de grabacion (toggle)
    /// Retorna true si inicio grabacion, false si la cancelo
    pub async fn toggle_recording(&mut self) -> anyhow::Result<bool> {
        // Debounce: ignorar invocaciones que vienen muy rapido (< 300ms)
        // Safety net para prevenir doble toggle accidental
        const DEBOUNCE_MS: u64 = 300;
        {
            let mut last_toggle = self.last_toggle_time.lock().unwrap();
            let elapsed = last_toggle.elapsed();
            if elapsed.as_millis() < DEBOUNCE_MS as u128 {
                log::debug!("Toggle ignorado por debounce ({}ms)", elapsed.as_millis());
                return Ok(false);
            }
            *last_toggle = std::time::Instant::now();
        }

        // Verificar estado actual
        let was_running = self.is_running.load(Ordering::SeqCst);
        let current_state = self.state();

        log::debug!("toggle_recording: running={}, state={:?}", was_running, current_state);

        match (was_running, current_state) {
            // No hay nada corriendo y estado es Idle -> iniciar grabacion
            (false, RecordingState::Idle) => {
                self.start_recording().await?;
                Ok(true)
            }
            // Hay algo corriendo y estado es Recording -> cancelar
            (true, RecordingState::Recording) => {
                self.cancel_recording();
                Ok(false)
            }
            // Estado es Processing -> no se puede cancelar
            (_, RecordingState::Processing) => {
                log::warn!("No se puede cancelar durante procesamiento");
                Ok(false)
            }
            // Race condition: estado dice Idle pero is_running dice true
            // Esto puede pasar brevemente mientras el task se inicializa
            // Ignoramos este toggle para evitar problemas
            (true, RecordingState::Idle) => {
                log::warn!("Toggle ignorado: tarea aun inicializandose");
                Ok(false)
            }
            // Estado dice Recording pero is_running dice false
            // Inconsistencia - reset a idle
            (false, RecordingState::Recording) => {
                log::warn!("Inconsistencia detectada: Recording sin is_running. Reseteando.");
                self.set_state(RecordingState::Idle);
                Ok(false)
            }
        }
    }

    /// Inicia la grabacion de audio
    async fn start_recording(&mut self) -> anyhow::Result<()> {
        // Intentar reclamar el slot de grabacion atomicamente
        // Si ya estaba en true, alguien mas ya esta grabando
        if self
            .is_running
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .is_err()
        {
            log::warn!("Grabacion ya en progreso, ignorando");
            return Ok(());
        }

        // Verificar que el modelo este cargado
        if let Err(e) = self.ensure_model_loaded().await {
            // Si falla, liberar el slot
            self.is_running.store(false, Ordering::SeqCst);
            return Err(e);
        }

        self.cancel_flag.store(false, Ordering::SeqCst);
        self.set_state(RecordingState::Recording);

        // Obtener configuracion
        let config = {
            let cfg = self.config.lock().unwrap();
            cfg.clone()
        };

        // Sonido de inicio
        play_sound_if_enabled(SoundCue::Start, config.app_config.sound_enabled);

        // Clonar recursos compartidos para el task
        let state = self.state.clone();
        let cancel_flag = self.cancel_flag.clone();
        let is_running = self.is_running.clone();
        let app_handle = self.app_handle.clone();
        let transcriber = self.transcriber.clone();
        let config_arc = self.config.clone();

        // Ejecutar pipeline en task separado
        tokio::spawn(async move {
            let result = run_recording_pipeline(
                config_arc,
                state.clone(),
                cancel_flag,
                app_handle.clone(),
                transcriber,
            )
            .await;

            // SIEMPRE liberar el flag al terminar
            is_running.store(false, Ordering::SeqCst);
            log::debug!("Pipeline task completado, is_running = false");

            if let Err(e) = result {
                log::error!("Error en pipeline: {}", e);
                emit_pipeline_event(
                    &app_handle,
                    PipelineEvent::Error {
                        message: e.to_string(),
                    },
                );
            }
        });

        Ok(())
    }

    /// Cancela la grabacion actual
    pub fn cancel_recording(&self) {
        self.cancel_flag.store(true, Ordering::SeqCst);
        log::info!("Grabacion cancelada por usuario");
    }
}

/// Helper para emitir eventos desde funciones standalone
fn emit_pipeline_event(app_handle: &Option<AppHandle>, event: PipelineEvent) {
    if let Some(app) = app_handle {
        if let Err(e) = app.emit("pipeline-event", &event) {
            log::error!("Error emitiendo evento pipeline: {}", e);
        }
    }
}

/// Ejecuta la fase de captura de audio (sincrona, no-Send)
///
/// Esta funcion corre en un spawn_blocking porque AudioCapture no es Send.
/// La grabación es MANUAL: solo termina cuando el usuario presiona el shortcut de nuevo
/// (cancel_flag) o se alcanza el tiempo máximo.
///
/// El VAD se usa para:
/// 1. Detectar cuando empieza el speech (para comenzar a acumular audio)
/// 2. Segmentar el audio (detectar pausas entre oraciones)
/// 3. Feedback visual al frontend
///
/// El VAD NO controla cuando termina la grabacion - eso es decision del usuario.
fn run_audio_capture(
    config: PipelineConfig,
    cancel_flag: Arc<AtomicBool>,
) -> anyhow::Result<CaptureResult> {
    // 1. Iniciar captura de audio
    let capture_config = CaptureConfig {
        device_id: config.app_config.audio_device_id.clone(),
        ..Default::default()
    };
    let capture = AudioCapture::start(capture_config)?;

    // 2. Crear resampler
    let mut resampler = AudioResampler::new(capture.sample_rate, capture.channels)?;

    // 3. Crear detector VAD
    let vad_config = config.app_config.vad.clone();
    let mut vad = VadDetector::new(16000, vad_config.clone())?;

    // 4. Crear maquina de estados VAD
    let mut vad_state = VadStateMachine::new(vad_config.clone());

    // 5. Crear buffer de speech
    let mut speech_buffer = SpeechBuffer::new(
        16000,
        vad_config.speech_pad_ms,
        config.max_recording_duration_s,
    );

    let mut speech_ever_detected = false;
    let mut currently_speaking = false;
    let recording_start = Instant::now();

    log::info!("🎙️ Grabación iniciada - presiona el shortcut de nuevo para detener");

    // Loop principal de captura - SOLO termina por:
    // 1. cancel_flag (usuario presiono shortcut de nuevo)
    // 2. Max duration reached
    // 3. Canal desconectado (error)
    loop {
        // ===== VERIFICAR CANCELACION (USUARIO DETUVO GRABACION) =====
        if cancel_flag.load(Ordering::Relaxed) {
            log::info!("🛑 Grabación detenida por usuario");
            capture.stop();

            // Si hay speech capturado, retornar Success para transcribir
            if speech_buffer.has_speech() {
                let speech_audio = speech_buffer.end_speech();
                let audio_duration_s = speech_audio.len() as f32 / 16000.0;
                log::info!(
                    "📝 Speech capturado: {} samples ({:.2}s)",
                    speech_audio.len(),
                    audio_duration_s
                );
                return Ok(CaptureResult::Success {
                    audio: speech_audio,
                    duration_s: audio_duration_s,
                });
            }

            // No hay speech, fue cancelado sin hablar
            return Ok(CaptureResult::Cancelled);
        }

        // ===== VERIFICAR TIMEOUT MAXIMO =====
        if recording_start.elapsed().as_secs_f32() > config.max_recording_duration_s + 5.0 {
            log::warn!("⏱️ Timeout de grabación alcanzado");
            break;
        }

        // ===== RECIBIR CHUNK DE AUDIO =====
        let chunk = match capture.receiver.recv_timeout(std::time::Duration::from_millis(100)) {
            Ok(chunk) => chunk,
            Err(crossbeam_channel::RecvTimeoutError::Timeout) => continue,
            Err(crossbeam_channel::RecvTimeoutError::Disconnected) => {
                log::warn!("⚠️ Canal de audio desconectado");
                break;
            }
        };

        // ===== RESAMPLEAR A 16kHz MONO =====
        let resampled = resampler.process(&chunk)?;

        // Calcular duracion del chunk en ms
        let chunk_duration_ms = (resampled.len() as f64 * 1000.0 / 16000.0) as u64;

        // ===== SIEMPRE AGREGAR AL PRE-BUFFER =====
        // Esto mantiene un buffer circular con audio reciente
        speech_buffer.push_pre_speech(&resampled);

        // ===== DETECTAR VOZ CON VAD =====
        let vad_result = vad.predict(&resampled);

        // Procesar en maquina de estados VAD
        let event = vad_state.process(vad_result.is_speech, chunk_duration_ms);

        match event {
            VadEvent::SpeechStarted => {
                log::info!("🎤 Speech detectado, acumulando audio");

                if !speech_ever_detected {
                    // Primera vez que detectamos speech - inicializar buffer
                    speech_buffer.start_speech();
                    speech_ever_detected = true;
                }

                currently_speaking = true;
            }
            VadEvent::SpeechEnded => {
                // Silencio detectado - pero NO terminamos la grabación
                // El usuario puede estar haciendo una pausa entre oraciones
                log::debug!("🔇 Pausa detectada (silencio confirmado)");
                currently_speaking = false;

                // Resetear VAD para detectar el proximo segmento de speech
                vad_state.reset();
            }
            VadEvent::MaxDurationReached => {
                // Buffer lleno - forzar fin
                log::info!("📦 Buffer de speech lleno");
                break;
            }
            VadEvent::None => {
                // Sin cambio de estado significativo
            }
        }

        // ===== ACUMULAR AUDIO CUANDO HAY SPEECH =====
        // Acumulamos audio cuando:
        // 1. Estamos capturando activamente (VAD dice que hay voz)
        // 2. O cuando estamos en silencio pendiente (pausa corta entre palabras)
        if speech_ever_detected && (vad_state.is_capturing() || currently_speaking) {
            speech_buffer.push_speech(&resampled);

            // Verificar limite de duracion
            if speech_buffer.is_at_capacity() {
                log::info!("📦 Max duration del buffer alcanzado: {}ms", speech_buffer.speech_duration_ms());
                break;
            }
        }
    }

    // ===== FINALIZAR CAPTURA =====
    capture.stop();

    // Verificar si hay speech suficiente
    if !speech_buffer.has_speech() {
        log::info!("❌ No se detectó speech suficiente");
        return Ok(CaptureResult::NoSpeech);
    }

    // Obtener audio acumulado
    let speech_audio = speech_buffer.end_speech();
    let audio_duration_s = speech_audio.len() as f32 / 16000.0;

    log::info!(
        "📝 Speech capturado: {} samples ({:.2}s)",
        speech_audio.len(),
        audio_duration_s
    );

    Ok(CaptureResult::Success {
        audio: speech_audio,
        duration_s: audio_duration_s,
    })
}

/// Ejecuta el pipeline de grabacion completo
async fn run_recording_pipeline(
    config_arc: Arc<std::sync::Mutex<PipelineConfig>>,
    state: Arc<std::sync::Mutex<RecordingState>>,
    cancel_flag: Arc<AtomicBool>,
    app_handle: Option<AppHandle>,
    transcriber_arc: Arc<TokioMutex<Option<WhisperTranscriber>>>,
) -> anyhow::Result<()> {
    // Obtener configuracion
    let config = {
        let cfg = config_arc.lock().unwrap();
        cfg.clone()
    };

    let sound_enabled = config.app_config.sound_enabled;

    // Emitir evento de speech started (aproximado, antes de captura)
    emit_pipeline_event(&app_handle, PipelineEvent::SpeechStarted);

    // Fase 1: Captura de audio (sincrona, en blocking task)
    let cancel_flag_capture = cancel_flag.clone();

    let capture_result = tokio::task::spawn_blocking(move || {
        run_audio_capture(config, cancel_flag_capture)
    })
    .await
    .map_err(|e| anyhow::anyhow!("Error en task de captura: {}", e))??;

    // Procesar resultado de captura
    let (speech_audio, audio_duration_s) = match capture_result {
        CaptureResult::Success { audio, duration_s } => {
            emit_pipeline_event(&app_handle, PipelineEvent::SpeechEnded {
                duration_ms: (duration_s * 1000.0) as u64
            });
            (audio, duration_s)
        },
        CaptureResult::Cancelled => {
            *state.lock().unwrap() = RecordingState::Idle;
            emit_pipeline_event(&app_handle, PipelineEvent::StateChanged { state: RecordingState::Idle });
            play_sound_if_enabled(SoundCue::Stop, sound_enabled);
            return Ok(());
        }
        CaptureResult::NoSpeech => {
            *state.lock().unwrap() = RecordingState::Idle;
            emit_pipeline_event(&app_handle, PipelineEvent::StateChanged { state: RecordingState::Idle });
            play_sound_if_enabled(SoundCue::Stop, sound_enabled);
            return Ok(());
        }
    };

    // Cambiar a estado de procesamiento
    *state.lock().unwrap() = RecordingState::Processing;
    emit_pipeline_event(&app_handle, PipelineEvent::StateChanged { state: RecordingState::Processing });
    play_sound_if_enabled(SoundCue::Stop, sound_enabled);

    // Fase 2: Transcribir con Whisper
    let transcribe_start = Instant::now();

    let text = {
        let transcriber_lock = transcriber_arc.lock().await;
        match transcriber_lock.as_ref() {
            Some(transcriber) => transcriber.transcribe(&speech_audio).await?,
            None => return Err(anyhow::anyhow!("Transcriber no disponible")),
        }
    };

    let processing_time_ms = transcribe_start.elapsed().as_millis() as u64;

    log::info!(
        "Transcripcion completada en {}ms: '{}'",
        processing_time_ms,
        text
    );

    emit_pipeline_event(&app_handle, PipelineEvent::TranscriptionComplete {
        text: text.clone(),
        audio_duration_s,
        processing_time_ms,
    });

    // Fase 3: Copiar al clipboard si hay texto
    if !text.is_empty() {
        match ClipboardManager::new() {
            Ok(mut clipboard) => {
                if let Err(e) = clipboard.set_text(&text) {
                    log::error!("Error copiando al clipboard: {}", e);
                    emit_pipeline_event(&app_handle, PipelineEvent::Error {
                        message: format!("Error copiando al clipboard: {}", e),
                    });
                    play_sound_if_enabled(SoundCue::Error, sound_enabled);
                } else {
                    emit_pipeline_event(&app_handle, PipelineEvent::CopiedToClipboard { text });
                    play_sound_if_enabled(SoundCue::Success, sound_enabled);
                }
            }
            Err(e) => {
                log::error!("Error inicializando clipboard: {}", e);
                emit_pipeline_event(&app_handle, PipelineEvent::Error {
                    message: format!("Error con clipboard: {}", e),
                });
                play_sound_if_enabled(SoundCue::Error, sound_enabled);
            }
        }
    } else {
        log::info!("Transcripcion vacia, no se copia al clipboard");
        play_sound_if_enabled(SoundCue::Stop, sound_enabled);
    }

    // Volver a idle
    *state.lock().unwrap() = RecordingState::Idle;
    emit_pipeline_event(&app_handle, PipelineEvent::StateChanged { state: RecordingState::Idle });

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pipeline_config_default() {
        let config = PipelineConfig::default();
        assert_eq!(config.max_recording_duration_s, 30.0);
        assert_eq!(config.app_config.language, "es");
    }

    #[test]
    fn test_pipeline_creation() {
        let config = PipelineConfig::default();
        let pipeline = Pipeline::new(config);

        assert_eq!(pipeline.state(), RecordingState::Idle);
        assert!(pipeline.app_handle.is_none()); // Sin app handle inicialmente
    }
}
