
# voice2machine

Herramientas de transcripción de voz a texto.

**Local-first.** Tus datos no salen de tu equipo por defecto. Rápido, privado, sin suscripciones.

---

## Por qué existe

Los servicios de transcripción en la nube son lentos, costosos y comprometen tu privacidad. Cada palabra que dictas viaja a servidores externos, se almacena, se procesa. voice2machine nace de una premisa simple: **deberías poder elegir**.

**Local-first, no local-only.** Priorizamos el procesamiento local porque es más rápido, más privado y no depende de conexión. Pero no estamos en contra de la nube — en futuras versiones podrás alternar entre procesamiento local y APIs externas vía tu propia API key, según tus necesidades.

---

## Para qué sirve

Para convertir tu voz en texto de forma instantánea:

- Sin latencia de red cuando usas procesamiento local
- Sin límites de uso ni costos recurrentes
- Con la opción futura de usar servicios cloud cuando lo prefieras

---

## Estructura del monorepo

### `apps/`

Aplicaciones productivas del ecosistema voice2machine.

| App | Descripción |
| :-- | :-- |
| **[capture](apps/capture/)** | Utilidad de voz a texto en tiempo real. Presiona `Ctrl+Shift+Space` → habla → el texto se copia a tu clipboard. |

---

## Filosofía técnica

### Principios

| Principio | Implementación |
| :-- | :-- |
| **Privacidad por defecto** | Procesamiento 100% local, sin telemetría, sin conexiones externas |
| **Rendimiento nativo** | Rust para el backend, modelos optimizados para CPU y GPU |
| **Simplicidad radical** | Una herramienta, un propósito, bien ejecutado |
| **Flexibilidad consciente** | Local-first, con opción de cloud vía API key en el futuro |

### Stack técnico

```
Frontend:  React + TypeScript + Tauri 2.0
Backend:   Rust + whisper.cpp + Silero VAD
Audio:     cpal (captura) + rubato (resampling)
Output:    arboard (clipboard)
```
