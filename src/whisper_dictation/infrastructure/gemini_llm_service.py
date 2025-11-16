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
    def __init__(self) -> None:
        # Cargar variables de entorno
        env_path = Path(__file__).parent.parent.parent.parent / '.env'
        if not env_path.exists():
            env_path.touch()
        load_dotenv(env_path)

        gemini_config = config['gemini']
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise LLMError("GEMINI_API_KEY not found in environment variables.")

        os.environ["GOOGLE_API_KEY"] = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = gemini_config['model']
        self.temperature = gemini_config['temperature']
        self.max_tokens = gemini_config['max_tokens']
        self.retry_attempts = gemini_config['retry_attempts']
        self.retry_min_wait = gemini_config['retry_min_wait']
        self.retry_max_wait = gemini_config['retry_max_wait']

    @retry(
        stop=stop_after_attempt(config['gemini']['retry_attempts']),
        wait=wait_exponential(
            multiplier=1,
            min=config['gemini']['retry_min_wait'],
            max=config['gemini']['retry_max_wait'],
        ),
    )
    def process_text(self, text: str) -> str:
        try:
            logger.info("Processing text with Gemini...")
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }

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
            logger.info("Gemini processing complete.")
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error processing text with Gemini: {e}")
            raise LLMError("Failed to process text with Gemini.") from e
