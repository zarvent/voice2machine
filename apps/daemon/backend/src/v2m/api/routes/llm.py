from fastapi import APIRouter

from v2m.api.app import state
from v2m.api.schemas import LLMResponse, ProcessTextRequest, TranslateTextRequest

router = APIRouter(prefix="/llm")


@router.post("/process", response_model=LLMResponse)
async def process_text(request: ProcessTextRequest) -> LLMResponse:
    """Procesa texto con el LLM (refinamiento, corrección, etc.)."""
    return await state.llm.process_text(request.text)


@router.post("/translate", response_model=LLMResponse)
async def translate_text(request: TranslateTextRequest) -> LLMResponse:
    """Traduce texto al idioma destino especificado."""
    return await state.llm.translate_text(request.text, request.target_lang)
