# INFRASTRUCTURE

### ¿qué es esta carpeta?
esta carpeta corresponde a la `capa de infraestructura` en nuestra arquitectura ddd. es la capa más externa de la aplicación y se encarga de todos los detalles técnicos y de la comunicación con el mundo exterior.

### ¿para qué sirve?
su propósito es proporcionar las implementaciones concretas de las abstracciones (principalmente interfaces de repositorios) definidas en la `capa de dominio`. esta capa contiene el código "pegamento" que conecta la lógica de negocio con las tecnologías específicas que se utilizan.

### ¿qué puedo encontrar aquí?
*   `implementaciones de repositorios`: código que realmente guarda y recupera datos de una base de datos específica (e.g., `sqlite_transcripcion_repository`).
*   `clientes de api`: clases para comunicarse con servicios externos (e.g., `google_gemini_client`, `openai_whisper_client`).
*   `adaptadores de framework`: código que integra la aplicación con frameworks específicos, como servidores web o librerías de interfaz de usuario.
*   `manejo de archivos`: utilidades para interactuar con el sistema de archivos del sistema operativo.
*   `servicios de sistema`: implementaciones de interfaces para acceder a hardware, como el micrófono.

### arquitectura o diagramas
esta capa implementa el `principio de inversión de dependencias`. el `dominio` define un contrato (interfaz) y la `infraestructura` proporciona la implementación. esto permite cambiar de tecnología sin afectar al `dominio`.

```mermaid
graph TD
    subgraph Dominio
        A[transcription_repository (interfaz)]
    end

    subgraph Infraestructura
        B[sqlite_repository (implementación)]
        C[in_memory_repository (implementación)]
    end

    B -- implementa --> A
    C -- implementa --> A
```

### cómo contribuir
1.  **implementa una interfaz del dominio**: si necesitas añadir soporte para una nueva base de datos o api, crea una nueva clase que implemente la interfaz correspondiente del `dominio`.
2.  **registra la implementación**: utiliza el `contenedor de inyección de dependencias` del `core` para registrar tu nueva implementación, de modo que la `capa de aplicación` pueda resolverla.
3.  **maneja la configuración**: asegúrate de que cualquier clave de api, cadena de conexión u otra configuración se cargue desde el archivo `config.toml` y no esté codificada directamente.

### faqs o preguntas frecuentes
*   **¿puedo llamar a la capa de dominio desde aquí?**
    *   no directamente. la infraestructura implementa las interfaces del dominio, pero no debería llamar a los servicios de dominio. su rol es ser "llamada por" la capa de aplicación, que a su vez orquesta el dominio.
*   **¿y si necesito usar una nueva librería externa?**
    *   esta es la capa correcta para hacerlo. encapsula la librería en una clase que implemente una interfaz del dominio, para que el resto de la aplicación no dependa directamente de esa librería.

### referencias y recursos
*   `src/whisper_dictation/domain/README.md`: para ver las interfaces que esta capa debe implementar.
*   `config.toml`: el archivo donde se define la configuración para los componentes de infraestructura.
