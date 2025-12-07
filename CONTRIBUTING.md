# 🤝 contributing

gracias por tu interés en contribuir a voice2machine

---

## antes de empezar

1. **abre un issue** para discutir cambios significativos antes de codear
2. **revisa issues existentes** para evitar duplicados
3. **lee la [arquitectura](docs/arquitectura.md)** para entender el diseño hexagonal

---

## setup de desarrollo

```bash
# clonar repo
git clone https://github.com/zarvent/voice2machine.git
cd voice2machine

# crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# instalar dependencias
pip install -r requirements.txt

# configurar variables de entorno
cp .env.example .env  # editar con tu GEMINI_API_KEY

# verificar setup
python scripts/check_cuda.py
pytest tests/ -v
```

---

## estándares de código

### estilo
- **PEP8** como base
- **ruff** para linting: `ruff check src/ scripts/`
- **type hints** en funciones públicas
- **docstrings** estilo Google

### ejemplo
```python
def transcribe_audio(audio_path: Path, model: str = "large-v3-turbo") -> str:
    """Transcribe audio file using Whisper.

    Args:
        audio_path: Path to the audio file.
        model: Whisper model name.

    Returns:
        Transcribed text.

    Raises:
        FileNotFoundError: If audio file doesn't exist.
    """
    ...
```

### commits
- mensajes claros y descriptivos
- prefijos: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- ejemplo: `feat: add ollama llm adapter`

---

## proceso de pull request

1. **fork** el repositorio
2. **crea una rama** desde `main`:
   ```bash
   git checkout -b feat/mi-feature
   ```
3. **haz tus cambios** siguiendo los estándares
4. **ejecuta tests**:
   ```bash
   pytest tests/ -v
   ruff check src/ scripts/
   ```
5. **commit y push**:
   ```bash
   git commit -m "feat: descripcion clara"
   git push origin feat/mi-feature
   ```
6. **abre PR** con descripción de:
   - qué cambia
   - por qué es necesario
   - cómo probarlo

---

## estructura del proyecto

```
voice2machine/
├── src/v2m/           # código principal
│   ├── domain/        # interfaces y entidades
│   ├── application/   # comandos y handlers
│   └── infrastructure/ # adaptadores (whisper, gemini, audio)
├── scripts/           # utilidades y entry points
├── tests/             # tests unitarios e integración
├── docs/              # documentación
└── prompts/           # prompts para LLM
```

---

## tipos de contribuciones bienvenidas

- 🐛 **bug fixes**: reporta o corrige errores
- 📝 **documentación**: mejora docs, traducciones
- ✨ **features**: nuevas funcionalidades (discutir primero)
- 🧪 **tests**: aumenta cobertura
- 🌐 **i18n**: traducciones al inglés u otros idiomas

---

## code of conduct

sé respetuoso y constructivo. este es un proyecto personal abierto a la comunidad.

- trata a otros como quieres ser tratado
- acepta feedback constructivo
- enfócate en el código, no en las personas

---

## preguntas?

abre un issue con el tag `question` o contacta via el repo.
