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
voice2machine (v2m) - sistema de dictado por voz para linux

este paquete proporciona una solución completa de dictado por voz que convierte
audio en texto utilizando el modelo whisper de openai ejecutándose localmente en gpu
opcionalmente el texto puede ser refinado mediante un modelo de lenguaje grande (llm)
como google gemini

arquitectura
    el proyecto sigue una arquitectura limpia basada en el patrón cqrs
    (command query responsibility segregation) con inyección de dependencias

    - **core/** interfaces protocolos ipc y el bus de comandos (cqrs)
    - **application/** casos de uso y servicios de aplicación (handlers)
    - **domain/** errores de dominio y entidades del negocio
    - **infrastructure/** implementaciones concretas (whisper gemini linux)

componentes principales
    - **daemon** proceso persistente que mantiene el modelo whisper en memoria
    - **client** cliente cli que envía comandos al daemon vía socket unix
    - **audiorecorder** captura de audio usando sounddevice
    - **whispertranscriptionservice** transcripción con faster-whisper
    - **geminillmservice** refinamiento de texto con google gemini

flujo típico de uso
    1 el usuario presiona un atajo de teclado global
    2 el script bash envía ``START_RECORDING`` al daemon
    3 el daemon comienza a capturar audio del micrófono
    4 al presionar el atajo nuevamente se envía ``STOP_RECORDING``
    5 el audio es transcrito con whisper y copiado al portapapeles

ejemplo
    iniciar el daemon::

        python -m v2m.main --daemon

    enviar comandos desde otro proceso::

        python -m v2m.main START_RECORDING
        python -m v2m.main STOP_RECORDING

notas
    - requiere linux con x11 o wayland
    - requiere xclip o wl-clipboard para el portapapeles
    - requiere notify-send para notificaciones
    - gpu nvidia con cuda recomendada para mejor rendimiento

versión 1.0.0
autor zarvent
licencia mit
"""

__version__ = "1.0.0"
__author__ = "zarvent"
__license__ = "MIT"

# Exportaciones públicas del paquete
__all__ = [
    "__version__",
    "__author__",
    "__license__",
]
