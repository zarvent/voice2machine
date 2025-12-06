# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
módulo que contiene los manejadores de comandos (command handlers)

los handlers son el corazón de la lógica de negocio de la aplicación
cada handler se suscribe a un tipo de comando específico y ejecuta las acciones
correspondientes cuando ese comando es despachado por el command bus

este enfoque inspirado en cqrs (command query responsibility segregation)
permite un bajo acoplamiento entre el punto de entrada de la aplicación (main.py)
y la lógica de negocio real
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Type
from v2m.core.cqrs.command import Command
from v2m.core.cqrs.command_handler import CommandHandler
from v2m.application.commands import StartRecordingCommand, StopRecordingCommand, ProcessTextCommand
from v2m.application.transcription_service import TranscriptionService
from v2m.application.llm_service import LLMService
from v2m.core.interfaces import NotificationInterface, ClipboardInterface
from v2m.config import config

# executor dedicado para operaciones de ml (single worker para evitar contención gpu)
# esto es más eficiente que el default threadpoolexecutor de asyncio.to_thread
_ml_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ml-inference")

class StartRecordingHandler(CommandHandler):
    """
    manejador para el comando `StartRecordingCommand`

    este handler interactúa con el servicio de transcripción para iniciar
    el proceso de grabación de audio también notifica al usuario que
    la grabación ha comenzado
    """
    def __init__(self, transcription_service: TranscriptionService, notification_service: NotificationInterface) -> None:
        """
        inicializa el handler con sus dependencias

        args:
            transcription_service: el servicio responsable de la grabación y transcripción
            notification_service: el servicio para enviar notificaciones al usuario
        """
        self.transcription_service = transcription_service
        self.notification_service = notification_service

    async def handle(self, command: StartRecordingCommand) -> None:
        """
        ejecuta la lógica para iniciar la grabación

        args:
            command: el comando que activa este handler
        """
        # start_recording es rápido pero por seguridad lo corremos en un hilo
        # para no bloquear el loop si sounddevice tarda un poco
        await asyncio.to_thread(self.transcription_service.start_recording)

        # crear bandera de grabación para que el script bash sepa que estamos grabando
        config.paths.recording_flag.touch()

        self.notification_service.notify("🎤 Voice2Machine", "Grabación iniciada...")

    def listen_to(self) -> Type[Command]:
        """
        se suscribe al tipo de comando `StartRecordingCommand`

        returns:
            el tipo de comando que este handler puede manejar
        """
        return StartRecordingCommand

class StopRecordingHandler(CommandHandler):
    """
    manejador para el comando `StopRecordingCommand`

    este handler detiene la grabación obtiene la transcripción del audio
    la copia al portapapeles y notifica al usuario del resultado
    """
    def __init__(self, transcription_service: TranscriptionService, notification_service: NotificationInterface, clipboard_service: ClipboardInterface) -> None:
        """
        inicializa el handler con sus dependencias

        args:
            transcription_service: el servicio responsable de la grabación y transcripción
            notification_service: el servicio para enviar notificaciones al usuario
            clipboard_service: el servicio para interactuar con el portapapeles
        """
        self.transcription_service = transcription_service
        self.notification_service = notification_service
        self.clipboard_service = clipboard_service

    async def handle(self, command: StopRecordingCommand) -> None:
        """
        ejecuta la lógica para detener la grabación y transcribir

        notifica al usuario durante el procesamiento y maneja el caso donde
        no se detecta voz en el audio

        args:
            command: el comando que activa este handler
        """
        # borrar bandera de grabación para que el script bash sepa que ya paramos
        if config.paths.recording_flag.exists():
            config.paths.recording_flag.unlink()

        self.notification_service.notify("⚡ V2M Processing", "Procesando...")

        # usar executor dedicado para ml - evita contención con otras tareas async
        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(
            _ml_executor,
            self.transcription_service.stop_and_transcribe
        )

        # si la transcripción está vacía no tiene sentido copiarla
        if not transcription.strip():
            self.notification_service.notify("❌ Whisper", "No se detectó voz en el audio")
            return

        self.clipboard_service.copy(transcription)
        preview = transcription[:80] # se muestra una vista previa para no saturar la notificación
        self.notification_service.notify(f"✅ Whisper - Copiado", f"{preview}...")

    def listen_to(self) -> Type[Command]:
        """
        se suscribe al tipo de comando `StopRecordingCommand`

        returns:
            el tipo de comando que este handler puede manejar
        """
        return StopRecordingCommand

class ProcessTextHandler(CommandHandler):
    """
    manejador para el comando `ProcessTextCommand`

    este handler utiliza un servicio de llm (large language model) para
    procesar y refinar un texto dado el resultado se copia al portapapeles
    """
    def __init__(self, llm_service: LLMService, notification_service: NotificationInterface, clipboard_service: ClipboardInterface) -> None:
        """
        inicializa el handler con sus dependencias

        args:
            llm_service: el servicio que interactúa con el llm (ej gemini)
            notification_service: el servicio para enviar notificaciones al usuario
            clipboard_service: el servicio para interactuar con el portapapeles
        """
        self.llm_service = llm_service
        self.notification_service = notification_service
        self.clipboard_service = clipboard_service

    async def handle(self, command: ProcessTextCommand) -> None:
        """
        ejecuta la lógica para procesar el texto con el llm

        args:
            command: el comando que contiene el texto a procesar
        """
        try:
            # asumimos que llm_service.process_text será async pronto
            # si no lo es asyncio.to_thread lo manejaría pero queremos async nativo
            # por ahora usaremos await si es corutina o to_thread si no
            if asyncio.iscoroutinefunction(self.llm_service.process_text):
                refined_text = await self.llm_service.process_text(command.text)
            else:
                refined_text = await asyncio.to_thread(self.llm_service.process_text, command.text)

            self.clipboard_service.copy(refined_text)
            self.notification_service.notify("✅ Gemini - Copiado", f"{refined_text[:80]}...")

        except Exception as e:
            # fallback si falla el llm copiamos el texto original
            self.notification_service.notify("⚠️ Gemini Falló", "Usando texto original...")
            self.clipboard_service.copy(command.text)
            self.notification_service.notify("✅ Whisper - Copiado (Raw)", f"{command.text[:80]}...")

    def listen_to(self) -> Type[Command]:
        """
        se suscribe al tipo de comando `ProcessTextCommand`

        returns:
            el tipo de comando que este handler puede manejar
        """
        return ProcessTextCommand
