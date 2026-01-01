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

import logging
from pathlib import Path
from typing import Any

import toml

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Gestor de configuración que permite leer y escribir `config.toml`.
    Actúa como una fachada para las operaciones de IO de configuración.
    """

    def __init__(self, config_path: str = "config.toml") -> None:
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            # Resolve path relative to apps/backend directory (4 levels up from this file)
            # This ensures the daemon works regardless of the current working directory
            module_dir = Path(__file__).parent.parent.parent.parent
            self.config_path = module_dir / config_path

        logger.info("config manager initialized", extra={"path": str(self.config_path)})

    def load_config(self) -> dict[str, Any]:
        """Lee la configuración actual del disco."""
        try:
            return toml.load(self.config_path)
        except Exception:
            logger.error(f"failed to load config from {self.config_path}", exc_info=True)
            raise

    def update_config(self, new_config: dict[str, Any]) -> None:
        """
        Actualiza el archivo de configuración con nuevos valores.
        Realiza un merge profundo simple (sobrescribe claves existentes).

        SECURITY:
            - Bloquea actualizaciones a la sección [paths].
            - Valida rutas de archivos para evitar path traversal.

        Args:
            new_config: Diccionario parcial o completo con nuevas configuraciones.

        Raises:
            ValueError: Si new_config no es un diccionario válido o si se intenta modificar secciones protegidas.
            Exception: Si falla la serialización TOML o escritura del archivo.
        """
        # Validar estructura básica antes de procesar
        if not isinstance(new_config, dict):
            raise ValueError("Config updates must be a dictionary")

        # SECURITY CHECK 1: Bloquear acceso a sección 'paths'
        if "paths" in new_config:
            logger.warning("security violation: attempt to modify [paths] section")
            raise ValueError("Security violation: modification of [paths] section is not allowed")

        # SECURITY CHECK 2: Validar path traversal en llm.local.model_path
        if "llm" in new_config and "local" in new_config["llm"]:
             local_config = new_config["llm"]["local"]
             if "model_path" in local_config:
                 path_str = str(local_config["model_path"])

                 # Normalizar la ruta para resolver '..'
                 # Usamos os.path.normpath para resolver los '..' sintácticamente
                 import os
                 normalized_path = os.path.normpath(path_str)

                 # Verificar si contiene '..' después de normalizar (indica intento de salir del root)
                 has_traversal = ".." in normalized_path.split(os.sep)

                 # Bloquear rutas absolutas por defecto (política de seguridad estricta)
                 # Los modelos deben estar contenidos dentro del proyecto para portabilidad y seguridad
                 is_absolute = os.path.isabs(normalized_path)

                 if has_traversal or is_absolute:
                     logger.warning(f"security violation: unsafe model path '{path_str}' -> '{normalized_path}'")
                     raise ValueError("Security violation: model_path must be a relative path without traversal (use 'models/' directory)")

        try:
            current_config = self.load_config()

            # Backup del config actual para rollback en caso de error
            backup_config = current_config.copy()

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

        except Exception:
            logger.error("failed to update config", exc_info=True)
            raise

    def _deep_update(self, target: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        """Actualiza recursivamente un diccionario."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
        return target
