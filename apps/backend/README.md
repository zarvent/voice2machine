# BACKEND

el corazón de voice2machine. aquí vive toda la lógica que convierte tu voz en texto y lo refina con inteligencia artificial.

---

## estructura

```
backend/
├── models/      # modelos de machine learning
├── logs/        # registros de actividad
├── prompts/     # plantillas para LLMs
└── src/         # código fuente principal
```

---

## 📁 directorios

cada directorio tiene su propio README con documentación detallada:

### [models/](models/)
almacenamiento de modelos de lenguaje en formato GGUF para inferencia local. estos archivos son pesados y no se versionan en git.

### [logs/](logs/)
registros de actividad generados automáticamente durante la ejecución. útil para diagnóstico y auditoría del sistema.

### [prompts/](prompts/)
plantillas de texto que guían el comportamiento de los LLMs. desacopladas del código para facilitar la experimentación.

### [src/](src/)
paquete python con toda la lógica de la aplicación. implementa arquitectura hexagonal para mantener el código limpio y testeable.

---

## flujo general

1. daemon carga whisper en memoria
2. usuario graba voz con atajo de teclado  
3. whisper transcribe y copia al portapapeles
4. opcionalmente, llm refina el texto

todo local, sin depender de servicios cloud (excepto si configuras backend remoto para LLM).

---

## requisitos

- python 3.12+
- GPU con CUDA
- ver `requirements.txt` para dependencias

consulta `/docs/instalacion.md` para setup completo.
