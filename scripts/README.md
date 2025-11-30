# Scripts de V2M

> **¿Eres nuevo aquí?** No te preocupes, este documento está pensado para que cualquier persona pueda entender qué hace cada script, sin importar tu nivel de experiencia.

---

## ¿Qué hay en esta carpeta?

Aquí encontrarás todas las herramientas auxiliares del proyecto Voice2Machine. Piensa en estos scripts como los "ayudantes" que hacen el trabajo pesado por ti: iniciar el servicio, diagnosticar problemas, limpiar archivos temporales, etc.

Los scripts están divididos en dos grupos:

| Tipo | Extensión | Para qué sirven |
|------|-----------|-----------------|
| **Shell** | `.sh` | Control del daemon, atajos de teclado, verificaciones rápidas |
| **Python** | `.py` | Diagnósticos, pruebas, instalación y mantenimiento |

---

## Lo que necesitas saber antes de empezar

### Prerrequisitos

Antes de ejecutar cualquier script, asegúrate de tener:

1. **Linux** (Ubuntu 22.04 o superior recomendado)
2. **Python 3.12+** instalado
3. **El entorno virtual creado** en `./venv`

Si acabas de clonar el repositorio, primero corre:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Cómo ejecutar los scripts

Siempre ejecuta los scripts **desde la raíz del proyecto** (donde está `config.toml`):

```bash
# Para scripts de shell
./scripts/nombre-del-script.sh

# Para scripts de Python
python scripts/nombre_del_script.py
```

---

## Scripts de Shell (los que usarás día a día)

Estos son los scripts que probablemente uses con más frecuencia.

### `v2m-toggle.sh` — El script principal

Este es **el corazón de V2M**. Con él controlas la grabación de voz.

**¿Cómo funciona?**

1. Lo ejecutas una vez → empieza a grabar
2. Lo ejecutas de nuevo → para de grabar, transcribe y copia al portapapeles

**Uso típico:**

```bash
./scripts/v2m-toggle.sh   # Presionas, hablas, presionas de nuevo
```

**Tip profesional:** Asigna este script al atajo `Ctrl+Shift+Space` para usarlo sin tocar la terminal.

---

### `v2m-daemon.sh` — Control del servicio

Gestiona el daemon (el proceso que corre en segundo plano esperando tus comandos de voz).

| Comando | Qué hace |
|---------|----------|
| `start` | Inicia el daemon |
| `stop` | Lo detiene |
| `restart` | Lo reinicia (útil después de cambiar configuración) |
| `status` | Te dice si está corriendo y si responde |
| `logs` | Muestra los logs para debugging |

**Ejemplos:**

```bash
# "Oye, ¿el daemon está vivo?"
./scripts/v2m-daemon.sh status

# "Se trabó algo, reinícialo"
./scripts/v2m-daemon.sh restart

# "Quiero ver qué está pasando internamente"
./scripts/v2m-daemon.sh logs
```

---

### `v2m-verify.sh` — Chequeo de salud del sistema

Corre este script cuando algo no funcione. Verifica TODO:

- ✅ Entorno virtual
- ✅ Whisper instalado
- ✅ CUDA funcionando
- ✅ Micrófono detectado
- ✅ FFmpeg y xclip presentes
- ✅ Atajos de teclado configurados

```bash
./scripts/v2m-verify.sh
```

Si ves todo en verde, estás bien. Si algo sale en rojo, el script te dice cómo arreglarlo.

---

### `v2m-process.sh` — Procesar texto del portapapeles

¿Copiaste un texto y quieres que Gemini lo mejore? Este script:

1. Lee lo que tengas en el portapapeles
2. Se lo manda a Gemini
3. Reemplaza el portapapeles con el resultado

```bash
# Copia algo primero, luego:
./scripts/v2m-process.sh
# Ahora Ctrl+V para pegar el texto mejorado
```

---

### `v2m-gemini.sh` — Enviar texto directo a Gemini

Similar al anterior, pero le pasas el texto como argumento:

```bash
./scripts/v2m-gemini.sh "corrige este texto con herrores de hortografia"
```

---

### `repair_libs.sh` — Reparar librerías NVIDIA

¿Ves errores como `libcudnn_ops.so.9 not found`? Este script reinstala las librerías CUDA de forma limpia.

```bash
./scripts/repair_libs.sh
```

> ⚠️ **Nota:** Solo córrelo si tienes problemas con CUDA. Si todo funciona, no lo toques.

---

## Scripts de Python (diagnóstico y mantenimiento)

Estos scripts son más técnicos, pero igual de importantes.

### Diagnóstico

#### `check_cuda.py` — ¿Funciona mi GPU?

El más simple pero crucial. Te dice si CUDA está disponible y si cuDNN funciona.

```bash
python scripts/check_cuda.py
```

**Salida esperada (si todo está bien):**

```
Python: /home/tu-usuario/v2m/venv/bin/python
CUDA Available: True
CUDA Device: NVIDIA GeForce RTX 3060
✅ Operación cuDNN básica exitosa
```

---

#### `diagnose_audio.py` — Problemas con el micrófono

Si V2M no "escucha" nada, corre este script. Te muestra todos los micrófonos disponibles y te deja probarlos uno por uno.

```bash
python scripts/diagnose_audio.py
```

El script te guía paso a paso:

1. Lista todos los dispositivos
2. Te pregunta cuál probar
3. Te pide que hables
4. Te dice si detectó señal

**Si ningún micrófono muestra señal**, revisa:
- Que el mic esté conectado y encendido
- Los niveles en `pavucontrol` o `alsamixer`
- Que tu usuario esté en el grupo `audio`

---

#### `test_clipboard.py` — ¿El portapapeles funciona?

V2M copia automáticamente las transcripciones al portapapeles. Este script verifica que eso funcione.

```bash
python scripts/test_clipboard.py
```

---

#### `test_whisper_standalone.py` — Prueba completa de transcripción

Prueba el pipeline completo: carga el modelo, genera audio de prueba, transcribe.

```bash
python scripts/test_whisper_standalone.py
```

Útil para verificar que todo esté bien después de instalar o actualizar.

---

#### `test_whisper_gpu.py` — Cargar el modelo grande

La primera vez que corras V2M, necesita descargar el modelo Whisper (~3GB). Este script lo hace por ti y verifica que cargue en GPU.

```bash
python scripts/test_whisper_gpu.py
```

> La primera ejecución toma 5-10 minutos (descarga). Las siguientes son instantáneas.

---

#### `verify_daemon.py` — Prueba de integración

Corre una prueba completa del sistema: inicia el daemon, envía comandos, graba, transcribe, y limpia.

```bash
python scripts/verify_daemon.py
```

> ⚠️ **Importante:** No ejecutes esto mientras el servicio systemd esté corriendo. Causa conflictos.

---

### Mantenimiento

#### `cleanup.py` — Limpieza del proyecto

Con el tiempo se acumulan archivos temporales (`__pycache__`, logs viejos, etc.). Este script los elimina.

```bash
# Ver qué se eliminaría (sin borrar nada)
python scripts/cleanup.py --dry-run --all

# Ejecutar la limpieza
python scripts/cleanup.py --all
```

**Opciones disponibles:**

| Opción | Qué limpia |
|--------|------------|
| `--all` | Todo lo siguiente |
| `--cache` | Directorios `__pycache__` y archivos `.pyc` |
| `--fix-venv` | Elimina `.venv` duplicado si existe |
| `--logs` | Logs más viejos de 7 días |
| `--orphans` | Archivos huérfanos de pip |

---

#### `monitor_resources.py` — ¿Cuántos recursos consume V2M?

Genera un reporte de uso de memoria, GPU, disco y procesos.

```bash
# Ver en pantalla
python scripts/monitor_resources.py

# Guardar a archivo
python scripts/monitor_resources.py --save reporte.md
```

---

#### `install_service.py` — Instalar como servicio del sistema

Configura V2M para que arranque automáticamente cuando inicies sesión.

```bash
python scripts/install_service.py
```

Esto crea un servicio systemd de usuario. Después puedes controlarlo con:

```bash
systemctl --user status v2m.service
systemctl --user restart v2m.service
```

---

#### `list_models.py` — Ver modelos Gemini disponibles

Lista todos los modelos de Gemini a los que tienes acceso con tu API key.

```bash
python scripts/list_models.py
```

---

## Solución de problemas comunes

### "El daemon no responde"

```bash
./scripts/v2m-daemon.sh status    # ¿Está corriendo?
./scripts/v2m-daemon.sh logs      # ¿Qué dicen los logs?
./scripts/v2m-daemon.sh restart   # Reinícialo
```

### "CUDA no funciona"

```bash
python scripts/check_cuda.py      # Diagnóstico básico
./scripts/repair_libs.sh          # Reinstalar librerías
python scripts/check_cuda.py      # Verificar de nuevo
```

### "No detecta mi voz"

```bash
python scripts/diagnose_audio.py  # Probar micrófonos
# Sigue las instrucciones en pantalla
```

### "El portapapeles no funciona"

```bash
python scripts/test_clipboard.py
# Si falla, verifica que tengas xclip instalado:
sudo apt install xclip
```

### "Todo está lento / consume mucha memoria"

```bash
python scripts/monitor_resources.py   # Ver qué consume recursos
python scripts/cleanup.py --all       # Limpiar archivos temporales
```

---

## Para contribuidores

### Agregar un nuevo script de Python

1. Crea el archivo en `scripts/` con nombre descriptivo (`mi_utilidad.py`)
2. Agrega un docstring al inicio explicando qué hace
3. Documenta cada función con Google Style Docstrings
4. Actualiza este README

### Agregar un nuevo script de Shell

1. Crea el archivo (`mi-script.sh`)
2. Agrega documentación en comentarios al inicio
3. Hazlo ejecutable: `chmod +x scripts/mi-script.sh`
4. Actualiza este README

---

## ¿Preguntas?

Si algo no quedó claro o encontraste un error en la documentación, abre un issue en el repositorio. La documentación es tan importante como el código, y cualquier mejora es bienvenida.

---

**Última actualización:** Noviembre 2025
