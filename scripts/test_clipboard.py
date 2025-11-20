#!/usr/bin/env python3
"""
Test script para verificar que el clipboard funcione correctamente
desde el daemon.
"""
import sys
import os

# Añadir src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from v2m.infrastructure.linux_adapters import LinuxClipboardAdapter

def main():
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
