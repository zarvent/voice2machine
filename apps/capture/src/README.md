# src

Frontend de capture construido con **React** y **TypeScript**.

Es la capa de presentación: lo que el usuario ve e interactúa. Se comunica con el backend Rust exclusivamente a través de **Tauri IPC commands**.

---

## Por qué está separado

La separación frontend/backend no es arbitraria:

| Capa | Cambia... | Prioriza... |
| :-- | :-- | :-- |
| **Frontend** | Rápido (UI, preferencias, feedback) | Experiencia de usuario |
| **Backend** | Lento (audio, transcripción, OS) | Rendimiento y estabilidad |

Esta división permite:

- Iterar en la interfaz sin tocar código Rust
- Optimizar el backend sin romper la experiencia visual
- Testing aislado de cada capa

---

## Estructura

### `components/`

Componentes React reutilizables de la aplicación.

```
components/
├── RecordingIndicator.tsx   # Feedback visual del estado
├── SettingsPanel.tsx        # Configuración de usuario
└── ...
```

**Filosofía:** Cada componente es autónomo — lógica, estilos y tipos viven juntos. Diseñados para composición, no herencia.

### `hooks/`

Hooks personalizados que encapsulan lógica reutilizable.

| Hook | Propósito |
| :-- | :-- |
| `useRecording` | Estado de grabación, toggle |
| `useConfig` | Configuración persistida |
| `useTauriEvents` | Listeners de eventos del backend |

**Filosofía:** Abstraen la comunicación con Tauri y el manejo de estado. Mantienen los componentes limpios de lógica compleja.

### `lib/`

Funciones y utilidades generales.

```
lib/
├── tauri-commands.ts   # Wrappers tipados de IPC commands
└── utils.ts            # Helpers puros
```

**Filosofía:** Si algo se usa en más de un lugar y no es hook ni componente, vive aquí.

### `types/`

Definiciones de tipos TypeScript compartidas.

```
types/
├── config.ts           # AppConfig, VadConfig
├── state.ts            # RecordingState
└── events.ts           # PipelineEvent payloads
```

**Filosofía:** Contrato tipado entre frontend y backend. Estos tipos deben reflejar exactamente los structs de Rust.
