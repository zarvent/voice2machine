# `v2m` (Python backend package)

`v2m` is the main backend package for Voice2Machine.

It provides:

- The long-running **daemon** (FastAPI Server) that keeps inference “warm”.
- A **REST API** used by CLI and GUI clients.
- A **Feature-Based** layout (`api/`, `features/`, `orchestration/`, `shared/`).

This package is designed to be **local-first**: by default, it does not expose a network API to the outside world (binds to localhost).

## Quick start (developer)

From `apps/backend/` (recommended):

```bash
python -m v2m.main
```

Then, from another terminal, you can interact with the API:

```bash
curl -X POST http://localhost:8765/health
curl -X POST http://localhost:8765/toggle
```

## Package map

- `main.py`: Entry point (FastAPI server runner).
- `api/`: FastAPI application, routes, and schemas.
- `orchestration/`: Business workflows (Recording, LLM).
- `features/`: Modular domain logic (Audio, LLM, Processing).
- `shared/`: Shared utilities, config, and logging.

## Architecture

The system follows a Modular Monolith architecture where features are self-contained but share common utilities.
Communication happens via async function calls within the process, orchestrated by `orchestration/` workflows.
External communication is handled solely via the `api/` layer (FastAPI).

## Config + secrets

Default config is committed at `apps/backend/config.toml`.

- Use env vars or `.env` for secrets (e.g. `GEMINI_API_KEY`).
- Keep runtime paths XDG-compliant via `v2m.shared.utils.paths`.

## Troubleshooting

- **Server isn't running**: start with `python -m v2m.main`.
- **Port already in use**: Check if another instance is running on port 8765.
- **High latency on first command**: expected if models aren’t warmed; daemon mode is intended to keep inference hot.
