# LOGS

registro de actividad del sistema voice2machine.

---

## ¿qué es?

directorio donde se almacenan los archivos de log generados automáticamente durante la ejecución de la aplicación.

---

## ¿para qué sirve?

los logs permiten:

- **diagnosticar problemas**: ver por qué falló una transcripción o llamada a LLM
- **auditar uso**: cuántas veces se usó el sistema, cuánto procesamiento se hizo
- **monitorear rendimiento**: tiempos de respuesta, uso de recursos
- **debugging**: entender el flujo de ejecución cuando algo no funciona

---

## ¿por qué existe?

en un daemon persistente que corre en background, no puedes simplemente hacer `print()` para ver qué pasa. los logs son la ventana hacia el estado interno del sistema.

además, como voice2machine se integra con atajos de teclado globales, necesitas ver qué sucedió DESPUÉS de presionar el atajo (cuando la terminal ya no está visible).

---

## archivos generados

### `llm.log`

registra todas las interacciones con modelos de lenguaje.

**contenido típico:**
```
2025-11-15 17:24:18,974 - INFO - Inicializado Perplexity con modelo sonar-pro
2025-11-15 17:24:18,974 - INFO - Procesando 52 caracteres con Perplexity
2025-11-15 17:24:27,549 - INFO - Resultado: 2240 caracteres
```

**qué muestra:**
- modelo usado (local/cloud)
- tamaño de entrada en caracteres
- tamaño de salida
- errores si hubo problemas de conexión o timeout

---

### `process.log`

eventos generales del daemon y comandos ejecutados.

**contenido típico:**
```
[2025-11-15 17:24:18] Texto original (52 caracteres)
[2025-11-15 17:24:27] Procesamiento exitoso (2451 caracteres)
[2025-11-15 18:03:27] Texto original (117 caracteres)
```

**qué muestra:**
- inicio/detención del daemon
- comandos recibidos vía IPC (`START_RECORDING`, `STOP_RECORDING`, `PROCESS_TEXT`)
- errores de sistema (audio, clipboard, notificaciones)
- resumen de operaciones completadas

---

## ubicación y persistencia

estos archivos se generan en tiempo de ejecución y están excluidos de git (`.gitignore`):

```gitignore
logs/*.log
```

**no se versionan** porque:
- contienen datos de uso personal
- crecen constantemente
- son específicos de cada máquina

---

## rotación de logs

actualmente los logs crecen indefinidamente. si ocupan mucho espacio, puedes:

1. **borrarlos manualmente**:
   ```bash
   rm apps/backend/logs/*.log
   ```

2. **implementar rotación** (futuro): usar `logging.handlers.RotatingFileHandler` para limitar tamaño.

---

## cómo usar los logs

### ver en tiempo real

```bash
tail -f apps/backend/logs/llm.log
tail -f apps/backend/logs/process.log
```

### buscar errores

```bash
grep -i "error" apps/backend/logs/*.log
grep -i "failed" apps/backend/logs/*.log
```

### filtrar por fecha

```bash
grep "2025-11-15" apps/backend/logs/llm.log
```

---

## configuración

el nivel de logging se configura en el código (`src/v2m/core/logging.py`). por defecto es `INFO`.

para más detalle (útil en desarrollo), cambia a `DEBUG`:

```python
logging.basicConfig(level=logging.DEBUG)
```

---

## privacidad

**importante**: los logs pueden contener fragmentos de texto que dictaste. si compartes logs públicamente para debugging:

1. revisa que no contengan información sensible
2. considera anonimizar o truncar el contenido

---

## estructura interna

los logs son archivos de texto plano. el formato es:

```
TIMESTAMP - LEVEL - MESSAGE
```

fácil de parsear con herramientas estándar (`grep`, `awk`, scripts python).

---

## referencias

- [python logging](https://docs.python.org/3/library/logging.html) - biblioteca usada
- [log levels](https://docs.python.org/3/library/logging.html#logging-levels) - DEBUG, INFO, WARNING, ERROR
