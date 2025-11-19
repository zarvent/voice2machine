"""
módulo que define la interfaz para los servicios de modelos de lenguaje grandes (LLM)

esta clase abstracta define el contrato que cualquier servicio de LLM debe
cumplir para ser utilizado por la aplicación la capa de aplicación depende de
esta abstracción no de una implementación concreta (como `geminillmservice`)
"""

from abc import ABC, abstractmethod

class LLMService(ABC):
    """
    clase base abstracta para los servicios de modelos de lenguaje

    define las operaciones que se pueden realizar con un LLM como procesar texto
    """

    @abstractmethod
    async def process_text(self, text: str) -> str:
        """
        procesa y refina un bloque de texto utilizando el LLM

        args:
            text: el texto de entrada a procesar

        returns:
            el texto procesado y refinado por el LLM
        """
        raise NotImplementedError
