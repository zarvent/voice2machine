# 🗣️ HERRAMIENTA DE DICTADO POR VOZ

<https://github.com/user-attachments/assets/e1b8a747-61fc-4afc-bd48-0db9f0774eaf>

---

## 🎯 propósito

> su propósito es integrar la transcripción de audio en todo tu sistema operativo.
> puedes dictar texto en cualquier campo de escritura sin importar la aplicación.
> el sistema está diseñado para ser eficiente y rápido.

---

## 🕹️ interacción

para interactuar con el sistema utilizas un único atajo de teclado:

- **`ctrl` + `mayúsculas` + `espacio`**

1. ⏺️ al presionarlo por primera vez se inicia la grabación de audio desde tu micrófono.
2. ⏹️ al presionarlo de nuevo la grabación se detiene y comienza el proceso de transcripción.
3. 📋 el texto resultante se copia automáticamente a tu portapapeles.
4. 📥 luego puedes pegarlo

---

## 🧩 núcleo del sistema

- el núcleo de este sistema es el modelo de lenguaje **Whisper** de OpenAI.
- específicamente se utiliza **faster-whisper**, una reimplementación optimizada para velocidad.
- el script principal `whisper-toggle.sh` gestiona el estado de la grabación.
- crea un archivo temporal para saber si está grabando o no.
- al detener la grabación este script invoca un proceso de Python.
- este proceso carga el modelo Whisper en la GPU utilizando la tecnología **CUDA**.
- la computación se realiza en **float16** para maximizar el rendimiento en tarjetas RTX.
- puedes verificar la correcta aceleración de tu GPU con el script `test_whisper_gpu`.
- una vez transcrito el texto el script utiliza la utilidad **xclip** para copiarlo al portapapeles.

---

## 🛠️ diagnóstico y dependencias

> antes de usarlo por primera vez el script `verify-setup` te ayuda a diagnosticar el sistema.

- revisa que todas las dependencias como **ffmpeg**, **CUDA** y **xclip** estén instaladas.
- así puedes asegurar que el entorno está configurado correctamente para su operación.

---

<https://github.com/user-attachments/assets/5bcadcfa-14f9-42a1-b3fc-dec93aa01996>

---

---

## 🧠 procesamiento con IA (Opcional)

además del dictado básico, el sistema incluye un procesador inteligente de texto:

- utiliza la **API de Google Gemini** para refinar y mejorar el texto transcrito.
- puedes procesar el contenido de tu portapapeles con un segundo atajo de teclado.
- el sistema lee el portapapeles, lo envía a Gemini, y devuelve el texto mejorado.
- el procesador se encuentra en `llm_processor.py` y usa el modelo **gemini-2.5-flash**.
- requiere configurar tu `GEMINI_API_KEY` en el archivo `.env`.

---

nota: para más detalles ampliados de la nueva actualización consulta [archives/2025-11-15 nueva feature](archives/2025-11-15%20nueva%20feature.md).

para información sobre la migración de Perplexity a Gemini consulta [MIGRATION.md](MIGRATION.md).

```
