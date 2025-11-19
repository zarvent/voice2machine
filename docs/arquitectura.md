# 🧩 ARQUITECTURA

este proyecto sigue principios de diseño robustos como la **inyección de dependencias (DI)** y un **bus de comandos (CQRS)** para orquestar los servicios de una manera desacoplada y fácil de mantener

a continuación se detallan los componentes clave y cómo interactúan entre sí

---

### DIAGRAMA DE COMPONENTES

este diagrama muestra las capas principales de la aplicación y sus responsabilidades

```mermaid
graph TD
    subgraph A[CAPA DE ENTRADA]
        direction LR
        main("main.py<br/>_punto de entrada_")
    end

    subgraph B[CAPA DE APLICACIÓN]
        direction TB
        bus(COMMAND BUS)
        handlers("handlers<br/>_lógica de negocio_")
    end

    subgraph C[CAPA DE INFRAESTRUCTURA]
        direction TB
        whisper("WHISPER<br/>_transcripción_")
        gemini("GEMINI<br/>_refinado LLM_")
    end

    subgraph D[CAPA DE CONFIGURACIÓN]
        direction LR
        container("DI CONTAINER<br/>_inyección de dependencias_")
        config("config.toml<br/>_parámetros_")
    end

    main -- "envía comandos" --> bus
    bus -- "dirige a" --> handlers
    handlers -- "usan" --> whisper
    handlers -- "usan" --> gemini
    container -- "configura" --> handlers
    config -- "provee a" --> container

    style main fill:#8EBBFF,stroke:#333,stroke-width:2px
    style bus fill:#FFD68E,stroke:#333,stroke-width:2px
    style handlers fill:#FFD68E,stroke:#333,stroke-width:2px
    style whisper fill:#A9E5BB,stroke:#333,stroke-width:2px
    style gemini fill:#A9E5BB,stroke:#333,stroke-width:2px
    style container fill:#F2C2E0,stroke:#333,stroke-width:2px
    style config fill:#F2C2E0,stroke:#333,stroke-width:2px
```

---

### DESCRIPCIÓN DE COMPONENTES

| componente                                | descripción                                                              |
| ------------------------------------------- | ------------------------------------------------------------------------ |
| `src/v2m/main.py`             | el **controlador** principal que escucha comandos desde los scripts de shell (`start` `stop` `process`) |
| `src/v2m/core/di/container.py`  | el **orquestador** donde se conectan las interfaces con sus implementaciones concretas ej `LLMService` se resuelve a `GeminiLLMService` |
| `src/v2m/application/`        | el **cerebro** con la lógica de negocio pura los comandos y los handlers que definen qué hacer |
| `src/v2m/infrastructure/`     | las **manos** que interactúan con el mundo real como la API de WHISPER o GOOGLE GEMINI |
| `config.toml`                               | el **panel de control** para configurar modelos dispositivos y otros parámetros |
| `.env`                                      | los **secretos** como tu `GEMINI_API_KEY` para mantenerlos fuera del código fuente |
