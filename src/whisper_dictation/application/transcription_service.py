"""
Módulo que define la interfaz para los servicios de transcripción de audio.

Esta clase abstracta establece el contrato que cualquier servicio de transcripción
debe seguir. La capa de aplicación interactúa con esta interfaz, permitiendo
que la implementación subyacente (ej. `WhisperTranscriptionService`) pueda ser
intercambiada sin afectar la lógica de negocio.
"""

from abc import ABC, abstractmethod

class TranscriptionService(ABC):
    """
    Clase base abstracta para los servicios de transcripción.

    Define las operaciones esenciales para la grabación y transcripción de audio.
    """

    @abstractmethod
    def start_recording(self) -> None:
        """
        Inicia el proceso de grabación de audio desde el dispositivo de entrada.
        """
        raise NotImplementedError

    @abstractmethod
    def stop_and_transcribe(self) -> str:
        """
        Detiene la grabación actual y procesa el audio para obtener una transcripción.

        Returns:
            El texto transcrito del audio grabado.
        """
        raise NotImplementedError
