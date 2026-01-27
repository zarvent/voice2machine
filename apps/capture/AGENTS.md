## overview

`capture` is a voice2machine app located in `voice2machine/apps/capture`.

voice2machine is a monorepo containing text transcription tools.

---

## purpose

capture will focus 100% on one thing: **transcribing the input assigned to it**.

---

## principles

- simplicity
- performance
- efficiency

---

## guidelines

### code conventions

- in all in code comments use spanish latin american native, everything else that is technical, variables, etc., uses native American English.

### hardware philosophy

- Don't make it "CPU-only" or "GPU-hard-dependency." In 2026, the standard is conditional compilation with runtime fallback.
- Linux: Use Vulkan. It's much more portable than CUDA and doesn't require proprietary Nvidia drivers (it works on AMD/Intel).

---

## tech stack

### front end

| library | description | docs |
| --- | --- | --- |
| **Tauri 2.0** | framework for creating desktop applications using web technologies. It allows you to manage windows, tray icons, and global shortcuts with a Rust backend. | [tauri.app](http://tauri.app) |
| **React** | library for building user interfaces. Used for the frontend/UI configuration and visual feedback. | [react.dev](http://react.dev) |
| **TypeScript** | superset of JavaScript with static typing. Provides type safety and better DX for frontend development. | [typescriptlang.org](http://typescriptlang.org) |

### back end

| library | description | docs |
| --- | --- | --- |
| **cpal** | low-level library for cross-platform audio capture and output (Cross-Platform Audio Library). Allows access to the system microphone. | [docs.rs/cpal](http://docs.rs/cpal) |
| **rubato** | audio resampling library. Required to convert microphone audio to 16kHz mono, the format required by Whisper. | [docs.rs/rubato](http://docs.rs/rubato) |
| **vad-rs** | Rust wrapper for Silero VAD. Detects voice activity to filter silence before sending audio to Whisper, reducing load and improving latency. | [github.com/nkeenan38/vad-rs](http://github.com/nkeenan38/vad-rs) |
| **whisper-rs** | Rust FFI bindings to whisper.cpp. Allows Whisper to run locally with GPU support (Metal, CUDA, Vulkan) and all available models. | [github.com/tazz4843/whisper-rs](http://github.com/tazz4843/whisper-rs) |
| **whisper.cpp** | C++ implementation of OpenAI's Whisper model. It is the transcription engine that whisper-rs uses underneath. | [github.com/ggerganov/whisper.cpp](http://github.com/ggerganov/whisper.cpp) |
| **arboard** | Rust library for interacting with the system clipboard. Used to copy the transcribed text to the clipboard. | [docs.rs/arboard](http://docs.rs/arboard) |
