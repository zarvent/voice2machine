este proyecto te proporciona una herramienta de dictado por voz

su propósito es integrar la transcripción de audio en todo tu sistema operativo

puedes dictar texto en cualquier campo de escritura sin importar la aplicación

el sistema está diseñado para ser eficiente y rápido

para interactuar con el sistema utilizas un único atajo de teclado

control mayúsculas y espacio

al presionarlo por primera vez se inicia la grabación de audio desde tu micrófono

al presionarlo de nuevo la grabación se detiene y comienza el proceso de transcripción

el texto resultante se copia automáticamente a tu portapapeles

luego puedes pegarlo en cualquier lugar con control v

el núcleo de este sistema es el modelo de lenguaje whisper de openai

específicamente se utiliza faster-whisper una reimplementación optimizada para velocidad

el script principal whisper-toggle.sh gestiona el estado de la grabación

crea un archivo temporal para saber si está grabando o no

al detener la grabación este script invoca un proceso de python

este proceso carga el modelo whisper en la gpu utilizando la tecnología cuda

la computación se realiza en float16 para maximizar el rendimiento en tarjetas rtx

puedes verificar la correcta aceleración de tu gpu con el script test_whisper_gpu

una vez transcrito el texto el script utiliza la utilidad xclip para copiarlo al portapapeles

antes de usarlo por primera vez el script verify-setup te ayuda a diagnosticar el sistema

revisa que todas las dependencias como ffmpeg cuda y xclip estén instaladas

así puedes asegurar que el entorno está configurado correctamente para su operación
