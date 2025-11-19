"""
Módulo que define la interfaz para los servicios de Modelos de Lenguaje Grandes (LLM).

Esta clase abstracta define el contrato que cualquier servicio de LLM debe
cumplir para ser utilizado por la aplicación. La capa de aplicación depende de
esta abstracción, no de una implementación concreta (como `GeminiLLMService`).
"""

from abc import ABC, abstractmethod

class LLMService(ABC):
    """
    Clase base abstracta para los servicios de modelos de lenguaje.

    Define las operaciones que se pueden realizar con un LLM, como procesar texto.
    """

    @abstractmethod
    async def process_text(self, text: str) -> str:
        """
        Procesa y refina un bloque de texto utilizando el LLM.

        Args:
            text: El texto de entrada a procesar.

        Returns:
            El texto procesado y refinado por el LLM.
        """
        raise NotImplementedError
