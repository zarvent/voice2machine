# CORE

### qué es esta carpeta
esta carpeta corresponde a la `capa core` de la arquitectura es el núcleo fundamental y transversal de la aplicación proporcionando componentes y herramientas que son utilizados por todas las demás capas

### para qué sirve
su propósito es centralizar la lógica y las abstracciones que no pertenecen a una capa específica pero que son esenciales para el funcionamiento del sistema esta capa no depende de ninguna otra (`domain` `application` `infrastructure`) pero las demás dependen de ella lo que la convierte en el pilar más estable de la arquitectura

### qué puedo encontrar aquí
*   `command bus` la implementación del bus de comandos que desacopla el envío de una acción de su ejecución (`CQRS`)
*   `dependency injection container` un contenedor para gestionar la creación y resolución de dependencias de manera centralizada
*   `custom exceptions` un conjunto de clases de excepción personalizadas para un manejo de errores más semántico y robusto
*   `logging` módulos para la configuración y el uso del sistema de logs
*   `abstracciones base` clases e interfaces fundamentales que definen contratos genéricos utilizados en toda la aplicación (eg `command_handler`)

### uso y ejemplos
los componentes de esta capa se utilizan como herramientas para construir las demás

*   **ejemplo de uso del `command bus`**
    ```python
    # desde la capa de aplicación en lugar de llamar a un servicio directamente
    command = IniciarGrabacionCommand(...)

    # se envía el comando al bus
    command_bus.dispatch(command)

    # el bus se encarga de encontrar y ejecutar el handler correspondiente
    ```

### cómo contribuir
1.  **identifica la necesidad** los componentes del `core` deben ser verdaderamente transversales si una funcionalidad solo es útil para una capa probablemente no pertenece aquí
2.  **prioriza la abstracción** el código en esta capa debe ser lo más genérico y abstracto posible
3.  **sin dependencias externas** el `core` no debe depender de ninguna otra capa del proyecto (`domain` `application` `infrastructure`)

### faqs o preguntas frecuentes
*   **por qué el `core` no depende del `dominio`**
    *   para mantenerlo lo más reutilizable y estable posible el `dominio` contiene la lógica de negocio específica de *esta* aplicación mientras que el `core` podría teóricamente ser reutilizado en otro proyecto
*   **puedo añadir librerías externas aquí**
    *   sí pero deben ser librerías de propósito general que actúen como herramientas fundamentales (eg una librería para inyección de dependencias)

### referencias y recursos
*   [inyección de dependencias (MARTIN FOWLER)](https://martinfowler.com/articles/injection.html) para entender el patrón de diseño que utiliza el contenedor
*   [command-query responsibility segregation (CQRS) (MARTIN FOWLER)](https://martinfowler.com/bliki/CQRS.html) para comprender el patrón del `command bus`
