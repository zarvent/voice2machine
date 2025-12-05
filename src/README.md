# código fuente

este directorio contiene todo el código fuente de la aplicación voice2machine organizado como un paquete de python estándar

estructura
- `v2m/` paquete principal de la aplicación

uso
para ejecutar la aplicación desde el código fuente se recomienda usar los scripts en el directorio `scripts/` o ejecutar el módulo directamente asegurándose de que `PYTHONPATH` incluya este directorio

ejemplo
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 -m v2m.main --daemon
```
