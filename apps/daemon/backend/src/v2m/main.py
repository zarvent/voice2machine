"""Punto de Entrada Principal para Voice2Machine (SOTA 2026).

Este módulo inicia el servidor FastAPI con Uvicorn, reemplazando el sistema
IPC manual basado en sockets Unix.

Modo de operación:
    - Servidor: `python -m v2m.main` → Inicia FastAPI en localhost:8765

Para desarrollo:
    uvicorn v2m.api.app:app --reload --host 127.0.0.1 --port 8765
"""

import argparse

from v2m.shared.logging import logger
from v2m.shared.utils.env import configure_gpu_environment

# Puerto por defecto para el servidor HTTP
DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"


def _setup_uvloop() -> None:
    """Configura uvloop como el bucle de eventos si está disponible.

    Optimiza el rendimiento de I/O asíncrono en sistemas *nix, proporcionando
    hasta 2-4x mejor throughput en operaciones de networking.

    Note:
        Solo tiene efecto en Linux/macOS. En Windows se ignora silenciosamente.
    """
    try:
        import uvloop

        uvloop.install()
        logger.debug("uvloop habilitado")
    except ImportError:
        pass


def _run_server(host: str, port: int) -> None:
    """Inicia el servidor FastAPI con Uvicorn.

    Args:
        host: Dirección IP o hostname para bind (ej. '127.0.0.1', '0.0.0.0').
        port: Puerto TCP para escuchar (ej. 8765).

    Note:
        El servidor se ejecuta en modo síncrono (blocking). Para desarrollo,
        use uvicorn directamente con --reload.
    """
    import uvicorn

    logger.info(f"🚀 Iniciando V2M Server en http://{host}:{port}")
    logger.info(f"📚 Documentación disponible en http://{host}:{port}/docs")

    uvicorn.run(
        "v2m.api.app:app",
        host=host,
        port=port,
        log_level="info",
        # Desactivar reload en producción - activar con --reload para desarrollo
    )


def main() -> None:
    """Función principal que inicia el servidor FastAPI."""
    parser = argparse.ArgumentParser(
        description="Voice2Machine - Transcripción de voz local con Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host para el servidor (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Puerto para el servidor (default: {DEFAULT_PORT})",
    )

    args = parser.parse_args()

    # Modo Servidor: iniciar FastAPI
    _setup_uvloop()
    configure_gpu_environment()
    _run_server(args.host, args.port)


if __name__ == "__main__":
    main()
