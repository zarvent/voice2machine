#!/usr/bin/env python3

# This file is part of voice2machine.
#
# voice2machine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# voice2machine is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with voice2machine.  If not, see <https://www.gnu.org/licenses/>.
"""
VERIFICACIÓN DE CUDA - ¿MI GPU FUNCIONA CON V2M?

¿PARA QUÉ SIRVE ESTE SCRIPT?
    v2m usa la gpu de tu computadora para transcribir audio rápidamente
    este script verifica que tu tarjeta gráfica nvidia esté configurada
    correctamente y lista para usar

¿CÓMO LO USO?
    simplemente ejecuta

    $ python scripts/check_cuda.py

¿QUÉ DEBERÍA VER SI TODO ESTÁ BIEN?
    python: /home/tu-usuario/v2m/venv/bin/python
    cuda available: true
    cuda device: nvidia geforce rtx 3060
    ✅ operación cudnn básica exitosa

¿QUÉ PASA SI CUDA NO ESTÁ DISPONIBLE?
    el script mostrará "cuda available: false" en ese caso

    1 verifica que tengas drivers nvidia instalados
       $ nvidia-smi

    2 si eso falla instala los drivers
       $ sudo apt install nvidia-driver-535

    3 si tienes drivers pero cuda sigue sin funcionar prueba
       $ ./scripts/repair_libs.sh

NOTA PARA DESARROLLADORES
    este script usa pytorch para detectar cuda y ejecuta una operación
    de convolución simple para verificar que cudnn funcione si la
    operación tiene éxito significa que todo el stack de gpu está
    funcionando correctamente
"""

import torch
import os
import sys


def check_cuda_availability() -> bool:
    """
    VERIFICA SI CUDA Y CUDNN ESTÁN FUNCIONANDO

    ¿QUÉ HACE EXACTAMENTE?
        1 muestra qué python estás usando
        2 muestra las rutas de librerías cuda
        3 prueba si cuda está disponible
        4 si lo está hace una prueba rápida con cudnn

    RETURNS
        true si todo funciona false si hay algún problema

    EXAMPLE
        >>> if check_cuda_availability():
        ...     print("listo para usar gpu")
        ... else:
        ...     print("usando cpu (más lento)")
    """
    print(f"python: {sys.executable}")
    print(f"ld_library_path: {os.environ.get('LD_LIBRARY_PATH', 'no establecido')}")
    print(f"cuda disponible: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"dispositivo cuda: {torch.cuda.get_device_name(0)}")
        try:
            # intentar cargar algo que use cudnn
            x = torch.randn(1, 1, 10, 10).cuda()
            conv = torch.nn.Conv2d(1, 1, 3).cuda()
            y = conv(x)
            print("✅ operación cudnn básica exitosa")
            return True
        except Exception as e:
            print(f"❌ error en operación cudnn: {e}")
            return False
    else:
        print("❌ cuda no disponible")
        return False


if __name__ == "__main__":
    check_cuda_availability()
