# infrastructure

esta capa contiene las implementaciones concretas de las interfaces definidas en `core` y `application` aquí es donde la aplicación interactúa con el mundo exterior (hardware apis sistema operativo)

contenido
- `audio/` manejo de grabación de audio y dispositivos
- `gemini_llm_service.py` implementación del servicio llm usando google gemini
- `linux_adapters.py` adaptadores para interactuar con el escritorio linux (notificaciones portapapeles)
- `vad_service.py` servicio de detección de actividad de voz usando silero vad
- `whisper_transcription_service.py` implementación de transcripción usando faster-whisper

filosofía
este es el único lugar donde se permite importar librerías de terceros pesadas o específicas de plataforma (ej `sounddevice` `google-generativeai` `faster_whisper`)
