"""
módulo que define la interfaz para los servicios de transcripción de audio

esta clase abstracta establece el contrato que cualquier servicio de transcripción
debe seguir la capa de aplicación interactúa con esta interfaz permitiendo
que la implementación subyacente (ej `whispertranscriptionservice`) pueda ser
intercambiada sin afectar la lógica de negocio
"""

from abc import ABC, abstractmethod

class TranscriptionService(ABC):
    """
    clase base abstracta para los servicios de transcripción

    define las operaciones esenciales para la grabación y transcripción de audio
    """

    @abstractmethod
    def start_recording(self) -> None:
        """
        inicia el proceso de grabación de audio desde el dispositivo de entrada
        """
        raise NotImplementedError

    @abstractd
    def stop_and_transcribe(self) -> str:
        """
        detiene la grabación actual y procesa el audio para obtener una transcripción

        returns:
            el texto transcrito del audio grabado
        """
        raise NotImplementedError
