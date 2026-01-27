# src-tauri

Backend de capture escrito en **Rust**.

Aquí vive la lógica de negocio: captura de audio, procesamiento VAD, transcripción Whisper, clipboard, y comunicación con el sistema operativo. Es el motor que hace que capture funcione.

---

## Por qué Rust

| Requisito | Solución en Rust |
| :-- | :-- |
| **Latencia predecible** | Sin garbage collector pausando en medio de grabación |
| **Control de memoria** | Ownership model previene leaks y race conditions |
| **Interop con C** | FFI directo con whisper.cpp, sin overhead |
| **Concurrencia segura** | `Send` + `Sync` garantizados en compile-time |

Para una aplicación de tiempo real donde cada milisegundo cuenta entre hablar y ver texto, Rust no es preferencia estética — es necesidad técnica.

---

## Estructura

### `assets/`

Recursos estáticos para Tauri.

| Contenido | Uso |
| :-- | :-- |
| Íconos | App icon, tray icons por estado |
| Sonidos | Audio cues (start, stop, success, error) |

Archivos que Tauri empaqueta en el binario final.

### `capabilities/`

Definiciones de **capabilities** de Tauri 2.0.

```json
{
  "permissions": [
    "core:default",
    "shell:allow-open",
    "global-shortcut:default",
    "notification:default"
  ]
}
```

**Seguridad por diseño:** La app solo puede hacer lo que se declara explícitamente aquí. Permisos declarativos, auditables, restrictivos por defecto.

### `gen/`

Archivos generados automáticamente por Tauri.

> ⚠️ **No editar manualmente.** Se regeneran en cada build.

### `src/`

Código fuente Rust de la aplicación.

Ver [`src/README.md`](src/README.md) para el detalle de cada módulo.

---

## Comandos IPC

El backend expone estos comandos al frontend vía Tauri:

| Comando | Descripción | Retorno |
| :-- | :-- | :-- |
| `toggle_recording` | Alterna grabación | `bool` (true=grabando) |
| `get_state` | Estado actual | `RecordingState` |
| `get_config` | Configuración actual | `AppConfig` |
| `set_config` | Actualiza configuración | `()` |
| `list_audio_devices` | Dispositivos disponibles | `Vec<AudioDeviceInfo>` |
| `is_model_downloaded` | ¿Modelo existe? | `bool` |
| `download_model` | Descarga modelo | `()` + eventos de progreso |
| `load_model` | Carga modelo en memoria | `()` |
| `is_model_loaded` | ¿Modelo en RAM? | `bool` |
