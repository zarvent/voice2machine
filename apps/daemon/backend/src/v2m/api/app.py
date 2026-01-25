"""FastAPI Application Factory for Voice2Machine (SOTA 2026)."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from v2m.orchestration.llm_workflow import LLMWorkflow
from v2m.orchestration.recording_workflow import RecordingWorkflow
from v2m.shared.logging import logger


class DaemonState:
    """Estado global del daemon (Singleton para la API)."""

    def __init__(self) -> None:
        """Inicializa los componentes del estado global."""
        self._recording_workflow: RecordingWorkflow | None = None
        self._llm_workflow: LLMWorkflow | None = None
        self._websocket_clients: set[WebSocket] = set()

    @property
    def recording(self) -> RecordingWorkflow:
        """Obtiene la instancia perezosa del workflow de grabación."""
        if self._recording_workflow is None:
            self._recording_workflow = RecordingWorkflow(broadcast_fn=self.broadcast_event)
        return self._recording_workflow

    @property
    def llm(self) -> LLMWorkflow:
        """Obtiene la instancia perezosa del workflow de LLM."""
        if self._llm_workflow is None:
            self._llm_workflow = LLMWorkflow()
        return self._llm_workflow

    async def broadcast_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emite un evento a todos los clientes WebSocket conectados."""
        if not self._websocket_clients:
            return

        message = {"event": event_type, "data": data}
        disconnected: list[WebSocket] = []

        for ws in self._websocket_clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self._websocket_clients.discard(ws)


# Singleton
state = DaemonState()

_background_tasks: set[asyncio.Task[None]] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    logger.info("🚀 Iniciando V2M API Server (Feature-Based Architecture)...")

    # Warmup en background
    task = asyncio.create_task(state.recording.warmup())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    yield

    logger.info("🛑 Apagando V2M API Server...")
    await state.recording.shutdown()


def create_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""
    app = FastAPI(
        title="Voice2Machine API",
        description="Transcripción de voz local con Whisper (Feature-Based)",
        version="0.3.0",
        lifespan=lifespan,
    )

    from v2m.api.routes import llm, recording, status

    app.include_router(recording.router)
    app.include_router(llm.router)
    app.include_router(status.router)

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket):
        await websocket.accept()
        state._websocket_clients.add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            state._websocket_clients.discard(websocket)

    return app


app = create_app()
