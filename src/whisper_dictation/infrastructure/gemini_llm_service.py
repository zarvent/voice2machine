"""
Módulo que implementa el servicio de LLM utilizando la API de GOOGLE GEMINI.

Esta es una implementación concreta de la interfaz `LLMService`. Es responsable
de toda la lógica de comunicación con el servicio de GOOGLE GEMINI incluyendo
la autenticación la construcción de la solicitud y el manejo de reintentos.
"""

from whisper_dictation.application.llm_service import LLMService
from whisper_dictation.config import config
from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from whisper_dictation.domain.errors import LLMError
from whisper_dictation.core.logging import logger

class GeminiLLMService(LLMService):
    """
    Implementación del `LLMService` que se conecta con GOOGLE GEMINI.

    Gestiona la configuración del cliente de la API la formulación de las
    peticiones y la lógica de reintentos para asegurar una comunicación robusta.
    """
    def __init__(self) -> None:
        """
        Inicializa el servicio de GOOGLE GEMINI.

        Este constructor realiza las siguientes acciones:
        1.  Carga las variables de entorno desde el archivo `.env`.
        2.  Lee la configuración específica de GEMINI desde `config.toml`.
        3.  Obtiene la `GEMINI_API_KEY` de las variables de entorno.
        4.  Configura e instancia el cliente de la API de GOOGLE.
        5.  Almacena los parámetros del modelo y la configuración de reintentos.

        Raises:
            LLMError: Si la `GEMINI_API_KEY` no se encuentra en las variables de entorno.
        """
        # --- Carga de configuración y secretos ---
        env_path = Path(__file__).parent.parent.parent.parent / '.env'
        if not env_path.exists():
            # se crea si no existe para evitar errores en `load_dotenv`
            env_path.touch()
        load_dotenv(env_path)

        gemini_config = config['gemini']
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise LLMError("la variable de entorno GEMINI_API_KEY no fue encontrada")

        # --- inicialización del cliente de la api ---
        # la librería de google utiliza `GOOGLE_API_KEY` por defecto
        os.environ["GOOGLE_API_KEY"] = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = gemini_config['model']
        self.temperature = gemini_config['temperature']
        self.max_tokens = gemini_config['max_tokens']

    @retry(
        stop=stop_after_attempt(config['gemini']['retry_attempts']),
        wait=wait_exponential(
            multiplier=1,
            min=config['gemini']['retry_min_wait'],
            max=config['gemini']['retry_max_wait'],
        ),
    )
    def process_text(self, text: str) -> str:
        """
        Procesa un texto utilizando el modelo de GOOGLE GEMINI.

        Implementa una estrategia de reintentos con `tenacity` para manejar
        errores transitorios de red o de la API de forma resiliente.

        Args:
            text: El texto a procesar.

        Returns:
            El texto refinado por el LLM.

        Raises:
            LLMError: Si la comunicación con la API falla después de todos los reintentos.
        """
        try:
            logger.info("procesando texto con GEMINI...")
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }

            # --- construcción del payload para la api ---
            contents = [
                genai.types.Content(
                    role="user",
                    parts=[genai.types.Part(text=text)]
                )
            ]

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generation_config
            )
            logger.info("procesamiento con GEMINI completado")
            return response.text.strip()
        except Exception as e:
            # --- manejo de errores ---
            # se captura cualquier excepción de la librería de google o de red
            # y se relanza como un error de dominio para no filtrar detalles
            # de la infraestructura a la capa de aplicación
            logger.error(f"error procesando texto con GEMINI {e}")
            raise LLMError("falló el procesamiento de texto con GEMINI") from e
