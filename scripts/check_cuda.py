#!/usr/bin/env python3
"""
Verificación de CUDA - ¿Mi GPU funciona con V2M?

¿Para qué sirve este script?
    V2M usa la GPU de tu computadora para transcribir audio rápidamente.
    Este script verifica que tu tarjeta gráfica NVIDIA esté configurada
    correctamente y lista para usar.

¿Cómo lo uso?
    Simplemente ejecuta:

    $ python scripts/check_cuda.py

¿Qué debería ver si todo está bien?
    Python: /home/tu-usuario/v2m/venv/bin/python
    CUDA Available: True
    CUDA Device: NVIDIA GeForce RTX 3060
    ✅ Operación cuDNN básica exitosa

¿Qué pasa si CUDA no está disponible?
    El script mostrará "CUDA Available: False". En ese caso:

    1. Verifica que tengas drivers NVIDIA instalados:
       $ nvidia-smi

    2. Si eso falla, instala los drivers:
       $ sudo apt install nvidia-driver-535

    3. Si tienes drivers pero CUDA sigue sin funcionar, prueba:
       $ ./scripts/repair_libs.sh

Nota para desarrolladores:
    Este script usa PyTorch para detectar CUDA y ejecuta una operación
    de convolución simple para verificar que cuDNN funcione. Si la
    operación tiene éxito, significa que todo el stack de GPU está
    funcionando correctamente.
"""

import torch
import os
import sys


def check_cuda_availability() -> bool:
    """
    Verifica si CUDA y cuDNN están funcionando.

    ¿Qué hace exactamente?
        1. Muestra qué Python estás usando
        2. Muestra las rutas de librerías CUDA
        3. Prueba si CUDA está disponible
        4. Si lo está, hace una prueba rápida con cuDNN

    Retorna:
        True si todo funciona, False si hay algún problema.

    Ejemplo:
        >>> if check_cuda_availability():
        ...     print("Listo para usar GPU")
        ... else:
        ...     print("Usando CPU (más lento)")
    """
    print(f"Python: {sys.executable}")
    print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'Not Set')}")
    print(f"CUDA Available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
        try:
            # Intentar cargar algo que use cuDNN
            x = torch.randn(1, 1, 10, 10).cuda()
            conv = torch.nn.Conv2d(1, 1, 3).cuda()
            y = conv(x)
            print("✅ Operación cuDNN básica exitosa")
            return True
        except Exception as e:
            print(f"❌ Error en operación cuDNN: {e}")
            return False
    else:
        print("❌ CUDA no disponible")
        return False


if __name__ == "__main__":
    check_cuda_availability()
