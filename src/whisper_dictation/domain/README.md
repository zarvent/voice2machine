# DOMAIN

### qué es esta carpeta
esta carpeta corresponde a la `capa de dominio` en nuestra arquitectura DDD es el corazón conceptual de la aplicación donde reside la lógica las reglas y el lenguaje del negocio

### para qué sirve
su propósito es modelar el dominio del problema que el software intenta resolver de una manera pura y aislada de las preocupaciones tecnológicas esta capa es la representación del negocio en el código y es completamente independiente de cómo se muestran los datos cómo se almacenan o qué sistemas externos se utilizan

### qué puedo encontrar aquí
*   `entidades` objetos que tienen una identidad única que persiste a lo largo del tiempo (eg `transcripcion`)
*   `objetos de valor` objetos inmutables definidos por sus atributos sin una identidad conceptual (eg `segmento_de_audio`)
*   `agregados` clústeres de entidades y objetos de valor que se tratan como una única unidad para los cambios de datos
*   `servicios de dominio` lógica de negocio que no encaja de forma natural en una entidad u objeto de valor
*   `interfaces de repositorio` contratos (interfaces) que definen cómo se deben persistir y recuperar los agregados abstrayendo el mecanismo de almacenamiento
*   `eventos de dominio` objetos que representan algo que sucedió en el dominio y que es de interés para otras partes del sistema

### uso y ejemplos
el código en esta capa se centra en la semántica del negocio

*   **ejemplo de una entidad `transcripcion` (conceptual)**
    ```python
    class Transcripcion:
        def __init__(self, id: TranscripcionId, texto: str):
            self.id = id
            self.texto = texto
            self.estado = "en_progreso"

        def marcar_como_completada(self):
            if self.estado == "en_progreso":
                self.estado = "completada"
                # aquí se podría disparar un evento de dominio
                self.registrar_evento(TranscripcionCompletada(self.id))
    ```

### cómo contribuir
1.  **piensa en el negocio** antes de escribir código modela los conceptos del dominio
2.  **mantén la pureza** el código de dominio no debe tener dependencias a frameworks bases de datos o apis externas solo debe depender de sí mismo y del `core`
3.  **usa el lenguaje ubicuo** nombra las clases métodos y atributos utilizando la terminología del negocio para que el código sea auto-explicativo

### faqs o preguntas frecuentes
*   **puedo poner lógica de validación aquí**
    *   sí absolutamente las reglas de negocio y las validaciones son una responsabilidad clave de la capa de dominio
*   **cómo se comunica el dominio con el exterior**
    *   a través de interfaces (como los repositorios) y eventos de dominio el dominio define el "qué" se necesita y la `infraestructura` implementa el "cómo"

### referencias y recursos
*   `src/whisper_dictation/infrastructure/README.md` para ver cómo se implementan las interfaces de esta capa
*   [domain-driven design quickly (libro gratuito)](https://www.infoq.com/minibooks/domain-driven-design-quickly/) una introducción concisa a los conceptos de DDD
