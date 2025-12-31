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
CONFIG MANAGER SERVICE

Este servicio gestiona la lectura y escritura del archivo de configuración global `config.toml`.
Permite actualizaciones en tiempo real desde el frontend.

ADVERTENCIA:
    Modificar el archivo de configuración en caliente es una operación delicada.
    Este servicio asegura que se mantenga la estructura básica TOML.
"""

import toml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Gestor de configuración que permite leer y escribir `config.toml`.
    Actúa como una fachada para las operaciones de IO de configuración.
    """

    # SECCIONES PROTEGIDAS: No se pueden modificar via IPC por seguridad
    # paths: rutas del sistema (evita overwrites)
    PROTECTED_SECTIONS = {"paths"}

    def __init__(self, config_path: str = "config.toml") -> None:
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            # Resolve path relative to apps/backend directory (4 levels up from this file)
            # This ensures the daemon works regardless of the current working directory
            module_dir = Path(__file__).parent.parent.parent.parent
            self.config_path = module_dir / config_path

        logger.info("config manager initialized", extra={"path": str(self.config_path)})

    def load_config(self) -> Dict[str, Any]:
        """Lee la configuración actual del disco."""
        try:
            return toml.load(self.config_path)
        except Exception as e:
            logger.error(f"failed to load config from {self.config_path}", exc_info=True)
            raise

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Actualiza el archivo de configuración con nuevos valores.
        Realiza un merge profundo simple (sobrescribe claves existentes).

        Args:
            new_config: Diccionario parcial o completo con nuevas configuraciones.

        Raises:
            ValueError: Si new_config no es un diccionario válido o contiene secciones protegidas.
            Exception: Si falla la serialización TOML o escritura del archivo.
        """
        # Validar estructura básica antes de procesar
        if not isinstance(new_config, dict):
            raise ValueError("Config updates must be a dictionary")

        # SECURITY FIX: Validar que no se intenten modificar secciones protegidas
        self._validate_security(new_config)

        try:
            current_config = self.load_config()

            # Merge recursivo simple para no borrar secciones enteras si solo se manda una clave
            self._deep_update(current_config, new_config)

            # Validar que el resultado sea TOML serializable antes de escribir
            try:
                toml.dumps(current_config)
            except Exception as e:
                logger.error("updated config is not valid TOML, rolling back", exc_info=True)
                raise ValueError(f"Invalid TOML structure after merge: {e}")

            with open(self.config_path, "w") as f:
                toml.dump(current_config, f)

            logger.info("configuration updated successfully")

        except Exception as e:
            logger.error("failed to update config", exc_info=True)
            raise

    def _validate_security(self, updates: Dict[str, Any]) -> None:
        """
        Valida que las actualizaciones no violen políticas de seguridad.

        Args:
            updates: El diccionario de actualizaciones.

        Raises:
            ValueError: Si se detecta un intento de modificar secciones protegidas.
        """
        for section in updates.keys():
            if section in self.PROTECTED_SECTIONS:
                logger.warning(f"SECURITY: Attempted to update protected section '{section}'")
                raise ValueError(f"Security violation: Cannot update protected section '{section}' via IPC")

        # Validación adicional para path traversal en llm.local.model_path
        if "llm" in updates and "local" in updates["llm"]:
             local_config = updates["llm"]["local"]
             if "model_path" in local_config:
                 path_str = local_config["model_path"]
                 # Verificar path traversal básico
                 if ".." in path_str or path_str.startswith("/"):
                     logger.warning(f"SECURITY: Potential path traversal in model_path: {path_str}")
                     # Permitimos rutas absolutas solo si están en whitelist (opcional)
                     # Por ahora, bloqueamos todo lo que parezca sospechoso o fuera de models/
                     # Pero para ser estrictos, solo permitimos nombres de archivo o rutas relativas simples
                     # Ojo: el usuario podría querer poner un modelo en /mnt/data...
                     # Para este parche, bloqueamos '..'
                     if ".." in path_str:
                         raise ValueError("Security violation: Path traversal detected in model_path")

    def _deep_update(self, target: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza recursivamente un diccionario."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
        return target
