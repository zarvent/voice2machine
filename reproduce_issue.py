
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Load environment variables
load_dotenv()

from v2m.infrastructure.gemini_llm_service import GeminiLLMService
from v2m.domain.errors import LLMError

async def main():
    print("Initializing GeminiLLMService...")
    try:
        service = GeminiLLMService()
        print("Service initialized.")
    except Exception as e:
        print(f"Failed to initialize service: {e}")
        return

    text = "hola esto es una prueba de transcripcion sin puntuacion"
    print(f"Processing text: '{text}'")

    try:
        result = await service.process_text(text)
        print(f"Result: '{result}'")
    except LLMError as e:
        print(f"LLMError: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
