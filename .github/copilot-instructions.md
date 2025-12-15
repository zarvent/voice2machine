# voice2machine (v2m)

es una herramienta local de dictado por voz para todo el sistema en linux
captura audio del micrófono y lo transcribe localmente usando whisper (acelerado por gpu) e inyecta el texto en la ventana activa
también cuenta con un "interruptor de independencia" para operar sin conexión y una integración opcional con llm (gemini) para refinar el texto

## stack tecnológico

### backend (python)
- **runtime:** python 3.12+
- **librerías core:** `faster-whisper` (transcripción) `sounddevice` (audio) `silero-vad` (vad)
- **frameworks:** `pydantic` (configuración/validación) `google-genai` (llm)
- **testing:** `pytest` `pytest-asyncio` `pytest-mock`
- **linting/formatting:** `ruff` (configuración estricta) `mypy` (tipado estático estricto)

### frontend (tauri/react)
- **framework:** tauri 2.0 (backend en rust)
- **ui:** react 19 typescript vite
- **estilos:** css modules con variables css (estética minimalista limpia)
- **comunicación:** ipc vía comandos tauri y sockets unix

### infraestructura
- **ipc:** sockets unix con framing personalizado (header de longitud de 4 bytes big-endian)
- **shell:** scripts bash para gestión de procesos y atajos globales

## guías de código

### general
- **licencia:** todos los archivos fuente deben incluir el header de licencia gplv3 estándar en inglés
- **idioma:** toda la documentación comentarios y textos visibles al usuario (logs notificaciones gui) deben estar en **español latinoamericano "humanizado"** (estrictamente minúsculas sin puntos ni comas paréntesis permitidos)
  - *excepción:* el header de la licencia gpl debe permanecer en inglés
- **arquitectura:** seguir domain-driven design (ddd) con capas: `core` `domain` `application` `infrastructure`
- **prioridad:** legibilidad (prosa técnica) > mantenibilidad > rendimiento

### python
- **tipado:** se requieren type hints estrictos para todas las funciones y métodos
- **documentación:** docstrings detallados y comentarios del "por qué" son obligatorios
- **manejo de errores:** usar excepciones personalizadas del dominio

### frontend
- **accesibilidad:** asegurar roles aria (ej `role="alert"` para errores) etiquetas para botones de solo ícono y navegación por teclado (escape para cerrar modales)
- **rendimiento:** usar `react.memo` `usecallback` y `usememo` para evitar re-renderizados innecesarios

## estructura del proyecto

- `apps/backend/`
  - `src/v2m/`: paquete principal de python (lógica core)
  - `config.toml`: archivo de configuración central
  - `tests/`: suite de pytest
- `apps/frontend/`
  - `src/`: código fuente de react
  - `src-tauri/`: backend de rust para tauri
- `scripts/`: scripts de shell para despliegue pruebas y runtime (ej `v2m-toggle.sh` `v2m-daemon.sh`)
- `docs/`: documentación técnica (mkdocs)
- `.Jules/`: memoria del proyecto y logs de desarrollo

## recursos

- **scripts:**
  - `scripts/v2m-daemon.sh`: gestiona el proceso demonio del backend
  - `scripts/v2m-toggle.sh`: alterna grabación (atajo global)
  - `scripts/v2m-process.sh`: procesa texto (atajo global)
  - `scripts/test_whisper_gpu.py`: verifica aceleración por gpu
- **configuración:**
  - `apps/backend/config.toml`: ajustes de usuario
  - `.env`: secretos (api keys)
