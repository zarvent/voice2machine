"""
modulo que define la interfaz para los servicios de transcripcion de audio.

esta clase abstracta establece el contrato que cualquier servicio de transcripcion
debe seguir. la capa de aplicacion interactua con esta interfaz permitiendo
que la implementacion subyacente (ej `whispertranscriptionservice`) pueda ser
intercambiada sin afectar la logica de negocio.
"""

from abc import ABC, abstractmethod

class TranscriptionService(ABC):
    """
    clase base abstracta para los servicios de transcripcion.

    define las operaciones esenciales para la grabacion y transcripcion de audio.
    """

    @abstractmethod
    def start_recording(self) -> None:
        """
        inicia el proceso de grabacion de audio desde el dispositivo de entrada.
        """
        raise NotImplementedError

    @abstractmethod
    def stop_and_transcribe(self) -> str:
        """
        detiene la grabacion actual y procesa el audio para obtener una transcripcion.

        returns:
            str: el texto transcrito del audio grabado.
        """
        raise NotImplementedError
