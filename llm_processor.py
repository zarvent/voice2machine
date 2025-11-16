#!/usr/bin/env python3
"""
Procesador de texto usando Google Gemini API
Optimizado para refinamiento de prompts con capacidades avanzadas de IA
"""

import sys
import os
import logging
import re
from pathlib import Path
from typing import Optional

from google import genai
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# Configurar logging
# Esto creará el directorio 'logs' si no existe.
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'llm.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
# Esto creará el archivo .env si no existe
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    env_path.touch()
load_dotenv(env_path)

# Configuración
class Config:
    """Pequeña agrupación de parámetros de LLM."""

    MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
    TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    MAX_INPUT_CHARS = int(os.getenv("LLM_MAX_INPUT_CHARS", "6000"))
    REQUEST_TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    RETRY_ATTEMPTS = int(os.getenv("LLM_RETRY_ATTEMPTS", "3"))
    RETRY_MIN_WAIT = int(os.getenv("LLM_RETRY_MIN_WAIT", "2"))
    RETRY_MAX_WAIT = int(os.getenv("LLM_RETRY_MAX_WAIT", "10"))


API_KEY = os.getenv("GEMINI_API_KEY")

def load_system_prompt() -> str:
    """Carga el prompt del sistema desde la carpeta ./prompts."""

    prompts_dir = Path(__file__).parent / 'prompts'
    prompt_path = prompts_dir / 'refine_system.txt'

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            data = f.read().strip()
    except FileNotFoundError:
        logger.error("No se encontró el archivo de prompt en %s", prompt_path)
        sys.exit(1)

    if not data:
        logger.error("El archivo de prompt está vacío: %s", prompt_path)
        sys.exit(1)

    return data


SYSTEM_PROMPT = load_system_prompt()


def sanitize_text(text: str) -> str:
    """Normaliza el texto recibido desde la CLI o stdin."""

    if text is None:
        return ""

    cleaned = text.replace('\r\n', '\n').strip()
    # Compactar múltiples líneas en bloques legibles conservando saltos importantes
    cleaned = '\n'.join(line.rstrip() for line in cleaned.split('\n'))
    return cleaned


def read_input_text() -> str:
    """Obtiene el texto desde stdin o argumentos, priorizando stdin."""

    stdin_payload: Optional[str] = None
    if not sys.stdin.isatty():
        stdin_payload = sys.stdin.read()
        if stdin_payload:
            stdin_payload = stdin_payload.strip()

    if stdin_payload:
        return sanitize_text(stdin_payload)

    if len(sys.argv) >= 2:
        # Unir todos los argumentos para preservar espacios y comillas
        return sanitize_text(' '.join(sys.argv[1:]))

    return ""


def validate_length(text: str) -> str:
    """Valida longitud mínima y máxima del texto recibido."""

    if not text:
        raise ValueError("El texto de entrada está vacío")

    if len(text) > Config.MAX_INPUT_CHARS:
        logger.warning(
            "Texto de entrada (%s chars) excede el máximo recomendado (%s). Se truncará.",
            len(text),
            Config.MAX_INPUT_CHARS,
        )
        return text[:Config.MAX_INPUT_CHARS]

    return text


THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_-]+)?")


def strip_model_artifacts(text: str) -> str:
    """Elimina bloques de razonamiento o markdown no deseado."""

    if not text:
        return ""

    cleaned = THINK_BLOCK_RE.sub("", text)
    cleaned = FENCE_RE.sub("", cleaned)

    drop_prefixes = ("analysis:", "reasoning:", "thought:")
    filtered_lines = []
    for line in cleaned.splitlines():
        normalized = line.strip().lower()
        if any(normalized.startswith(prefix) for prefix in drop_prefixes):
            continue
        filtered_lines.append(line)

    cleaned = '\n'.join(filtered_lines)
    cleaned = cleaned.replace('<think>', '').replace('</think>', '')
    return cleaned.strip()


class GeminiProcessor:
    """Procesador usando Google Gemini API"""

    def __init__(self):
        self.api_key = API_KEY
        if not self.api_key:
            raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")

        # Configurar el cliente de Gemini
        os.environ["GOOGLE_API_KEY"] = self.api_key
        self.client = genai.Client(api_key=self.api_key)

        self.model = Config.MODEL
        self.temperature = Config.TEMPERATURE
        logger.info(
            "Inicializado Gemini | modelo=%s | temperatura=%s",
            self.model,
            self.temperature,
        )

    @retry(
        stop=stop_after_attempt(Config.RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=1,
            min=Config.RETRY_MIN_WAIT,
            max=Config.RETRY_MAX_WAIT,
        ),
    )
    def refine(self, text: str) -> str:
        cleaned_text = validate_length(sanitize_text(text))
        logger.info(
            "Procesando %s caracteres con Gemini",
            len(cleaned_text),
        )

        # Preparar la configuración de generación
        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": Config.MAX_TOKENS,
        }

        # Crear el contenido con el sistema y usuario
        contents = [
            genai.types.Content(
                role="user",
                parts=[genai.types.Part(text=f"{SYSTEM_PROMPT}\n\n{cleaned_text}")]
            )
        ]

        # Generar contenido
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=generation_config
        )

        result = response.text.strip()
        result = strip_model_artifacts(result)

        logger.info(f"Resultado: {len(result)} caracteres")
        return result


def main():
    input_text = read_input_text()
    if not input_text:
        logger.error("No se proporcionó texto de entrada. Puedes pasar texto como argumento o por stdin.")
        sys.exit(1)

    try:
        processor = GeminiProcessor()
        refined_text = processor.refine(input_text)

        # Imprimir solo el resultado a stdout
        print(refined_text, end='')

    except Exception as e:
        logger.exception(f"Error procesando texto: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
