# BACKEND

el corazón de voice2machine. aquí vive toda la lógica que convierte tu voz en texto y lo refina con inteligencia artificial.

---

## estructura

```
backend/
├── models/      # modelos de machine learning
├── logs/        # registro de actividad
├── prompts/     # plantillas para LLMs
└── src/         # código fuente de la aplicación
```

---

## 📦 models

**¿qué es?**  
espacio reservado para los modelos de machine learning que usa la aplicación localmente.

**¿para qué sirve?**  
almacena archivos pesados de modelos de lenguaje (formato GGUF) que no pueden versionarse en git por su tamaño. estos modelos permiten procesar texto sin depender de servicios cloud.

**ejemplos de contenido:**
- `qwen2.5-3b-instruct-q4_k_m.gguf` - modelo local para refinamiento de texto
- cualquier modelo compatible con llama.cpp

**nota importante:** estos archivos están excluidos en `.gitignore` por su peso. debes descargarlos manualmente según las instrucciones de instalación.

---

## 📋 logs

**¿qué es?**  
directorio donde se guardan los registros de actividad de la aplicación.

**¿para qué sirve?**  
permite diagnosticar problemas, auditar el uso del sistema y entender el comportamiento de los componentes en ejecución.

**archivos que encontrarás:**
- `llm.log` - interacciones con modelos de lenguaje (API calls, tokens procesados, tiempos de respuesta)
- `process.log` - eventos generales del daemon (inicio, detención, comandos recibidos)

**nota importante:** estos archivos `.log` también están excluidos en `.gitignore` y se generan automáticamente durante el uso.

---

## 💬 prompts

**¿qué es?**  
colección de plantillas de texto que guían el comportamiento de los modelos de lenguaje.

**¿para qué sirve?**  
separar la ingeniería de prompts del código permite iterar y mejorar las instrucciones sin tocar la lógica de la aplicación. cualquier persona puede editar un prompt sin ser programador.

**contenido destacado:**
- `refine_system.txt` - prompt principal para refinar transcripciones de voz
- `README.md` - documentación completa sobre cómo crear y usar prompts

**filosofía:** los prompts son código que habla con máquinas inteligentes. merecen su propio espacio y versionado.

---

## 💻 src

**¿qué es?**  
el código fuente completo de voice2machine. implementado como un paquete python moderno.

**¿para qué sirve?**  
contiene toda la lógica de:
- transcripción de audio con whisper
- refinamiento de texto con LLMs (local o cloud)
- gestión del daemon persistente
- comunicación IPC entre procesos
- integración con el sistema operativo (notificaciones, portapapeles, audio)

**arquitectura:**  
sigue principios de **arquitectura hexagonal** (ports and adapters) para mantener el código desacoplado, testeable y mantenible.

```
src/v2m/
├── application/     # casos de uso y servicios (transcripción, LLM)
├── core/            # núcleo del sistema (CQRS, DI, interfaces)
├── domain/          # entidades de negocio y errores
└── infrastructure/  # adaptadores concretos (audio, notificaciones, sistema)
```

**punto de entrada:**  
`main.py` - CLI unificado que puede actuar como daemon o cliente

**documentación completa:** consulta `src/v2m/README.md` para detalles de arquitectura interna.

---

## flujo de trabajo típico

1. **daemon** carga modelo whisper en memoria - esperando en `/tmp/v2m.sock`
2. **usuario** presiona atajo de teclado - script envía comando al daemon
3. **daemon** graba audio - transcribe con whisper - copia a portapapeles
4. **usuario** (opcional) activa refinamiento - llm procesa texto - reemplaza portapapeles

todo sucede localmente, sin tocar internet (excepto si usas backend cloud para LLM).

---

## requisitos

- python 3.12+
- GPU con CUDA (para whisper acelerado)
- dependencias en `requirements.txt`

consulta `/docs/instalacion.md` para el setup completo.

---

## licencia

GNU General Public License v3.0 - ver [LICENSE](../../LICENSE)
