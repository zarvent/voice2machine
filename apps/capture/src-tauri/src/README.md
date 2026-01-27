# src

Módulos Rust del backend de capture.

Cada módulo tiene una **responsabilidad única** y bien definida. Se comunican a través de interfaces explícitas, no estado global implícito.

---

## Arquitectura

### Flujo de datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   🎤 MICRÓFONO                                                      │
│        │                                                             │
│        ▼                                                             │
│   ┌─────────────────┐                                               │
│   │    audio/       │  cpal + rubato                                │
│   │    AudioCapture │  → Stream de f32 @ 16kHz mono                 │
│   └────────┬────────┘                                               │
│            │ crossbeam channel                                       │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │    vad/         │  Silero VAD + State Machine                   │
│   │    VadDetector  │  → VadEvent: SpeechStarted/Ended              │
│   └────────┬────────┘                                               │
│            │ speech segments                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │  transcription/ │  whisper-rs + whisper.cpp                     │
│   │  Whisper        │  → String (texto transcrito)                  │
│   └────────┬────────┘                                               │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │    output/      │  arboard                                      │
│   │    Clipboard    │  → Texto en clipboard del sistema             │
│   └─────────────────┘                                               │
│                                                                      │
│   ─────────────────────────────────────────────────────────────      │
│   ORQUESTACIÓN: pipeline/Pipeline coordina todo el flujo            │
│   CONFIGURACIÓN: config/AppConfig define parámetros                 │
│   UI: tray/TrayManager muestra estado en system tray                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### State machine de grabación

```
┌──────────────────────────────────────────────────────────────────┐
│                    RECORDING STATE MACHINE                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│                      ┌────────────┐                              │
│                      │            │                              │
│      ┌───────────────│    Idle    │◄──────────────────┐         │
│      │               │            │                    │         │
│      │               └─────┬──────┘                    │         │
│      │                     │                           │         │
│      │        toggle_recording()                       │         │
│      │                     │                           │         │
│      │                     ▼                           │         │
│      │               ┌────────────┐                    │         │
│      │               │            │                    │         │
│      │               │ Recording  │──── cancel ────────┤         │
│      │               │            │                    │         │
│      │               └─────┬──────┘                    │         │
│      │                     │                           │         │
│      │           speech_ended / timeout                │         │
│      │                     │                           │         │
│      │                     ▼                           │         │
│      │               ┌────────────┐                    │         │
│      │               │            │                    │         │
│      └─── cancel ────│ Processing │────── done ───────►│         │
│                      │            │                    │         │
│                      └────────────┘                    │         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Módulos

### `audio/`

**Captura de audio del micrófono del sistema.**

| Componente | Responsabilidad |
| :-- | :-- |
| `AudioCapture` | Stream de audio vía cpal, buffer ring |
| `AudioResampler` | Conversión a 16kHz mono vía rubato |
| `devices` | Enumeración de dispositivos de entrada |
| `playback` | Audio cues (start, stop, success) |

**Output:** `Vec<f32>` PCM samples @ 16kHz mono

### `vad/`

**Voice Activity Detection con Silero.**

| Componente | Responsabilidad |
| :-- | :-- |
| `VadDetector` | Wrapper de silero-vad, probabilidad de voz |
| `VadStateMachine` | Estados: Idle → SpeechPending → SpeechActive → SilencePending |
| `SpeechBuffer` | Pre-buffer + acumulación de speech segments |

**State machine con debouncing:**
- `min_speech_duration_ms`: evita falsos positivos
- `min_silence_duration_ms`: evita cortes prematuros
- `speech_pad_ms`: incluye contexto previo al speech

### `transcription/`

**Speech-to-text con Whisper.**

| Componente | Responsabilidad |
| :-- | :-- |
| `WhisperTranscriber` | Wrapper de whisper-rs, inferencia |
| `ModelDownloader` | Descarga modelo de Hugging Face |

**Configuración optimizada:**
- Modelo: `ggml-large-v3-turbo`
- `no_speech_thold: 0.4` (ajustado para no conflictuar con VAD)
- Ejecución en `spawn_blocking` (CPU-bound)

### `pipeline/`

**Orquestación del flujo completo.**

| Componente | Responsabilidad |
| :-- | :-- |
| `Pipeline` | State machine de grabación, coordinación |
| `PipelineEvent` | Eventos para actualizar UI |
| `PipelineConfig` | Configuración de duración máxima, etc. |

**Flujo:**
1. `toggle_recording()` inicia/cancela
2. Audio capture en `spawn_blocking` (cpal no es Send)
3. VAD procesa en tiempo real
4. Transcripción async
5. Clipboard + eventos a UI

### `config/`

**Configuración de la aplicación.**

| Componente | Responsabilidad |
| :-- | :-- |
| `AppConfig` | Configuración de usuario (device, language, VAD params) |
| `VadConfig` | Thresholds y tiempos de VAD |
| `RecordingState` | Estado serializable para frontend |
| `get_model_path()` | Path al modelo Whisper |

**Path de modelo:** `~/.local/share/capture/models/`

### `output/`

**Salida del texto transcrito.**

| Componente | Responsabilidad |
| :-- | :-- |
| `ClipboardManager` | Copia texto vía arboard |

**Extensible:** Diseñado para futuras salidas (notificaciones, archivos, integraciones).

### `tray/`

**Integración con system tray.**

| Componente | Responsabilidad |
| :-- | :-- |
| `TrayManager` | Ícono, menú contextual, feedback visual |

**Estados visuales:** Ícono cambia según `RecordingState`.

---

## Entry points

| Archivo | Propósito |
| :-- | :-- |
| `main.rs` | Entry point de Tauri, IPC command handlers |
| `lib.rs` | `AppState`, `setup_app()`, re-exports de módulos |
