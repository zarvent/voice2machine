# Voice2Machine (V2M) Project Instructions

This document provides context and guidelines for GitHub Copilot to assist effectively with the Voice2Machine project.

## Project Overview

Voice2Machine (V2M) is a **local-first** voice dictation tool designed to convert speech to text using a local GPU (via Whisper) and insert it into any operating system field. It also offers optional post-processing using an LLM (Google Gemini).

**Key Philosophy:**
- **Local-First:** Audio processing happens locally to ensure privacy and speed.
- **Hexagonal Architecture:** Strict separation of concerns (Core, Domain, Application, Infrastructure).
- **CQRS:** Command Query Responsibility Segregation for handling user intentions.
- **Sustainable Code:** Prioritizes readability and maintainability over premature optimization.

## Tech Stack

### Backend (`apps/backend`)
- **Language:** Python 3.12+
- **Core Libraries:** `faster-whisper`, `sounddevice`, `pydantic`, `google-genai`.
- **Linting/Formatting:** `ruff` (strict configuration, 120 line length).
- **Testing:** `pytest` (asyncio mode), `pytest-mock`.
- **Type Checking:** Strict type hints (validated by `ruff`'s type-aware linting).

### Frontend (`apps/frontend`)
- **Framework:** Tauri v2 (Rust core) + React v19.
- **Language:** TypeScript.
- **Build Tool:** Vite.
- **Styling:** CSS Modules / Standard CSS (Clean Minimalist aesthetic).

### Infrastructure (`scripts`)
- **OS:** Linux (Debian-based targets).
- **Tools:** `xclip` (clipboard), `notify-send` (notifications), `bash` scripts for IPC and orchestration.

## Coding Guidelines

### General
- **Architecture:** Follow Hexagonal Architecture principles. Business logic (`src/v2m/core`, `src/v2m/domain`) must not depend on infrastructure (`src/v2m/infrastructure`).
- **Language:** All documentation, comments, logs, and user-facing strings must be in **humanized Latin American Spanish** (lowercase, minimal punctuation except parentheses).
- **License:** All source files must include the GPLv3 license header.

### Python (Backend)
- **Typing:** Use strict type hints for all function arguments and return values.
- **Style:** Follow `ruff` configuration in `pyproject.toml`.
- **Error Handling:** Use domain-specific exceptions (e.g., `MicrophoneNotFoundError`).
- **Logging:** Structured JSON logging via `python-json-logger`.

### TypeScript/React (Frontend)
- **Accessibility:**
    - Icon-only buttons MUST have `aria-label`.
    - Error banners MUST use `role="alert"` and `aria-live="assertive"`.
    - Modals MUST close on `Escape`.
- **Performance:** Use `React.memo`, `useCallback`, and `useMemo` to prevent unnecessary re-renders.

## Project Structure

- **`apps/backend/`**: Python source code.
    - `src/v2m/`: Main package.
        - `core/`: DI container, Command Bus.
        - `domain/`: Interfaces, Entities.
        - `application/`: Command Handlers.
        - `infrastructure/`: Implementations (Whisper, Audio, Gemini).
    - `tests/`: Unit and integration tests.
    - `config.toml`: Application configuration.
- **`apps/frontend/`**: GUI application.
    - `src/`: React components and logic.
    - `src-tauri/`: Rust backend for Tauri.
- **`scripts/`**: Shell scripts for system interaction.
    - `v2m-daemon.sh`: Main background service.
    - `v2m-toggle.sh`: Trigger for recording/transcribing.
    - `v2m-llm.sh`: Trigger for LLM refinement.
- **`docs/`**: Comprehensive documentation (Architecture, Installation, etc.).

## Resources

- **Verification Scripts:**
    - `scripts/test_whisper_gpu.py`: Verify GPU acceleration.
    - `scripts/verify_daemon.py`: Check daemon status.
- **Documentation:** Refer to `docs/arquitectura.md` for architectural decisions and flow diagrams.
