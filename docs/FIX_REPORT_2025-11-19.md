# FIX REPORT - 2025-11-19

## 1. CLIPBOARD FIX (SOLUCIONADO)

**Problema**: El portapapeles no funcionaba desde el daemon (timeout o fallo silencioso).
**Causa**: `pyperclip` y `xclip` tienen problemas con variables de entorno y manejo de procesos en background cuando se ejecutan como daemon.
**Solución**:
- Reemplazo de `pyperclip` por implementación nativa con `subprocess`.
- Manejo explícito de `xclip` en background (sin esperar a que termine).
- Detección automática de backend (X11/Wayland).

## 2. TRANSCRIPCIÓN "CONGELADA" (SOLUCIONADO)

**Problema**: La transcripción se quedaba procesando indefinidamente o fallaba silenciosamente.
**Causa**:
1. **Conflicto de versiones**: `torch` requería cuDNN 9.10 pero se instaló 9.16, causando conflictos binarios (Segfaults silenciosos).
2. **LD_LIBRARY_PATH**: El daemon no tenía acceso a las librerías dinámicas de NVIDIA en el entorno virtual.

**Solución**:
- **Alineación de versiones**: Se forzó la instalación de `nvidia-cudnn-cu12==9.10.2.21` y `nvidia-cublas-cu12==12.8.4.1`.
- **Script de arranque robusto**: `scripts/v2m-daemon.sh` ahora configura `LD_LIBRARY_PATH` automáticamente antes de iniciar el daemon.
- **Fallback a CPU**: Se implementó lógica en `WhisperTranscriptionService` para cambiar automáticamente a CPU si CUDA falla, evitando que el servicio quede inoperable.

## ESTADO ACTUAL

- **Daemon**: Corriendo (PID: 10227)
- **Modelo**: Cargado en **CUDA** (GPU acelerada)
- **Clipboard**: Funcional (X11 backend)

## INSTRUCCIONES DE USO

Para gestionar el servicio, usar el nuevo script unificado:

```bash
./scripts/v2m-daemon.sh start    # Iniciar
./scripts/v2m-daemon.sh stop     # Detener
./scripts/v2m-daemon.sh restart  # Reiniciar
./scripts/v2m-daemon.sh status   # Ver estado y test de conectividad
./scripts/v2m-daemon.sh logs     # Ver logs en tiempo real
```
