## 2025-10-18 - [Path Inseguro de Socket IPC]
**Vulnerability:** El archivo de socket IPC estaba hardcodeado a `/tmp/v2m.sock`.
**Learning:** Hardcodear rutas en `/tmp` es peligroso porque son predecibles y el directorio es world-writable, permitiendo ataques de denegación de servicio (si otro usuario crea el archivo primero) o potencial hijacking de conexión.
**Prevention:** Siempre usar `XDG_RUNTIME_DIR` o un subdirectorio en `/tmp` que incluya el UID del usuario y tenga permisos restrictivos (0700), resolviendo la ruta dinámicamente en tiempo de ejecución tanto en backend como en frontend.
