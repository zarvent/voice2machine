# SCRIPTS

### ¿qué es esta carpeta?
esta carpeta contiene scripts de envoltura (`wrappers`) diseñados para simplificar la ejecución de la aplicación desde la línea de comandos.

### ¿para qué sirve?
su objetivo es abstraer la complejidad de la configuración del entorno y la invocación directa de los módulos de `python`. estos scripts se aseguran de que la aplicación se ejecute con el intérprete correcto, las dependencias adecuadas y los argumentos necesarios.

### ¿qué puedo encontrar aquí?
*   `scripts de shell (.sh)`: archivos ejecutables que actúan como puntos de entrada para diferentes funcionalidades de la aplicación.

### uso y ejemplos
para ejecutar la aplicación, utiliza los scripts desde la raíz del repositorio.

*   **ejemplo para iniciar el dictado:**
    ```bash
    # este comando activa el entorno virtual y ejecuta el proceso de dictado
    ./scripts/start_dictation.sh
    ```

*   **ejemplo para procesar un archivo de audio:**
    ```bash
    # este comando podría tomar un archivo como argumento y devolver la transcripción
    ./scripts/process_audio.sh --file /ruta/a/mi/audio.wav
    ```
    *(nota: los nombres de los scripts son ilustrativos y pueden variar)*

### cómo contribuir
1.  **crea un nuevo script**: añade un archivo `.sh` con un nombre descriptivo (e.g., `run_tests.sh`).
2.  **añade la lógica**: asegúrate de que el script active el entorno virtual de `python` y llame al módulo principal (`src/whisper_dictation/main.py`) con los comandos y argumentos correctos.
3.  **hazlo ejecutable**: no olvides dar permisos de ejecución al nuevo script con `chmod +x scripts/tu_nuevo_script.sh`.

### faqs o preguntas frecuentes
*   **¿por qué no ejecutar `python -m src.whisper_dictation.main` directamente?**
    *   usar scripts asegura que todos los desarrolladores ejecuten la aplicación de la misma manera y evita errores comunes relacionados con la activación del entorno virtual o la especificación de rutas.
*   **¿estos scripts funcionan en windows?**
    *   están diseñados principalmente para entornos `unix-like` (`linux`, `macos`). para `windows`, podría ser necesario crear archivos equivalentes `.bat` o usar `wsl`.

### referencias y recursos
*   `src/whisper_dictation/main.py`: el punto de entrada principal que estos scripts invocan.
