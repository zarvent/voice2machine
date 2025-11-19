"""
módulo que implementa el servicio de LLM utilizando la API de GOOGLE GEMINI

esta es una implementación concreta de la interfaz `llmservice` es responsable
de toda la lógica de comunicación con el servicio de GOOGLE GEMINI incluyendo
la autenticación la construcción de la solicitud y el manejo de reintentos
"""

from whisper_dictation.application.llm_service import LLMService
from whisper_dictation.config import config, BASE_DIR
from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from whisper_dictation.domain.errors import LLMError
from whisper_dictation.core.logging import logger

class GeminiLLMService(LLMService):
    """
    implementación del `llmservice` que se conecta con GOOGLE GEMINI

    gestiona la configuración del cliente de la API la formulación de las
    peticiones y la lógica de reintentos para asegurar una comunicación robusta
    """
    def __init__(self) -> None:
        """
        inicializa el servicio de GOOGLE GEMINI

        este constructor realiza las siguientes acciones
        1.  obtiene la configuración y la API KEY desde `config.py` (pydantic settings)
        2.  configura e instancia el cliente de la API de GOOGLE
        3.  almacena los parámetros del modelo y la configuración de reintentos

        raises:
            llmerror: si la `GEMINI_API_KEY` no se encuentra en la configuración
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

    @retry(
        stop=stop_after_attempt(config.gemini.retry_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=config.gemini.retry_min_wait,
            max=config.gemini.retry_max_wait,
        ),
    )
    async def process_text(self, text: str) -> str:
        """
        procesa un texto utilizando el modelo de GOOGLE GEMINI

        implementa una estrategia de reintentos con `tenacity` para manejar
        errores transitorios de red o de la API de forma resiliente

        args:
            text: el texto a procesar

        returns:
            el texto refinado por el LLM

        raises:
            llmerror: si la comunicación con la API falla después de todos los reintentos
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
            logger.error(f"error procesando texto con GEMINI {e}")
            raise LLMError("falló el procesamiento de texto con GEMINI") from e
