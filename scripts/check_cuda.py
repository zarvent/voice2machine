#!/usr/bin/env python3
"""
Script de verificación de CUDA y cuDNN para Voice2Machine (V2M).

Este módulo proporciona funcionalidades para verificar la disponibilidad
y correcto funcionamiento de CUDA y cuDNN en el sistema. Es fundamental
para asegurar que la aceleración por GPU esté disponible para la
transcripción con Whisper.

Ejemplo de uso:
    $ python scripts/check_cuda.py

    Salida esperada:
        Python: /path/to/python
        LD_LIBRARY_PATH: /path/to/libs
        CUDA Available: True
        CUDA Device: NVIDIA GeForce RTX 3060
        ✅ Operación cuDNN básica exitosa

Dependencias:
    - torch: Para verificar la disponibilidad de CUDA.
    - nvidia-cudnn-cu12: Librerías cuDNN para operaciones de convolución.

Notas:
    Si CUDA no está disponible, verifica:
    1. Que los drivers de NVIDIA estén instalados correctamente.
    2. Que LD_LIBRARY_PATH incluya las rutas a las librerías CUDA.
    3. Que las versiones de CUDA, cuDNN y PyTorch sean compatibles.

Author:
    Voice2Machine Team

Since:
    v1.0.0
"""

import torch
import os
import sys


def check_cuda_availability() -> bool:
    """
    Verifica la disponibilidad de CUDA y cuDNN en el sistema.

    Esta función realiza las siguientes verificaciones:
    1. Imprime información del entorno Python.
    2. Verifica si CUDA está disponible.
    3. Si CUDA está disponible, muestra el dispositivo y prueba cuDNN.

    Returns:
        bool: True si CUDA está disponible y cuDNN funciona correctamente,
              False en caso contrario.

    Raises:
        No lanza excepciones directamente, pero captura errores de cuDNN.

    Example:
        >>> check_cuda_availability()
        Python: /home/user/v2m/venv/bin/python
        LD_LIBRARY_PATH: /path/to/nvidia/libs
        CUDA Available: True
        CUDA Device: NVIDIA GeForce RTX 3060
        ✅ Operación cuDNN básica exitosa
        True
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
