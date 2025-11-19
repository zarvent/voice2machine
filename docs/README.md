# DOCS

### qué es esta carpeta
esta carpeta contiene los archivos fuente de la documentación oficial del proyecto la documentación se escribe en formato `markdown` y se compila utilizando `mkdocs` para generar un sitio web estático y navegable

### para qué sirve
su objetivo es centralizar toda la información detallada del proyecto desde guías de instalación y tutoriales hasta explicaciones profundas sobre la arquitectura y el diseño del software sirve como la fuente de verdad para cualquier persona que necesite entender el proyecto a fondo

### qué puedo encontrar aquí
*   `archivos markdown (.md)` el contenido de la documentación cada archivo `.md` suele corresponder a una página del sitio
*   `imágenes y otros recursos` los archivos multimedia utilizados en la documentación
*   `mkdocs.yml` el archivo de configuración principal de `mkdocs` que define la estructura de navegación el tema y las extensiones

### uso y ejemplos
para visualizar la documentación en tu entorno local puedes seguir estos pasos

1.  asegúrate de tener `mkdocs` instalado (`pip install mkdocs`)
2.  navega a la raíz del proyecto en tu terminal
3.  ejecuta el siguiente comando
    ```bash
    mkdocs serve
    ```
4.  abre tu navegador y visita `http://127.0.0.1:8000` para ver el sitio de documentación

### cómo contribuir
1.  **editar contenido** modifica los archivos `.md` existentes para corregir errores o mejorar la información
2.  **añadir nueva sección** crea un nuevo archivo `.md` y añádelo a la estructura de navegación en el archivo `mkdocs.yml`
3.  **verificar cambios** ejecuta `mkdocs serve` para asegurarte de que tus cambios se visualizan correctamente antes de enviarlos

### faqs o preguntas frecuentes
*   **debo editar los archivos html directamente**
    *   no los archivos `html` son generados automáticamente por `mkdocs` siempre debes editar los archivos fuente `.md`
*   **por qué mis cambios no aparecen en el sitio web**
    *   asegúrate de haber guardado el archivo `.md` y de que el servidor de `mkdocs` se haya recargado si es necesario detén (`ctrl+c`) y vuelve a iniciar el servidor

### referencias y recursos
*   `mkdocs.yml` el archivo de configuración principal que define la estructura de la documentación
*   [documentación oficial de mkdocs](https://www.mkdocs.org/) para aprender más sobre cómo usar esta herramienta
