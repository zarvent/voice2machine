# MODELS

almacén de modelos de machine learning para procesamiento local.

---

## ¿qué es?

este directorio contiene los modelos de lenguaje que voice2machine usa para procesar texto de manera local, sin depender de APIs cloud.

---

## ¿para qué sirve?

permite que la aplicación funcione completamente offline (para la parte de LLM). los modelos se cargan en memoria y se usan para tareas como:

- refinar transcripciones de voz
- corregir gramática y puntuación
- mejorar claridad del texto dictado

---

## ¿por qué existe?

**privacidad primero**: tu texto no sale de tu máquina. todo el procesamiento ocurre localmente.

**velocidad**: modelos en GPU local pueden ser más rápidos que llamadas a APIs remotas (sin latencia de red).

**costo cero**: sin límites de tokens ni facturas mensuales por uso de APIs.

---

## contenido típico

```
models/
└── qwen2.5-3b-instruct-q4_k_m.gguf   # modelo de 3B parámetros cuantizado
```

### formato GGUF

los modelos usan formato [GGUF](https://github.com/ggerganov/ggml) compatible con llama.cpp. esto permite:

- carga rápida en memoria
- inferencia eficiente en GPU/CPU
- cuantización para reducir uso de VRAM

---

## cómo obtener modelos

los archivos `.gguf` son pesados (varios GB) y están excluidos en `.gitignore`. debes descargarlos manualmente:

1. busca modelos en [huggingface](https://huggingface.co/models?library=gguf)
2. descarga el archivo `.gguf` que desees
3. colócalo en este directorio `models/`
4. actualiza la ruta en `config.toml`:

```toml
[llm.local]
model_path = "models/tu-modelo.gguf"
```

---

## modelos recomendados

para voice2machine, modelos pequeños y rápidos funcionan mejor:

- **qwen2.5-3b-instruct** (cuantizado Q4): excelente balance calidad/velocidad
- **phi-3-mini** (3.8B): alternativa rápida de microsoft
- **llama-3.2-3b-instruct**: opción de meta

evita modelos >7B a menos que tengas GPU potente (24GB+ VRAM).

---

## estructura interna

este directorio solo almacena archivos `.gguf`. no contiene código. la lógica de carga está en `src/v2m/application/llm_service.py`.

---

## troubleshooting

**problema**: modelo no carga / out of memory  
**solución**: usa un modelo más pequeño o aumenta cuantización (Q4 → Q5 → Q8)

**problema**: inferencia muy lenta  
**solución**: verifica que estés usando GPU (`device = "cuda"` en config.toml)

---

## referencias

- [llama.cpp](https://github.com/ggerganov/llama.cpp) - motor de inferencia
- [GGUF spec](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md) - formato de archivos
- [cuantización explicada](https://huggingface.co/docs/optimum/concept_guides/quantization) - por qué usar Q4/Q5
