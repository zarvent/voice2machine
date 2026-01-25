---
name: backend-commit
description: Automates the commit workflow for the Voice2Machine backend. Ensures code hygiene (Ruff), rigorous testing (Pytest), environment health (Health Check), and "Docs-as-Code" synchronization in Native Latin American Spanish. Use this when finalizing changes in 'apps/daemon/backend' to ensure compliance with Hexagonal Architecture and Conventional Commits.
---

# Backend Commit Workflow (Voice2Machine)

This skill guides the agent through the mandatory verification and commitment process for the `apps/daemon/backend` module.

## Core Philosophical Alignment

- **Local-First**: No telemetry, no cloud leaks.
- **Hexagonal Architecture**: Dependencies point inwards. Domain remains isolated.
- **SOTA 2026**: Python 3.12+ (asyncio-native), Pydantic V2, Ruff.

## Step 1: Mandatory Hygiene

Before any commit, you **MUST** run the following tools in `/home/zarvent/developer/voice2machine/apps/daemon/backend`:

1. **Linter & Auto-fix**:
   ```bash
   ruff check src/ --fix
   ```
2. **Formatter**:
   ```bash
   ruff format src/
   ```

## Step 2: Verification Suite

Ensure the stability of the system.

1. **Unit & Integration Tests**:
   ```bash
   pytest tests/
   ```
2. **Environment Health Check**:
   Run the specialized diagnostic script:
   ```bash
   python scripts/diagnostics/health_check.py
   ```

## Step 3: Docs-as-Code Synchronization

Functional changes **MUST** be documented immediately.

- **Location**: `/home/zarvent/developer/voice2machine/docs/docs/es/`
- **Language**: Native Latin American Spanish.
- **Standards**: WCAG 2.2+, Diátaxis (Tutorials, How-to, Reference, Explanation).
- **Update Rule**: If you added a feature or fixed a bug, the corresponding `.md` file in the docs must reflect it. If it's a new feature, update `CHANGELOG.md` and `LEEME.md`.

## Step 4: Conventional Commit Message

Generate a commit message in **English** using this format: `type(scope): description`.

### Types

- `feat`: New feature (e.g., new VAD logic).
- `fix`: Bug fix (e.g., fixing a race condition in audio capture).
- `docs`: Documentation only changes.
- `refactor`: Code change that neither fixes a bug nor adds a feature.
- `test`: Adding missing tests or correcting existing tests.

### Scopes (Voice2Machine Specific)

- `api`: FastAPI routes, schemas, models.
- `whisper`: AI transcription logic.
- `vad`: Voice Activity Detection components.
- `audio`: Rust bridge or `sounddevice` adapters.
- `orchestration`: Business workflows and lifecycle.
- `shared`: Config, errors, and common utils.

### Example

`feat(whisper): add persistent worker with VRAM pressure detection`

## Step 5: Self-Correction & Quality Vectors (SOTA 2026)

Before finalizing the commit, mentally apply these filters:

1. **Critical Eye**: "Does this code look human-made or 'AI-coded'?" (Avoid generic/repetitive AI patterns).
2. **Privacy First**: "Did I accidentally hardcode 127.0.0.1 or an API key?"
3. **Async Hygiene**: "Did I introduce any blocking `time.sleep` or sync I/O in an async path?"
4. **Hexagonal Check**: "Is my feature leaking implementation details from `infrastructure` into the `orchestration` layer?"

## Step 6: Pull Request Preparation

Verify that you have fulfilled the requirements in `.github/pull_request_template.md`:

- [ ] Tests passed (`pytest`).
- [ ] Code is linted and formatted (`ruff`).
- [ ] Documentation updated in Spanish (`docs/docs/es/`).
- [ ] Conventional Commit message used.
- [ ] No secrets or hardcoded paths.

### Pro-Tip: Automated PR Description

When creating the PR, you can use the following structure in Spanish based on your changes:

- **Descripción**: Resumen claro del impacto.
- **Cambios Técnicos**: Lista de archivos y lógica modificada.
- **Testing**: Especifica si corriste `pytest tests/` y los resultados.
- **Checklist**: Confirma que actualizaste el `CHANGELOG.md` si es un `feat` o `fix`.
