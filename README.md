# 🗣️ Whisper Dictation Tool

## 🎯 Purpose

This tool integrates audio transcription into your entire operating system. You can dictate text in any text field, regardless of the application. The system is designed to be efficient and fast.

## 🚀 New Architecture

This project has been refactored to follow modern software architecture best practices. The new architecture is based on a modular and configurable Python application, which offers the following advantages:

- **Separation of Concerns**: The application logic is separated from the user interface (keyboard shortcuts).
- **Centralized Configuration**: All application settings are managed in a single `config.toml` file, making it easy to customize.
- **Modularity**: The application is divided into reusable modules for transcription and language processing.
- **Maintainability**: The code is now more organized, easier to understand, and easier to maintain.

## 🛠️ Installation and Setup

### 1. System Dependencies

Before installing the application, make sure you have the following system dependencies installed:

- **ffmpeg**: For audio processing.
- **CUDA**: For GPU acceleration (optional, but recommended for better performance).
- **xclip**: For copying text to the clipboard.

You can use the `scripts/verify-setup.sh` script to check if these dependencies are installed.

### 2. Python Environment

It is recommended to use a virtual environment to install the Python dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

### 4. Configuration

All application settings are managed in the `config.toml` file. You can customize the following settings:

- **Paths**: Temporary file paths.
- **Whisper**: Whisper model settings (model, language, device, etc.).
- **Gemini**: Gemini API settings (model, temperature, etc.).

### 5. Environment Variables

If you want to use the optional AI processing with Gemini, you need to configure your Gemini API key in a `.env` file in the project root:

```
GEMINI_API_KEY="YOUR_API_KEY"
```

## 🕹️ Usage

The application is controlled by the `scripts/whisper-toggle.sh` script, which is intended to be triggered by a keyboard shortcut (e.g., `Ctrl+Shift+Space`).

- **Start Recording**: The first time you trigger the shortcut, it will start recording audio from your microphone.
- **Stop and Transcribe**: The second time you trigger the shortcut, it will stop the recording, transcribe the audio using Whisper, and copy the resulting text to the clipboard.

### Optional AI Processing

You can also process the text in your clipboard with Gemini. The `scripts/process-clipboard.sh` script is designed to be triggered by a second keyboard shortcut. It reads the content of the clipboard, sends it to Gemini for processing, and copies the improved text back to the clipboard.

## 🧠 Core of the System

- **Whisper**: The core of this system is OpenAI's Whisper model. We use `faster-whisper`, an optimized reimplementation for speed.
- **Gemini**: The system includes an intelligent text processor that uses the Google Gemini API to refine and improve the transcribed text.
- **Python Application**: The main logic is encapsulated in a Python application located in the `src` directory. The `whisper-toggle.sh` script acts as a simple interface to this application.

For more details on the new features, check the `archives` directory.
