from fastapi import APIRouter

from v2m.api.app import state
from v2m.api.schemas import HealthResponse, StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Obtiene el estado actual del daemon (grabación, modelo cargado, etc.)."""
    return state.recording.get_status()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Verifica la salud del servicio API."""
    return HealthResponse()
