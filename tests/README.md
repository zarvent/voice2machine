# 🧪 Suite de Pruebas - v2m

Bienvenido al directorio de pruebas del proyecto voice2machine. Este documento
sirve como guía completa para entender, ejecutar y contribuir a las pruebas.

## Filosofía de Testing

Las pruebas automatizadas son la primera línea de defensa contra regresiones.
Siguiendo el principio de "fail fast", nos permiten detectar problemas antes
de que lleguen a producción.

**Beneficios clave:**

- **Confianza para refactorizar**: Puedes cambiar código sabiendo que las pruebas te avisarán si rompes algo.
- **Documentación ejecutable**: Las pruebas demuestran cómo se usa el código.
- **Diseño mejorado**: Código difícil de probar suele ser código mal diseñado.

## 📁 Estructura del Directorio

```text
tests/
├── README.md                     # Esta guía
├── integration/                  # Pruebas de integración (en desarrollo)
└── unit/                         # Pruebas unitarias
    ├── test_audio_recorder.py    # Componente de captura de audio
    ├── test_config.py            # Sistema de configuración
    └── test_vad_service.py       # Servicio de detección de voz
```

### Tipos de pruebas

| Tipo | Propósito | Velocidad | Aislamiento |
|------|-----------|-----------|-------------|
| **Unitarias** | Verificar componentes individuales | Rápidas (~ms) | Total (con mocks) |
| **Integración** | Verificar interacción entre componentes | Medias (~s) | Parcial |
| **E2E** | Verificar flujos completos | Lentas (~min) | Ninguno |

En v2m priorizamos pruebas unitarias por su velocidad y determinismo.

## 🚀 Ejecución de Pruebas

### Comandos básicos

```bash
# Ejecutar todas las pruebas con output detallado
pytest tests/ -v

# Solo pruebas unitarias
pytest tests/unit/ -v

# Un archivo específico
pytest tests/unit/test_vad_service.py -v

# Una prueba específica (formato: archivo::funcion)
pytest tests/unit/test_vad_service.py::test_vad_process_with_speech -v
```

### Análisis de cobertura

La cobertura de código mide qué porcentaje del código fuente es ejecutado
por las pruebas. Una métrica útil, aunque no garantiza calidad por sí sola.

```bash
# Generar reporte de cobertura en terminal
pytest tests/ --cov=src/v2m

# Generar reporte HTML interactivo
pytest tests/ --cov=src/v2m --cov-report=html
# Abrir htmlcov/index.html en navegador

# Fallar si la cobertura es menor al 80%
pytest tests/ --cov=src/v2m --cov-fail-under=80
```

## 📋 Descripción de los Módulos de Prueba

### test_audio_recorder.py

Verifica el componente `AudioRecorder`, responsable de la captura de audio
desde dispositivos de entrada del sistema.

| Prueba | Descripción | Tipo |
|--------|-------------|------|
| `test_stop_clears_frames` | Valida que stop() libere el buffer interno y falle en llamadas subsecuentes | Edge case |

**Conceptos clave:**

- Patrón de acumulación de frames
- Principio de single-use
- Test doubles con `unittest.mock`

### test_config.py

Verifica el sistema de configuración basado en TOML.

| Prueba | Descripción | Tipo |
|--------|-------------|------|
| `test_config_loading` | Valida la carga correcta de parámetros desde config.toml | Smoke test |

**Conceptos clave:**

- Configuración externa (twelve-factor app)
- Contract testing

### test_vad_service.py

Verifica el servicio de Voice Activity Detection basado en Silero VAD.

| Prueba | Descripción | Tipo |
|--------|-------------|------|
| `test_vad_process_empty_audio` | Manejo robusto de entrada vacía | Edge case |
| `test_vad_process_no_speech` | Correcta identificación de silencio | Negative test |
| `test_vad_process_with_speech` | Extracción correcta de segmentos de voz | Happy path |
| `test_vad_uses_configured_threshold` | Prevención de regresión (threshold hardcodeado) | Regression test |

**Conceptos clave:**

- Voice Activity Detection
- Teorema de Nyquist (sample rate 16kHz)
- Threshold/umbral de detección

## 🔧 Configuración del Entorno

### Dependencias

```bash
pip install pytest pytest-cov
```

### Fixtures de pytest

Las fixtures son el mecanismo de pytest para inyección de dependencias en tests.
Reemplazan y mejoran el patrón setUp/tearDown de unittest.

**Disponibles en test_vad_service.py:**

```python
@pytest.fixture
def vad_service() -> VADService:
    """Instancia base, sin modificaciones."""
    return VADService()

@pytest.fixture
def configured_vad_service() -> VADService:
    """Instancia con modelo mockeado para pruebas rápidas."""
    service = VADService()
    service.load_model = MagicMock()
    service.model = MagicMock()
    return service
```

## 📝 Guía de Estilo para Pruebas

### Nomenclatura

Seguimos convenciones estándar de Python y pytest:

```python
# Archivos: test_<modulo>.py
test_audio_recorder.py

# Clases: Test<Componente>
class TestAudioRecorder:

# Funciones: test_<accion>_<resultado_esperado>
def test_stop_clears_frames():
def test_process_empty_audio_returns_empty():
```

### Estructura AAA (Arrange-Act-Assert)

Cada prueba debe tener tres secciones claramente identificables:

```python
def test_ejemplo() -> None:
    """Descripción del caso de prueba."""
    # ARRANGE: Preparar el escenario
    service = MiServicio()
    datos = crear_datos_prueba()

    # ACT: Ejecutar la acción bajo prueba
    resultado = service.procesar(datos)

    # ASSERT: Verificar el resultado
    assert resultado.exitoso is True
    assert resultado.valor == esperado
```

### Docstrings de pruebas

Los docstrings deben explicar el **por qué**, no solo el **qué**:

```python
def test_stop_raises_when_not_recording() -> None:
    """Verifica que stop() falle sin grabación activa.

    Caso de prueba
    --------------
    Llamar stop() sin haber llamado start() previamente.

    Motivación
    ----------
    Un stop() sin start() indica un error de programación.
    Preferimos fallar explícitamente a retornar datos incorrectos
    (principio de fail-fast).

    Raises:
        AssertionError: Si no se lanza RecordingError.
    """
```

## 🐛 Debugging de Pruebas

### Opciones útiles de pytest

```bash
# Mostrar print() y logging
pytest tests/ -v -s

# Detenerse en el primer fallo
pytest tests/ -x

# Re-ejecutar solo las que fallaron
pytest tests/ --lf

# Entrar al debugger en fallos
pytest tests/ --pdb

# Ejecutar las más lentas primero (útil para identificar cuellos de botella)
pytest tests/ --durations=10
```

### Investigar fallos

1. **Lee el mensaje de error completo** - pytest da contexto detallado.
2. **Revisa el diff** - En assertions, muestra qué esperabas vs qué obtuviste.
3. **Usa -s** - Si tienes prints de debug, -s los muestra.
4. **Aísla la prueba** - Corre solo esa prueba con `::nombre_funcion`.

## 📊 Métricas de Calidad

### Cobertura objetivo

Apuntamos a **≥80% de cobertura de línea** como baseline. Sin embargo,
cobertura alta no garantiza calidad - una prueba puede ejecutar código
sin verificar su comportamiento.

**Más importante que el número:**

- Cubrir los caminos críticos (happy paths)
- Cubrir los edge cases conocidos
- Tener al menos un test de regresión por bug arreglado

### Velocidad de ejecución

Las pruebas unitarias deben ser rápidas. Si una prueba tarda más de 1 segundo,
considera:

- ¿Está cargando recursos pesados que podrían mockearse?
- ¿Está haciendo I/O que podría evitarse?
- ¿Debería ser una prueba de integración?

## 🤝 Contribución

### Checklist antes de merge

- [ ] Escribí pruebas para el código nuevo
- [ ] Todas las pruebas pasan (`pytest tests/ -v`)
- [ ] La cobertura no bajó (`pytest --cov --cov-fail-under=80`)
- [ ] Los docstrings explican el propósito de cada prueba
- [ ] Seguí el patrón AAA y las convenciones de nomenclatura

### Recursos adicionales

- [pytest documentation](https://docs.pytest.org/)
- [Python Testing with pytest](https://pragprog.com/titles/bopytest2/) - Brian Okken
- [xUnit Test Patterns](http://xunitpatterns.com/) - Gerard Meszaros
