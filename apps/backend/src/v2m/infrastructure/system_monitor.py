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
SYSTEM MONITOR SERVICE

Este servicio se encarga de recolectar métricas del sistema en tiempo real.
Utiliza psutil para obtener estadísticas de CPU y RAM, y métodos específicos
para métricas de GPU si están disponibles.

Se adhiere al principio de "Single Responsibility" proveyendo solo datos de observación.
"""

import logging
from types import ModuleType
from typing import Any

import psutil

logger = logging.getLogger(__name__)

class SystemMonitor:
    """
    Monitor de recursos del sistema para observabilidad en tiempo real.
    Provee métricas de RAM, CPU y GPU (si está disponible).
    """

    def __init__(self) -> None:
        # OPTIMIZACIÓN BOLT: Cachear módulo torch para evitar importación repetida
        self._torch: ModuleType | None = None
        self._gpu_available = self._check_gpu_availability()

        # OPTIMIZACIÓN BOLT: Cachear métricas estáticas (Total RAM, GPU Name)
        # Esto evita syscalls y llamadas a driver redundantes en cada polling (500ms)
        try:
            mem = psutil.virtual_memory()
            self._ram_total_gb = round(mem.total / (1024**3), 2)
        except Exception as e:
            logger.warning(f"failed to cache ram info: {e}")
            self._ram_total_gb = 0.0

        self._gpu_static_info: dict[str, Any] = {}
        if self._gpu_available and self._torch:
            try:
                device = self._torch.cuda.current_device()
                props = self._torch.cuda.get_device_properties(device)
                self._gpu_static_info = {
                    "name": props.name,
                    "vram_total_mb": round(props.total_memory / (1024 ** 2), 2)
                }
            except Exception as e:
                logger.warning(f"failed to cache gpu info: {e}")
                self._gpu_available = False

        logger.info("system monitor initialized", extra={
            "gpu_available": self._gpu_available,
            "ram_total_gb": self._ram_total_gb
        })

    def _check_gpu_availability(self) -> bool:
        """Verifica si hay una GPU NVIDIA disponible via torch.cuda."""
        try:
            import torch
            # OPTIMIZACIÓN BOLT: Guardar referencia al módulo para reuso en polling
            self._torch = torch
            return torch.cuda.is_available()
        except ImportError:
            logger.warning("torch not available, GPU monitoring disabled")
            return False
        except Exception as e:
            logger.warning(f"failed to check GPU availability: {e}")
            return False

    def get_system_metrics(self) -> dict[str, Any]:
        """
        Obtiene una instantánea de las métricas actuales del sistema.

        Returns:
            Dict con claves 'ram', 'cpu', 'gpu' (opcional)
        """
        metrics = {
            "ram": self._get_ram_usage(),
            "cpu": self._get_cpu_usage(),
        }

        if self._gpu_available:
            metrics["gpu"] = self._get_gpu_usage()

        return metrics

    def _get_ram_usage(self) -> dict[str, float]:
        """Retorna uso de memoria RAM en GB y porcentaje."""
        mem = psutil.virtual_memory()
        return {
            "total_gb": self._ram_total_gb, # Usar valor cacheado
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent
        }

    def _get_cpu_usage(self) -> dict[str, Any]:
        """Retorna uso de CPU global."""
        return {
            "percent": psutil.cpu_percent(interval=None)
        }

    def _get_gpu_usage(self) -> dict[str, Any]:
        """
        Retorna uso real de GPU usando torch.cuda.

        Returns:
            Dict con métricas de GPU: name, vram_used_mb, vram_total_mb, temp_c
        """
        try:
            # OPTIMIZACIÓN BOLT: Usar referencia cacheada self._torch
            # Evita búsqueda en sys.modules cada 500ms
            if not self._torch or not self._torch.cuda.is_available():
                return {"name": "N/A", "vram_used_mb": 0, "vram_total_mb": 0, "temp_c": 0}

            device = self._torch.cuda.current_device()
            # Usar estáticos cacheados
            static = self._gpu_static_info

            # VRAM metrics en MB (Dinámico)
            vram_reserved = self._torch.cuda.memory_reserved(device) / (1024 ** 2)

            return {
                "name": static.get("name", "Unknown"),
                "vram_used_mb": round(vram_reserved, 2),
                "vram_total_mb": static.get("vram_total_mb", 0),
                "temp_c": 0  # torch no expone temperatura, requiere pynvml
            }
        except Exception as e:
            logger.error(f"failed to get GPU metrics: {e}", exc_info=True)
            return {"name": "Error", "vram_used_mb": 0, "vram_total_mb": 0, "temp_c": 0}
