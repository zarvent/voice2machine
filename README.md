# 🗣️ herramienta de dictado por voz

_una herramienta de dictado por voz para transcribir audio en cualquier campo de texto del sistema operativo_

---

### 📚 documentacion completa

> **toda la documentacion detallada se encuentra en la carpeta `/docs`**
>
> explora la guia de instalacion, la arquitectura y mas navegando en esa carpeta.

---

## 🎯 proposito

el objetivo es simple:

> poder dictar texto en cualquier lugar del sistema operativo.

la idea es transcribir audio con una gpu para maxima velocidad, sin importar la aplicacion que estes usando.

este proyecto es una refactorizacion de un script simple a una aplicacion modular en python para separar responsabilidades y facilitar el mantenimiento a futuro.

---

## ⚙️ configuracion y desarrollo

### requisitos previos

*   python 3.10+
*   ffmpeg (para procesamiento de audio)
*   xclip o wl-clipboard (para gestion del portapapeles en linux)
*   gpu nvidia (opcional, pero recomendada para whisper)

### instalacion

1.  clona el repositorio:
    ```bash
    git clone <url-del-repo>
    cd v2m
    ```

2.  crea un entorno virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  instala las dependencias:
    ```bash
    pip install -r requirements.txt
    ```

4.  configura las variables de entorno:
    crea un archivo `.env` basado en el ejemplo (si existe) o configura manualmente:
    ```env
    gemini_api_key=tu_api_key_aqui
    ```

---

## 🚀 uso

la aplicacion funciona con un demonio en segundo plano y scripts clientes que envian comandos.

### iniciar el demonio

el demonio carga los modelos en memoria y espera comandos.

```bash
python -m v2m.main --daemon
```

### comandos del cliente

puedes controlar el demonio enviando comandos desde otra terminal:

*   **iniciar grabacion:**
    ```bash
    python -m v2m.main start_recording
    ```

*   **detener grabacion y transcribir:**
    ```bash
    python -m v2m.main stop_recording
    ```

*   **procesar texto del portapapeles (refinado con llm):**
    ```bash
    python -m v2m.main process_text "texto a procesar"
    ```

---

## 🕹️ flujo de trabajo

la interaccion tiene dos funciones principales activadas por atajos de teclado globales (configurados en tu gestor de ventanas) para no interrumpir tu trabajo.

#### 1. flujo de dictado (voz -> texto)

este es el flujo principal para capturar tu voz y convertirla en texto. se activa tipicamente con un script wrapper como `scripts/v2m-toggle.sh`.

```mermaid
%%{init: {"flowchart": {"htmllabels": false}} }%%
flowchart td
    subgraph voz a texto
        a["🎤 atajo 1<br/>_inicia grabacion_"] --> b{"transcribe con whisper"}
        b --> c["📋 copiado<br/>_texto en portapapeles_"]
    end

    style a fill:#8ebbff,stroke:#333,stroke-width:2px
    style b fill:#ffd68e,stroke:#333,stroke-width:2px
    style c fill:#a9e5bb,stroke:#333,stroke-width:2px
```

#### 2. flujo de refinado (texto -> texto mejorado)

a veces la transcripcion no es perfecta. este flujo toma el texto de tu portapapeles y usa un llm para limpiarlo, corregirlo o formatearlo. se activa con `scripts/v2m-process.sh`.

```mermaid
%%{init: {"flowchart": {"htmllabels": false}} }%%
flowchart td
    subgraph texto a texto mejorado
        a["📋 copias texto"] --> b["🧠 atajo 2<br/>_inicia refinado_"]
        b --> c{"procesa con llm<br/>_google gemini_"}
        c --> d["📋 reemplaza<br/>_texto mejorado en portapapeles_"]
    end

    style a fill:#f2c2e0,stroke:#333,stroke-width:2px
    style b fill:#8ebbff,stroke:#333,stroke-width:2px
    style c fill:#ffd68e,stroke:#333,stroke-width:2px
    style d fill:#a9e5bb,stroke:#333,stroke-width:2px
```

---

> _**nota sobre la visualizacion**: si los diagramas de flujo no se muestran en tu editor, asegurate de tener instalada una extension compatible con mermaid._
