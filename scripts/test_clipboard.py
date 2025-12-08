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
prueba del portapapeles - ¿ctrl+v funciona desde v2m?

¿por qué es importante?
    v2m copia automáticamente las transcripciones al portapapeles
    si esto no funciona aunque transcribas bien no podrás pegar

¿cómo lo uso?
    $ python scripts/test_clipboard.py

¿qué debería ver?
    🧪 probando linuxclipboardadapter...
    📋 copiando: hola mundo desde el daemon de v2m! 🚀
    📋 leyendo del clipboard...
    ✅ éxito: hola mundo desde el daemon de v2m! 🚀

¿qué pasa si falla?
    1 verifica que tengas xclip instalado
       $ sudo apt install xclip

    2 verifica que estés en una sesión con display
       $ echo $DISPLAY
       (debería mostrar algo como :0 o :1)

    3 si estás por ssh necesitas x forwarding
       $ ssh -X usuario@servidor

para desarrolladores
    este script usa el linuxclipboardadapter del módulo infrastructure
    ese adaptador internamente usa xclip para las operaciones de
    clipboard si xclip no está disponible intenta con xsel
"""

import sys
import os

# Añadir src al path para importar los módulos de V2M
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from v2m.infrastructure.linux_adapters import LinuxClipboardAdapter


def main() -> int:
    """
    Prueba que el portapapeles funcione.

    Copia un texto, lo lee de vuelta, y verifica que sean iguales.

    Returns:
        0 si todo bien, 1 si falló.

    Example:
        >>> exit_code = main()
        >>> print(f"Prueba {'exitosa' if exit_code == 0 else 'fallida'}")
    """
    print("🧪 Probando LinuxClipboardAdapter...")

    clipboard = LinuxClipboardAdapter()

    # Test 1: Copiar
    test_text = "Hola mundo desde el daemon de v2m! 🚀"
    print(f"\n📋 Copiando: {test_text}")
    clipboard.copy(test_text)

    # Test 2: Pegar
    print("\n📋 Leyendo del clipboard...")
    result = clipboard.paste()

    if result == test_text:
        print(f"✅ SUCCESS: {result}")
        return 0
    else:
        print(f"❌ FAIL: Se esperaba '{test_text}', se obtuvo '{result}'")
        return 1


if __name__ == "__main__":
    sys.exit(main())
