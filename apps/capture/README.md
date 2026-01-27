# capture

Utilidad local de voz a texto. Presiona un atajo → habla → el texto se copia a tu clipboard.

Diseñada para **velocidad**, **privacidad** y **simplicidad**. Corre completamente en tu hardware.

---

## Por qué existe

Porque dictar debería ser instantáneo.

Sin esperar respuestas de servidores. Sin pagar subscripciones. Sin que tus palabras pasen por infraestructura ajena.

capture existe para que tu voz se convierta en texto en milisegundos, no segundos. Para que puedas hablar libremente sabiendo que nadie más escucha — a menos que tú elijas lo contrario.

> **Nota:** En futuras versiones, capture soportará providers cloud opcionales vía API key para quienes prefieran ese modelo. Local-first, no local-only.

---

## Cómo funciona

```
┌──────────────────────────────────────────────────────────────────┐
│                         FLUJO DE CAPTURE                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   1. ATAJO GLOBAL                                                │
│      └── Ctrl+Shift+Space activa la grabación                   │
│                                                                   │
│   2. CAPTURA DE AUDIO                                            │
│      └── El micrófono graba mientras hablas                     │
│                                                                   │
│   3. DETECCIÓN DE VOZ (VAD)                                      │
│      └── Silero VAD filtra silencios en tiempo real             │
│      └── State machine con debouncing evita falsos positivos    │
│                                                                   │
│   4. TRANSCRIPCIÓN LOCAL                                         │
│      └── whisper.cpp procesa el audio en CPU/GPU                │
│      └── Modelo: large-v3-turbo (optimizado para velocidad)     │
│                                                                   │
│   5. CLIPBOARD                                                   │
│      └── Texto transcrito copiado automáticamente               │
│      └── Listo para pegar donde quieras                         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Estructura del proyecto

### `docs/`

Documentación del proyecto: decisiones de arquitectura, guías, y contexto histórico.

| Contenido | Propósito |
| :-- | :-- |
| **ADRs** | Architecture Decision Records — el *por qué* de las decisiones técnicas |

### `src/`

Frontend de la aplicación.

| Tecnología | Propósito |
| :-- | :-- |
| **React** | Componentes de UI, feedback visual |
| **TypeScript** | Tipado estático, contratos con el backend |
| **Tauri IPC** | Comunicación bidireccional con el backend Rust |

Maneja la interfaz de usuario, configuración, y visualización del estado de grabación.

### `src-tauri/`

Backend de la aplicación.

| Tecnología | Propósito |
| :-- | :-- |
| **Rust** | Rendimiento predecible, sin GC |
| **Tauri 2.0** | Framework de desktop apps |
| **whisper.cpp** | Motor de transcripción |

Contiene toda la lógica de captura de audio, VAD, transcripción, y clipboard. Es el corazón de capture.

---

## Uso básico

### Prerrequisitos

1. **Modelo Whisper descargado** — la app te guía en la primera ejecución
2. **Micrófono configurado** — cualquier mic del sistema funciona

### Atajos

| Atajo | Acción |
| :-- | :-- |
| `Ctrl+Shift+Space` | Toggle grabación (presiona para iniciar, presiona de nuevo para cancelar) |

### Estados

| Estado | Indicador | Descripción |
| :-- | :-- | :-- |
| **Idle** | 🔵 | Esperando. Listo para grabar. |
| **Recording** | 🔴 | Grabando. Hablando o esperando voz. |
| **Processing** | 🟡 | Transcribiendo. Audio enviado a Whisper. |
