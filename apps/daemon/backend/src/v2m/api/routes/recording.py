from fastapi import APIRouter

from v2m.api.app import state
from v2m.api.schemas import ToggleResponse

router = APIRouter()


@router.post("/toggle", response_model=ToggleResponse)
async def toggle_recording() -> ToggleResponse:
    """Inicia o detiene la grabación dependiendo del estado actual."""
    return await state.recording.toggle()


@router.post("/start", response_model=ToggleResponse)
async def start_recording() -> ToggleResponse:
    """Inicia explícitamente la grabación."""
    return await state.recording.start()


@router.post("/stop", response_model=ToggleResponse)
async def stop_recording() -> ToggleResponse:
    """Detiene la grabación y realiza la transcripción final."""
    return await state.recording.stop()
