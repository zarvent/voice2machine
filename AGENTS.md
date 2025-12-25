# Voice2Machine (V2M)

Local-first voice dictation tool that converts speech-to-text using local GPU (Whisper) with optional LLM post-processing (Gemini).

---

## Setup Commands

```bash
# Backend (Python)
cd apps/backend && source venv/bin/activate
pip install -e .                       # install package

# Frontend (Tauri + React)
cd apps/frontend
npm install                            # install deps
npm run tauri dev                      # start dev server
```

## Build & Test Commands

```bash
# Backend - these are safe to auto-run
pytest -v                              # run all tests
pytest --cov=src/v2m tests/            # with coverage
ruff check src/ --fix                  # lint and auto-fix
ruff format src/                       # format code

# Frontend - these are safe to auto-run
npm run build                          # TypeScript + Vite build
npm run tauri build                    # production build

# System scripts
scripts/v2m-daemon.sh start            # start daemon
scripts/v2m-daemon.sh stop             # stop daemon
scripts/v2m-toggle.sh                  # toggle recording
scripts/v2m-llm.sh                     # refine with Gemini
```

---

## Tech Stack

### Backend (`apps/backend`)

- **Python 3.12+** with strict type hints
- **Core libs**: `faster-whisper`, `sounddevice`, `pydantic`, `google-genai`
- **Linting**: `ruff` (strict, 120 chars/line)
- **Testing**: `pytest` with asyncio mode

### Frontend (`apps/frontend`)

- **Tauri v2** (Rust core) + **React v19**
- **TypeScript** strict mode
- **Vite v7** for bundling
- **CSS Modules** (clean minimalist aesthetic)

### Infrastructure (`scripts`)

- **Target OS**: Linux (Debian-based)
- **System tools**: `xclip` (clipboard), `notify-send` (notifications)

---

## Project Structure

```
v2m/
├── apps/
│   ├── backend/
│   │   ├── src/v2m/
│   │   │   ├── core/           # DI container, Command Bus
│   │   │   ├── domain/         # interfaces, entities, errors
│   │   │   ├── application/    # command handlers
│   │   │   └── infrastructure/ # Whisper, Audio, Gemini implementations
│   │   ├── tests/              # unit and integration tests
│   │   ├── prompts/            # LLM prompts
│   │   └── config.toml         # application config
│   │
│   └── frontend/
│       ├── src/                # React components
│       └── src-tauri/          # Rust backend
│
├── scripts/                    # bash scripts for orchestration
│   ├── v2m-daemon.sh           # main background service
│   ├── v2m-toggle.sh           # recording trigger
│   └── v2m-llm.sh              # LLM refinement trigger
│
└── docs/                       # technical documentation
    └── arquitectura.md         # architecture decisions and diagrams
```

---

## Code Style

### Python

- Always use strict type hints for all arguments and return values
- Follow `ruff` configuration in `pyproject.toml`
- Use domain-specific exceptions (e.g., `MicrophoneNotFoundError`)
- Run `ruff check --fix` and `ruff format` before committing

```python
# ✅ Good - strict types, descriptive names, proper error handling
async def transcribe_audio(audio_path: Path, model: str = "large-v3") -> Transcription:
    if not audio_path.exists():
        raise AudioFileNotFoundError(f"file not found: {audio_path}")
    return await whisper_service.transcribe(audio_path, model)

# ❌ Bad - no types, vague names, no error handling
async def proc(p):
    return await ws.t(p)
```

### TypeScript/React

- TypeScript strict mode is mandatory
- Icon-only buttons MUST have `aria-label`
- Error banners MUST use `role="alert"` and `aria-live="assertive"`
- Modals MUST close on `Escape` key
- Use `React.memo`, `useCallback`, `useMemo` to prevent unnecessary re-renders

```typescript
// ✅ Good - aria-label, memo, keyboard handling
const RecordButton: React.FC<Props> = React.memo(({ onToggle, recording }) => (
  <button
    onClick={onToggle}
    onKeyDown={(e) => e.key === "Escape" && onToggle()}
    aria-label={recording ? "stop recording" : "start recording"}
  >
    {recording ? "⏹️" : "🎙️"}
  </button>
));

// ❌ Bad - no aria-label, no memo
const BadButton = ({ onClick }) => <button onClick={onClick}>🎙️</button>;
```

---

## Architecture Rules

This project follows **Hexagonal Architecture** (Ports and Adapters):

- Business logic in `core/` and `domain/` MUST NOT import from `infrastructure/`
- Dependencies flow inward: Infrastructure → Application → Domain → Core
- Use dependency injection for swapping implementations

---

## Testing Instructions

1. Run unit tests for the specific module you changed:
   - `pytest tests/unit/ -v`
2. Run integration tests if you modified infrastructure:
   - `pytest tests/integration/ -v`
3. Verify GPU acceleration works:
   - `python scripts/test_whisper_gpu.py`
4. Check daemon health:
   - `python scripts/verify_daemon.py`

Always add or update tests for code you change, even if not explicitly requested.

---

## Security Considerations

- **NEVER** commit API keys or secrets (use `.env` files, already in `.gitignore`)
- **NEVER** hardcode absolute paths (use config files or environment variables)
- **NEVER** modify `venv/`, `node_modules/`, or generated files
- Audio data is processed locally only—never transmitted externally without explicit user action
- LLM processing (Gemini) only occurs when user explicitly triggers `v2m-llm.sh`

---

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/descriptive-name

# Before committing, always run
ruff check apps/backend/src/ --fix
ruff format apps/backend/src/
cd apps/frontend && npm run build     # verify TypeScript

# Commit message format
git commit -m "feat(backend): add whisper-turbo model support"
# types: feat, fix, docs, style, refactor, test, chore
# scopes: backend, frontend, scripts, docs
```

---

## Boundaries

### ✅ Always do

- Follow hexagonal architecture (core/domain never import infrastructure)
- Write tests for new functionality
- Use strict type hints in Python and TypeScript
- Validate with `ruff` and `tsc` before commit
- Keep documentation in `docs/` synchronized

### ⚠️ Ask first

- Config schema changes (`config.toml`)
- Adding new dependencies
- Modifying system scripts (`scripts/v2m-*.sh`)
- Changes affecting audio pipeline

### 🚫 Never do

- Commit secrets or API keys
- Modify `venv/`, `node_modules/`, or generated files
- Hardcode absolute paths
- Break hexagonal architecture layer separation
- Remove failing tests without authorization

---

## Verification Resources

- `scripts/test_whisper_gpu.py` — verify GPU acceleration
- `scripts/verify_daemon.py` — check daemon status
- `scripts/health_check.py` — full system diagnostics
- `scripts/diagnose_audio.py` — audio device diagnostics
- `scripts/check_cuda.py` — verify CUDA configuration

---

## Documentation

- `docs/arquitectura.md` — architecture decisions and flow diagrams
- `apps/backend/README.md` — backend setup and usage
- `apps/frontend/README.md` — frontend setup and usage
- `scripts/README.md` — system scripts documentation

---

## Monorepo Note

Nested `AGENTS.md` files are supported. Place package-specific instructions in subdirectories, and the nearest `AGENTS.md` will take precedence for that context.
