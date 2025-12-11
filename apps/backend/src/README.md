# SRC

código fuente principal de voice2machine.

---

## ¿qué es?

el paquete python `v2m` que contiene toda la lógica de la aplicación. desde transcripción de audio hasta integración con el sistema operativo.

---

## ¿para qué sirve?

implementa el corazón funcional del sistema:

- **transcripción**: carga whisper, procesa audio, genera texto
- **refinamiento**: envía texto a LLMs (local o cloud) y recibe mejoras
- **daemon**: proceso persistente que mantiene modelos en memoria
- **IPC**: comunicación entre script de atajo de teclado y daemon
- **sistema**: integración con clipboard, notificaciones, audio del OS

---

## ¿por qué existe?

voice2machine empezó como scripts bash simples. creció a una aplicación compleja con:

- múltiples backends de transcripción (whisper, futuro: vosk)
- múltiples proveedores de LLM (gemini, perplexity, local)
- gestión de estado persistente (daemon)
- arquitectura testeable y mantenible

el directorio `src/` centraliza todo este código en un paquete python profesional.

---

## arquitectura

sigue **arquitectura hexagonal** (ports and adapters) para separar:

```
src/v2m/
├── application/     # casos de uso (orquestación)
├── core/            # núcleo del framework (CQRS, DI)
├── domain/          # entidades y reglas de negocio
└── infrastructure/  # adaptadores a tecnología concreta
```

### capas explicadas

**application/** - la lógica de "qué hace" el sistema
- `transcription_service.py` - orquesta la grabación y transcripción
- `llm_service.py` - gestiona refinamiento de texto con LLMs
- `commands.py` - comandos que el usuario puede ejecutar
- `command_handlers.py` - implementación de cada comando

**core/** - el motor reutilizable
- `cqrs/` - patrón command bus para desacoplar ejecución
- `di/` - inyección de dependencias (container)
- `interfaces.py` - contratos que deben cumplir los adaptadores
- `ipc_protocol.py` - protocolo de comunicación cliente-daemon

**domain/** - modelos de negocio puros (sin dependencias externas)
- entidades del dominio
- excepciones personalizadas
- lógica de negocio core

**infrastructure/** - implementaciones concretas
- `audio/` - grabación con sounddevice
- `linux_adapters.py` - clipboard, notificaciones vía dbus
- `notification_service.py` - envío de alertas al usuario
- `system_monitor.py` - monitoreo de recursos

---

## punto de entrada

### `main.py`

CLI unificado que puede actuar como:

1. **daemon** - proceso persistente en background
   ```bash
   python -m v2m.main --daemon
   ```

2. **cliente** - envía comandos al daemon
   ```bash
   python -m v2m.main START_RECORDING
   python -m v2m.main STOP_RECORDING
   python -m v2m.main PROCESS_TEXT "mi texto"
   ```

el daemon escucha en un socket unix (`/tmp/v2m.sock`) y responde a comandos.

---

## flujo de ejecución típico

### transcripción (voz → texto)

1. usuario presiona atajo de teclado
2. script bash ejecuta `v2m.main START_RECORDING`
3. daemon recibe comando vía IPC
4. `audio_recording_worker` captura audio
5. usuario suelta tecla → script envía `STOP_RECORDING`
6. daemon pasa audio a `transcription_service`
7. whisper transcribe → texto va a clipboard
8. notificación informa al usuario

### refinamiento (texto → texto mejorado)

1. usuario copia texto y presiona otro atajo
2. script ejecuta `v2m.main PROCESS_TEXT "$(xclip -o)"`
3. daemon recibe texto vía IPC
4. `llm_service` envía a modelo (local o API)
5. respuesta refinada reemplaza clipboard
6. notificación muestra resultado

---

## patrones de diseño usados

- **hexagonal architecture** - independencia de frameworks
- **CQRS** - separación comando/query (command bus)
- **dependency injection** - container gestiona instancias
- **repository pattern** - abstracción de persistencia (futuro)
- **strategy pattern** - múltiples implementaciones de transcripción/LLM

---

## testing

```bash
pytest tests/
```

los tests están en `../tests/` (nivel backend, no dentro de src).

estructura:
```
tests/
├── unit/           # pruebas de componentes aislados
├── integration/    # pruebas de integración entre capas
└── fixtures/       # datos de prueba
```

---

## configuración

la carga de config está en `config.py` usando pydantic-settings. lee de:

1. `config.toml` - configuración principal
2. variables de entorno - sobreescriben toml
3. valores por defecto - fallback

---

## dependencias principales

ver `../pyproject.toml` para lista completa:

- **faster-whisper** - transcripción con GPU
- **sounddevice** - captura de audio
- **google-genai** - cliente de gemini
- **pydantic** - validación de datos
- **typer** - CLI framework

---

## cómo extender

### añadir un nuevo proveedor de LLM

1. implementa la interfaz `LLMProvider` en `core/interfaces.py`
2. crea adaptador en `infrastructure/`
3. registra en `core/providers/provider_registry.py`
4. actualiza config para seleccionarlo

### añadir un nuevo backend de transcripción

1. implementa interfaz `TranscriptionService`
2. añade en `application/`
3. configura en `config.toml` bajo `[transcription]`

---

## documentación detallada

consulta `v2m/README.md` para más detalles sobre la arquitectura interna del paquete.

---

## referencias

- [hexagonal architecture](https://alistair.cockburn.us/hexagonal-architecture/) - ports and adapters
- [CQRS pattern](https://martinfowler.com/bliki/CQRS.html) - command query separation
- [dependency injection in python](https://python-dependency-injector.ets-labs.org/) - DI patterns
