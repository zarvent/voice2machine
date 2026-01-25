---
title: Changelog
description: Registro de cambios del proyecto Voice2Machine.
ai_context: "Versiones, Historial de Cambios, SemVer"
depends_on: []
status: stable
---

# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [0.2.0] - 2025-01-20

### Added

- **FastAPI REST API**: Nueva API HTTP que reemplaza el sistema IPC basado en Unix Sockets
- **WebSocket streaming**: Endpoint `/ws/events` para transcripción provisional en tiempo real
- **Documentación Swagger**: UI interactiva en `/docs` para probar endpoints
- **Orchestrator pattern**: Nuevo patrón de coordinación que simplifica el flujo de trabajo
- **Rust audio engine**: Extensión nativa `v2m_engine` para captura de audio de baja latencia
- **Sistema de documentación MkDocs**: Documentación estructurada con Material theme

### Changed

- **Arquitectura simplificada**: De CQRS/CommandBus a Orchestrator pattern más directo
- **Comunicación**: De Unix Domain Sockets binarios a HTTP REST estándar
- **Modelo de estado**: Gestión centralizada en `DaemonState` con lazy initialization
- Actualización de README.md con nueva arquitectura

### Removed

- `daemon.py`: Reemplazado por `api.py` (FastAPI)
- `client.py`: Ya no necesario, usar `curl` o cualquier cliente HTTP
- Protocolo IPC binario: Reemplazado por JSON estándar

### Fixed

- Latencia de arranque: El servidor inicia en ~100ms, modelo carga en background
- Memory leaks en WebSocket connections

## [0.3.0] - 2026-01-23

### Added

- **Arquitectura Basada en Features**: Reestructuración total hacia módulos autocontenidos en `features/` (audio, llm, transcription).
- **Orquestación mediante Workflows**: Introducción de `RecordingWorkflow` y `LLMWorkflow` para desacoplar la lógica de negocio del antiguo Orchestrator monolítico.
- **Protocolos Estrictos**: Implementación de `typing.Protocol` para todos los servicios internos, permitiendo swapping fácil de proveedores.
- **API Modular**: Estructura de paquetes en `api/` con rutas y esquemas separados.

### Changed

- **Eliminación de Orchestrator**: `services/orchestrator.py` ha sido descompuesto y eliminado.
- **Refactorización de Infraestructura**: La carpeta `infrastructure/` ha sido integrada dentro de cada `feature` correspondiente.
- **Core y Domain**: Simplificados y movidos a `shared/` e interfaces locales.

### Removed

- **Test de Audio Legacy**: Eliminación de pruebas obsoletas de la extensión Rust.
- **System Monitor**: Telemetría de sistema eliminada por simplificación del core.

## [Unreleased]

### Added

- **Detección de Alucinaciones**: Filtros heurísticos y parámetros de calidad (`no_speech`, `compression_ratio`) en `StreamingTranscriber` para reducir salidas erróneas en Whisper.
- **Métricas de Rendimiento**: Seguimiento de latencia de inferencia en logs para diagnóstico detallado.

### Changed

- **Optimización de VAD**: Ajuste del umbral por defecto a 0.4 para reducir falsos positivos por ruido ambiental y respiración.
- **Gestión de Memoria**: Reinicio forzado de la caché de CUDA (`torch.cuda.empty_cache()`) al descargar modelos para liberar VRAM de forma efectiva.
- **Higiene de Código**: Refactorización de imports y corrección de errores de linting (`ruff`) en toda la base de código del backend.

### Planned

- Soporte para múltiples idiomas de transcripción simultáneos
- Dashboard web para monitoreo en tiempo real
- Integración con más proveedores LLM

## [0.1.0] - 2024-03-20

### Added

- Versión inicial del sistema Voice2Machine
- Soporte para transcripción local con Whisper (faster-whisper)
- Integración básica con LLMs (Ollama/Gemini)
- Sistema IPC basado en Unix Domain Sockets
- Arquitectura hexagonal con puertos y adaptadores
- Configuración mediante TOML
