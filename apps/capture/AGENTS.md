# AGENTS.md

> Este archivo está optimizado para usuarios técnicos.
> Para documentación desde una vista mas macro, ver [README.md](README.md).

---

## Overview

`capture` es una app de **voice2machine** ubicada en `voice2machine/apps/capture`.

**voice2machine** es un monorepo de herramientas de transcripción de voz a texto.

**Filosofía:** Local-first, no local-only. Procesamiento local por defecto para velocidad y privacidad. Soporte futuro para providers cloud vía API key.

---

## Purpose

capture se enfoca en una cosa: **transcribir voz a texto de forma instantánea**.

```
Ctrl+Shift+Space → grabar → VAD → Whisper → clipboard
```

---

## Principles

| Principio | Implementación |
| :-- | :-- |
| **Simplicity** | Un propósito, bien ejecutado |
| **Performance** | Latencia mínima entre hablar y obtener texto |
| **Privacy** | Cero datos enviados a servidores externos (por defecto) |
| **Flexibility** | Local-first, con opción de cloud vía API key (futuro) |

---

## Architecture

### System overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (src/)                           │
│  React + TypeScript + Tauri IPC                                     │
│  ├── components/   → UI components                                  │
│  ├── hooks/        → useRecording, useConfig, useTauriEvents        │
│  ├── lib/          → tauri-commands.ts, utilities                   │
│  └── types/        → Contratos tipados con backend                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ IPC Commands (invoke/listen)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND (src-tauri/src/)                       │
│  Rust + Tauri 2.0                                                   │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ main.rs                                                        │  │
│  │ Entry point + IPC command handlers                            │  │
│  │ toggle_recording, get_state, get_config, set_config,         │  │
│  │ list_audio_devices, download_model, load_model, ...          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                 │                                   │
│                                 ▼                                   │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ lib.rs                                                         │  │
│  │ AppState { pipeline, config, tray_manager }                   │  │
│  │ setup_app() → plugins, global shortcuts                       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                 │                                   │
│  ┌──────────────────────────────┴───────────────────────────────┐  │
│  │                     PIPELINE (pipeline/)                      │  │
│  │  Orchestrates: audio capture → VAD → transcription → output  │  │
│  │  State machine: Idle ↔ Recording ↔ Processing                 │  │
│  │  Events: StateChanged, SpeechStarted, SpeechEnded,            │  │
│  │          TranscriptionComplete, CopiedToClipboard, Error      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│           │              │              │              │            │
│           ▼              ▼              ▼              ▼            │
│  ┌──────────────┐ ┌───────────┐ ┌──────────────┐ ┌──────────┐       │
│  │ audio/       │ │ vad/      │ │transcription/│ │ output/  │       │
│  │ cpal         │ │ silero    │ │ whisper-rs   │ │ arboard  │       │
│  │ rubato       │ │ vad-rs    │ │ whisper.cpp  │ │          │       │
│  │ crossbeam    │ │ debounce  │ │ spawn_block  │ │          │       │
│  └──────────────┘ └───────────┘ └──────────────┘ └──────────┘       │
│                                                                     │
│  ┌──────────────┐                                ┌──────────┐       │
│  │ config/      │                                │ tray/    │       │
│  │ AppConfig    │                                │ TrayIcon │       │
│  │ VadConfig    │                                │ Menu     │       │
│  │ paths        │                                │ states   │       │
│  └──────────────┘                                └──────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### Data flow detail

```
1. User: Ctrl+Shift+Space
   └── tauri_plugin_global_shortcut emite "toggle-recording"

2. Frontend: escucha evento → invoca toggle_recording IPC

3. Backend: Pipeline::toggle_recording()
   ├── If Idle:
   │   └── ensure_model_loaded()
   │   └── play_sound(Start)
   │   └── set_state(Recording)
   │   └── spawn task → run_recording_pipeline()
   │
   └── If Recording:
       └── cancel_flag.store(true)

4. run_recording_pipeline() [tokio task]:
   │
   ├── spawn_blocking: run_audio_capture()
   │   ├── AudioCapture::start() → cpal stream
   │   ├── loop:
   │   │   ├── recv chunk via crossbeam channel
   │   │   ├── resampler.process() → 16kHz mono
   │   │   ├── speech_buffer.push_pre_speech()
   │   │   ├── vad.predict() → is_speech: bool
   │   │   ├── vad_state.process() → VadEvent
   │   │   │   ├── SpeechStarted: speech_buffer.start_speech()
   │   │   │   ├── SpeechEnded: break
   │   │   │   └── None: if capturing, speech_buffer.push_speech()
   │   │   └── check cancel_flag, timeout
   │   └── return CaptureResult { audio, duration }
   │
   ├── set_state(Processing)
   ├── play_sound(Stop)
   │
   ├── transcriber.transcribe(audio) [spawn_blocking interno]
   │   ├── WhisperContext::create_state()
   │   ├── FullParams con language, no_speech_thold=0.4
   │   └── state.full() → segments → String
   │
   ├── ClipboardManager::set_text(text)
   ├── play_sound(Success)
   ├── emit PipelineEvent::CopiedToClipboard
   │
   └── set_state(Idle)
```

### VAD state machine

```
Estados de VadStateMachine:

    ┌─────────┐
    │  Idle   │◄──────────────────────────────────┐
    └────┬────┘                                   │
         │ is_speech=true                         │
         ▼                                        │
    ┌─────────────────┐                           │
    │ SpeechPending   │                           │
    │ started_at_ms   │──── is_speech=false ─────►│
    └────────┬────────┘     (falso positivo)      │
             │ elapsed >= min_speech_duration_ms  │
             │ (voz confirmada)                   │
             ▼                                    │
    ┌─────────────────┐                           │
    │  SpeechActive   │                           │
    └────────┬────────┘                           │
             │ is_speech=false                    │
             ▼                                    │
    ┌─────────────────┐                           │
    │ SilencePending  │──── is_speech=true ──────►│ SpeechActive
    │ started_at_ms   │     (silencio interrumpido)
    └────────┬────────┘
             │ elapsed >= min_silence_duration_ms
             │ (silencio confirmado)
             ▼
         SpeechEnded ──────────────────────────────►│ Idle
```

---

## Key modules

### audio/

**Captura de audio del micrófono.**

| Archivo | Propósito |
| :-- | :-- |
| `capture.rs` | `AudioCapture` — cpal stream, ring buffer, crossbeam channel |
| `resampler.rs` | `AudioResampler` — rubato, conversión a 16kHz mono |
| `devices.rs` | `list_input_devices()` — enumeración de mics |
| `playback.rs` | `play_sound_if_enabled()` — audio cues |

**Configuración:**
- Sample rate nativo del device → resampling a 16kHz
- Channels nativos → mixdown a mono
- Buffer: chunks de ~32ms

### vad/

**Voice Activity Detection.**

| Archivo | Propósito |
| :-- | :-- |
| `detector.rs` | `VadDetector` — Silero VAD wrapper, `predict() → bool` |
| `state_machine.rs` | `VadStateMachine` — estados, debouncing, `process() → VadEvent` |
| `buffer.rs` | `SpeechBuffer` — pre-buffer + acumulación de speech |

**Configuración (VadConfig):**

| Parámetro | Default | Propósito |
| :-- | :-- | :-- |
| `threshold` | 0.35 | Probabilidad mínima para considerar voz |
| `min_speech_duration_ms` | 100 | Debounce para confirmar inicio de voz |
| `min_silence_duration_ms` | 200 | Debounce para confirmar fin de voz |
| `speech_pad_ms` | 50 | Contexto incluido antes del speech |
| `energy_fallback_threshold` | 0.005 | Fallback por energía si VAD es muy agresivo |

### transcription/

**Speech-to-text con Whisper.**

| Archivo | Propósito |
| :-- | :-- |
| `whisper.rs` | `WhisperTranscriber` — wrapper de whisper-rs, inferencia |
| `model.rs` | `ModelDownloader` — descarga de Hugging Face con progreso |

**Configuración de Whisper:**

```rust
// Parámetros optimizados para velocidad + calidad
params.set_language(Some(&language));  // "es" o "en"
params.set_n_threads(4);
params.set_translate(false);
params.set_no_timestamps(true);
params.set_no_speech_thold(0.4);  // Bajado para no conflictuar con VAD
params.set_suppress_blank(true);
params.set_suppress_nst(true);
```

**Modelo:** `ggml-large-v3-turbo` — balance óptimo velocidad/calidad
**Path:** `~/.local/share/capture/models/ggml-large-v3-turbo.bin`

### pipeline/

**Orquestación del flujo.**

| Archivo | Propósito |
| :-- | :-- |
| `orchestrator.rs` | `Pipeline` — state machine, coordinación de módulos |

**Estados:**
```rust
pub enum RecordingState {
    Idle,       // Esperando. Listo para grabar.
    Recording,  // Grabando. Capturando audio, VAD activo.
    Processing, // Transcribiendo. Audio enviado a Whisper.
}
```

**Eventos:**
```rust
pub enum PipelineEvent {
    StateChanged(RecordingState),
    SpeechStarted,
    SpeechEnded { duration_ms: u64 },
    TranscriptionComplete { text, audio_duration_s, processing_time_ms },
    CopiedToClipboard { text },
    Error { message },
}
```

### config/

**Configuración de la aplicación.**

| Archivo | Propósito |
| :-- | :-- |
| `settings.rs` | `AppConfig`, `VadConfig`, `RecordingState`, paths |

**AppConfig:**
```rust
pub struct AppConfig {
    pub audio_device_id: Option<String>,
    pub language: String,           // "es" o "en"
    pub sound_enabled: bool,
    pub vad: VadConfig,
}
```

### output/

**Salida del texto.**

| Archivo | Propósito |
| :-- | :-- |
| `clipboard.rs` | `ClipboardManager` — arboard wrapper |

**Extensibilidad:** Diseñado para agregar providers:
- Notificaciones del sistema
- Archivo de logs
- Integración con apps (futuro)

### tray/

**System tray.**

| Archivo | Propósito |
| :-- | :-- |
| `manager.rs` | `TrayManager` — ícono, menú, feedback visual |

---

## Guidelines

### Code conventions

| Contexto | Idioma |
| :-- | :-- |
| Comentarios in-code | Español latinoamericano |
| Variables, funciones, tipos | English (American) |
| Docs (README, AGENTS) | Español |
| Commits | Conventional commits, inglés |

### Hardware philosophy

- **No** "CPU-only" ni "GPU-hard-dependency"
- Compilación condicional con runtime fallback
- Linux: **Vulkan** (portable, AMD/Intel/Nvidia sin drivers propietarios)
- macOS: Metal
- Windows: CUDA (si disponible) o CPU

### Error handling

```rust
// Errores propagados: anyhow::Result
pub async fn toggle_recording(&mut self) -> anyhow::Result<bool>

// Errores tipados de módulos: thiserror
#[derive(Error, Debug)]
pub enum AudioError {
    #[error("No input devices found")]
    NoInputDevices,
    // ...
}

// Log con contexto antes de propagar
log::error!("Error cargando modelo: {}", e);
return Err(e.into());
```

### Async model

| Contexto | Runtime | Razón |
| :-- | :-- | :-- |
| IPC commands | tokio (vía Tauri) | Async handlers |
| Audio capture | thread dedicado | cpal no es Send, usa crossbeam |
| Transcripción | `spawn_blocking` | CPU-bound, no bloquear runtime |

### Concurrency patterns

```rust
// Estado compartido: Arc<Mutex<T>> o Arc<TokioMutex<T>>
pub struct AppState {
    pub pipeline: Arc<TokioMutex<Pipeline>>,
    pub config: Arc<TokioMutex<AppConfig>>,
    pub tray_manager: Arc<TokioMutex<Option<TrayManager>>>,
}

// Comunicación audio thread ↔ pipeline: crossbeam channel
let (tx, rx) = crossbeam_channel::bounded(1024);

// Cancelación: AtomicBool + Ordering::SeqCst
cancel_flag.store(true, Ordering::SeqCst);
if cancel_flag.load(Ordering::Relaxed) { break; }
```

---

## Tech stack

### Frontend

| Library | Purpose | Docs |
| :-- | :-- | :-- |
| **Tauri 2.0** | Desktop app framework, IPC, global shortcuts | [tauri.app](https://tauri.app) |
| **React** | UI components | [react.dev](https://react.dev) |
| **TypeScript** | Type safety | [typescriptlang.org](https://typescriptlang.org) |

### Backend

| Library | Purpose | Docs |
| :-- | :-- | :-- |
| **cpal** | Cross-platform audio capture | [docs.rs/cpal](https://docs.rs/cpal) |
| **rubato** | Audio resampling (→16kHz mono) | [docs.rs/rubato](https://docs.rs/rubato) |
| **vad-rs** | Silero VAD wrapper | [github.com/nkeenan38/vad-rs](https://github.com/nkeenan38/vad-rs) |
| **whisper-rs** | whisper.cpp FFI bindings | [github.com/tazz4843/whisper-rs](https://github.com/tazz4843/whisper-rs) |
| **whisper.cpp** | Local whisper inference | [github.com/ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp) |
| **arboard** | Clipboard access | [docs.rs/arboard](https://docs.rs/arboard) |
| **crossbeam** | Lock-free channels | [docs.rs/crossbeam](https://docs.rs/crossbeam) |
| **tokio** | Async runtime (via Tauri) | [tokio.rs](https://tokio.rs) |
| **anyhow** | Error handling | [docs.rs/anyhow](https://docs.rs/anyhow) |

---

## File structure

```
capture/
├── AGENTS.md               # Este archivo (optimizado para LLMs)
├── README.md               # Documentación para humanos
├── Cargo.toml              # Workspace members
├── package.json            # Frontend deps
│
├── docs/                   # Documentación
│   ├── README.md           # Índice
│   └── adr/                # Architecture Decision Records
│       └── 0001-mvp-birth-plan.md
│
├── src/                    # Frontend (React + TypeScript)
│   ├── App.tsx             # Root component
│   ├── main.tsx            # Entry point
│   ├── components/         # UI components
│   ├── hooks/              # React hooks
│   ├── lib/                # Utilities
│   └── types/              # TypeScript types
│
└── src-tauri/              # Backend (Rust)
    ├── Cargo.toml          # Rust deps
    ├── tauri.conf.json     # Tauri config
    ├── capabilities/       # Tauri 2.0 permissions
    ├── assets/             # Icons, sounds
    └── src/
        ├── main.rs         # Entry, IPC handlers
        ├── lib.rs          # AppState, setup_app, re-exports
        ├── audio/          # Audio capture
        │   ├── mod.rs
        │   ├── capture.rs
        │   ├── resampler.rs
        │   ├── devices.rs
        │   └── playback.rs
        ├── vad/            # Voice activity detection
        │   ├── mod.rs
        │   ├── detector.rs
        │   ├── state_machine.rs
        │   └── buffer.rs
        ├── transcription/  # Whisper integration
        │   ├── mod.rs
        │   ├── whisper.rs
        │   └── model.rs
        ├── pipeline/       # Orchestration
        │   ├── mod.rs
        │   └── orchestrator.rs
        ├── config/         # Configuration
        │   ├── mod.rs
        │   └── settings.rs
        ├── output/         # Clipboard, future outputs
        │   ├── mod.rs
        │   └── clipboard.rs
        └── tray/           # System tray
            ├── mod.rs
            └── manager.rs
```

---

## Common tasks

### Development

```bash
# Run dev mode (hot reload frontend, rebuild backend)
cd apps/capture
pnpm tauri dev

# Only frontend dev server
pnpm dev

# Only backend check
cargo check
cargo clippy

# Run tests
cargo test
```

### Build

```bash
# Production build
cd apps/capture
pnpm tauri build

# Debug build (faster, unoptimized)
pnpm tauri build --debug
```

### Model location

```
~/.local/share/capture/models/ggml-large-v3-turbo.bin
```

### Logs

```bash
# Ver logs en tiempo real
RUST_LOG=debug pnpm tauri dev
```

---

## Known trade-offs

| Decisión | Trade-off | Razón |
| :-- | :-- | :-- |
| `spawn_blocking` para audio | Overhead de thread | cpal no es Send, necesario |
| `no_speech_thold: 0.4` | Más falsos positivos de Whisper | VAD ya filtra, evita doble filtrado |
| large-v3-turbo | ~3GB de modelo | Balance óptimo velocidad/calidad |
| Silero VAD | Dependency adicional | Mucho más rápido que VAD de Whisper |
| crossbeam vs tokio channels | Dos tipos de channels | crossbeam para sync, tokio para async |
