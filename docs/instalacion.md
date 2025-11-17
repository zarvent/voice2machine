# 🛠️ INSTALACIÓN Y DIAGNÓSTICO

para poner esto en marcha necesitas configurar tres capas el sistema PYTHON y la IA

### 1. DEPENDENCIAS DEL SISTEMA

primero necesitas las herramientas básicas del sistema `ffmpeg` y `pactl` se usan para grabar audio mientras que `xclip` gestiona el portapapeles

*   **asegúrate de tener** `ffmpeg` `xclip` y `pactl`

> _para usuarios de GPU NVIDIA_
> si tienes una GPU NVIDIA asegúrate de que los drivers y el CUDA toolkit estén instalados para aprovechar la aceleración por hardware esto es **altamente recomendado** para un rendimiento óptimo

### 2. ENTORNO DE PYTHON

es una buena práctica usar un entorno virtual para mantener las dependencias del proyecto aisladas

```bash
# paso 1 crear un entorno virtual
python3 -m venv venv

# paso 2 activar el entorno
source venv/bin/activate

# paso 3 instalar dependencias
pip install -r requirements.txt
```

### 3. CONFIGURACIÓN DE IA (GOOGLE GEMINI)

para el refinado de texto la aplicación necesita tu clave de API de GOOGLE GEMINI la leemos desde un archivo `.env` para no exponerla en el código

```bash
# paso 1 crear el archivo .env si no existe
touch .env

# paso 2 añadir tu api key de gemini al archivo .env
echo 'GEMINI_API_KEY="AIzaSy..."' > .env
```

### 4. CONFIGURACIÓN DE LA APLICACIÓN

echa un vistazo a `config.toml` aquí es donde puedes afinar el rendimiento como elegir un modelo de WHISPER más pequeño si `large-v2` es demasiado pesado para tu sistema

*   **revisa** `config.toml`
*   **asegúrate** que `[whisper]` apunte al modelo y dispositivo correctos (ej `model = "large-v2"` `device = "cuda"`)

### 5. VERIFICACIÓN

para asegurar que todo esté conectado correctamente puedes usar estos scripts

*   `scripts/verify-setup.sh` te da un chequeo rápido de las dependencias del sistema
*   `python test_whisper_gpu.py` es útil para confirmar que `faster-whisper` está usando tu GPU y no el CPU
