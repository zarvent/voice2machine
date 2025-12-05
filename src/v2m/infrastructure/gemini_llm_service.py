"""
módulo que implementa el servicio de llm utilizando la api de google gemini

esta es una implementación concreta de la interfaz `llmservice` es responsable
de toda la lógica de comunicación con el servicio de google gemini incluyendo
la autenticación la construcción de la solicitud y el manejo de reintentos
"""

from v2m.application.llm_service import LLMService
from v2m.config import config, BASE_DIR
from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from v2m.domain.errors import LLMError
from v2m.core.logging import logger
import httpx

class GeminiLLMService(LLMService):
    """
    implementación del `llmservice` que se conecta con google gemini

    gestiona la configuración del cliente de la api la formulación de las
    peticiones y la lógica de reintentos para asegurar una comunicación robusta
    """
    def __init__(self) -> None:
        """
        inicializa el servicio de google gemini

        este constructor realiza las siguientes acciones
        1 obtiene la configuración y la api key desde `config.py` (pydantic settings)
        2 configura e instancia el cliente de la api de google
        3 almacena los parámetros del modelo y la configuración de reintentos

        raises:
            LLMError: si la `GEMINI_API_KEY` no se encuentra en la configuración
        """
        # --- carga de configuración y secretos ---
        gemini_config = config.gemini
        api_key = gemini_config.api_key

        if not api_key:
            raise LLMError("la variable de entorno GEMINI_API_KEY no fue encontrada")

        # --- inicialización del cliente de la api ---
        # la librería de GOOGLE utiliza `GOOGLE_API_KEY` por defecto
        os.environ["GOOGLE_API_KEY"] = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = gemini_config.model
        self.temperature = gemini_config.temperature
        self.max_tokens = gemini_config.max_tokens

        # cargar system prompt
        prompt_path = BASE_DIR / "prompts" / "refine_system.txt"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read()
        except FileNotFoundError:
            logger.warning("system prompt no encontrado usando default")
            self.system_instruction = "eres un editor de texto experto"

    # Retry solo para errores transitorios de red/rate-limit
    # Tiempos reducidos para baja latencia: 0.5s, 1s, 2s (máx 3.5s total)
    @retry(
        stop=stop_after_attempt(config.gemini.retry_attempts),
        wait=wait_exponential(
            multiplier=0.5,  # Reducido de 1
            min=0.5,         # Reducido de 2
            max=2,           # Reducido de 10
        ),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, ConnectionError)),
        reraise=True,  # Re-lanzar si se agotan los intentos
    )
    async def process_text(self, text: str) -> str:
        """
        procesa un texto utilizando el modelo de google gemini

        implementa una estrategia de reintentos con `tenacity` para manejar
        errores transitorios de red o de la api de forma resiliente

        args:
            text: el texto a procesar

        returns:
            el texto refinado por el llm

        raises:
            LLMError: si la comunicación con la api falla después de todos los reintentos
        """
        try:
            logger.info("procesando texto con GEMINI...")
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
                "system_instruction": self.system_instruction,
            }

            # --- construcción del payload para la api ---
            contents = [
                genai.types.Content(
                    role="user",
                    parts=[genai.types.Part(text=text)]
                )
            ]

            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=generation_config
            )
            logger.info("procesamiento con GEMINI completado")
            if response.text:
                return response.text.strip()
            else:
                raise LLMError("respuesta vacía de GEMINI")
        except Exception as e:
            # --- manejo de errores ---
            # se captura cualquier excepción de la librería de GOOGLE o de red
            # y se relanza como un error de dominio para no filtrar detalles
            # de la infraestructura a la capa de aplicación
            error_msg = str(e)
            if "API key not valid" in error_msg:
                logger.critical("GEMINI_API_KEY invalida o expirada")
                raise LLMError("API Key de Gemini inválida. Revisa tu archivo .env") from e

            logger.error(f"error procesando texto con GEMINI {e}")
            raise LLMError("falló el procesamiento de texto con GEMINI") from e
