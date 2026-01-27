### STACKS

`FRONT END`

**Tauri 2.0:** Framework for creating desktop applications using web technologies. It allows you to manage windows, tray icons, and global shortcuts with a Rust backend.

https://v2.tauri.app/start/

**React:** Library for building user interfaces. Used for the frontend/UI configuration and visual feedback.

https://react.dev/

**TypeScript:** Superset of JavaScript with static typing. Provides type safety and better DX for frontend development.

https://www.typescriptlang.org/docs/

`BACK END`

**cpal:** Low-level library for cross-platform audio capture and output (Cross-Platform Audio Library). Allows access to the system microphone.

https://docs.rs/cpal/latest/cpal/

**rubato:** Audio resampling library. Required to convert microphone audio to 16kHz mono, the format required by Whisper.

https://docs.rs/rubato/latest/rubato/

**vad-rs:** Rust wrapper for Silero VAD. Detects voice activity to filter silence before sending audio to Whisper, reducing load and improving latency.

https://github.com/nkeenan38/vad-rs

**whisper-rs:** Rust FFI bindings to whisper.cpp. Allows Whisper to run locally with GPU support (Metal, CUDA, Vulkan) and all available models.

https://github.com/tazz4843/whisper-rs

**whisper.cpp:** C++ implementation of OpenAI's Whisper model. It is the transcription engine that whisper-rs uses underneath.

https://github.com/ggerganov/whisper.cpp

**arboard:** Rust library for interacting with the system clipboard. Used to copy the transcribed text to the clipboard.

https://docs.rs/arboard/latest/arboard/
