import torch
import os
import sys

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
    except Exception as e:
        print(f"❌ Error en operación cuDNN: {e}")
else:
    print("❌ CUDA no disponible")
