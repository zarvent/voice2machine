"""
modulo que implementa el servicio de llm utilizando la api de google gemini.

esta es una implementacion concreta de la interfaz `llmservice`. es responsable
de toda la logica de comunicacion con el servicio de google gemini, incluyendo
la autenticacion, la construccion de la solicitud y el manejo de reintentos.
"""

from v2m.application.llm_service import LLMService
from v2m.config import config, BASE_DIR
from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from v2m.domain.errors import LLMError
from v2m.core.logging import logger

class GeminiLLMService(LLMService):
    """
    implementacion del `llmservice` que se conecta con google gemini.

    gestiona la configuracion del cliente de la api, la formulacion de las
    peticiones y la logica de reintentos para asegurar una comunicacion robusta.
    """
    def __init__(self) -> None:
        """
        inicializa el servicio de google gemini.

        este constructor realiza las siguientes acciones:
        1.  obtiene la configuracion y la api key desde `config.py` (pydantic settings).
        2.  configura e instancia el cliente de la api de google.
        3.  almacena los parametros del modelo y la configuracion de reintentos.

        raises:
            LLMError: si la `GEMINI_API_KEY` no se encuentra en la configuracion.
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
        procesa un texto utilizando el modelo de google gemini.

        implementa una estrategia de reintentos con `tenacity` para manejar
        errores transitorios de red o de la api de forma resiliente.

        args:
            text (str): el texto a procesar.

        returns:
            str: el texto refinado por el llm.

        raises:
            LLMError: si la comunicacion con la api falla despues de todos los reintentos.
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
