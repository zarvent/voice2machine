#!/usr/bin/env python3
"""
Ver modelos de Gemini disponibles

¿Para qué sirve?
    Te muestra todos los modelos de Gemini AI que puedes usar
    con tu API key. Útil para:
    - Verificar que tu API key funciona
    - Ver qué modelos tienes disponibles
    - Elegir qué modelo usar en config.toml

¿Cómo lo uso?
    $ python scripts/list_models.py

¿Qué voy a ver?
    Available models:
    models/gemini-1.5-pro        <- El más potente
    models/gemini-1.5-flash      <- Rápido y económico (recomendado)
    models/gemini-pro            <- Versión anterior

¿Qué modelo debería usar?
    Para V2M recomendamos gemini-1.5-flash:
    - Es rápido (importa para dictado)
    - Es económico (si pagas por uso)
    - Calidad suficiente para corrección de texto

¿Me sale error de API key?
    1. Verifica que tengas un archivo .env en la raíz del proyecto
    2. Que contenga: GEMINI_API_KEY=tu-clave-aqui
    3. Sin espacios alrededor del =
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv


def list_available_models() -> None:
    """
    Muestra los modelos de Gemini que puedes usar.

    Lee tu API key del archivo .env y consulta a Google qué modelos
    tienes disponibles. Solo muestra los que sirven para generar texto.
    """
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables.")
    else:
        genai.configure(api_key=api_key)
        print("Available models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)


if __name__ == "__main__":
    list_available_models()
