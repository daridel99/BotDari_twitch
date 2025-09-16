# 📘 Manual Técnico - Twitch Bot con OBS y TTS

## 1. Arquitectura del Proyecto

El sistema se divide en varios módulos:

-   **main.py** → Punto de entrada, lógica central del bot, GUI y Flask.
-   **animacion_chat_class.py** → Generación de audio TTS + animación
    con imágenes.
-   **websocket_obs_class.py** → Control de OBS (cambiar escenas,
    conexión).
-   **config.py** → Manejo de configuración y credenciales.

```{=html}
<!-- -->
```
    +------------------+       +--------------------+
    |   Twitch Chat    | <---> |   Bot (twitchio)   |
    +------------------+       +--------------------+
                                     |
             +-----------------------+----------------------+
             |                       |                      |
    +-------------------+   +------------------+   +-------------------+
    | Flask Web (comms) |   | Tkinter GUI      |   | OBS Controller    |
    +-------------------+   +------------------+   +-------------------+
                                                        |
                                                  +-------------+
                                                  | OBS Studio  |
                                                  +-------------+

------------------------------------------------------------------------

## 2. Flujo General

1.  Usuario inicia la GUI (Tkinter).
2.  Se levanta un **thread paralelo con Flask** (panel web de comandos).
3.  El bot se conecta a Twitch (twitchio).
4.  Eventos del chat activan:
    -   Animaciones TTS (`animacion_chat_class`).
    -   Mensajes automáticos.
    -   Creación de clips y envío a Discord.
    -   Cambios de escena en OBS (`websocket_obs_class`).

------------------------------------------------------------------------

## 3. Dependencias Clave

-   **twitchio** → conexión y comandos en Twitch.
-   **pygame** → animación de imágenes y reproducción de audio.
-   **gTTS + librosa** → generación de voz y análisis de audio.
-   **obs-websocket-py** → integración con OBS Studio.
-   **Flask** → panel web de comandos.
-   **Tkinter** → interfaz gráfica del bot.

------------------------------------------------------------------------

## 4. Configuración

-   Variables sensibles en `.env` (tokens y webhooks).
-   Parámetros adicionales en `setting.txt` (canal, juegos, TTS, OBS).

------------------------------------------------------------------------

## 5. Seguridad

-   Nunca exponer `ACCESS_TOKEN_SECRET` en repositorios públicos.
-   Reemplazar `setting.txt` por base de datos segura en producción.

------------------------------------------------------------------------

## 6. Mejoras Propuestas 🚀

-   Reestructurar proyecto en paquetes (`bot/`, `gui/`, `web/`, `obs/`,
    `tts/`).
-   Implementar **logging rotativo** en lugar de `print`.
-   Mejorar GUI con **PyQt** o migrar panel web a **FastAPI + React**.
-   Integrar más alertas de Twitch (suscripciones, raids, donaciones).
-   Persistir estadísticas en base de datos (PostgreSQL/MongoDB).
-   Añadir sistema de roles/permisos para comandos.

------------------------------------------------------------------------

## 7. Diagramas de Flujo Simplificados

### Flujo de Mensaje en Twitch

    Usuario → Chat Twitch → Bot (event_message) →
      ├─> Comando normal → respuesta en chat
      ├─> !s → animación TTS (pygame)
      └─> !clip → crea clip (API Twitch) → envía link a Discord

### Flujo de OBS

    Tkinter GUI → OBSController → OBS Studio
        │
        └─> Cambiar escena según app detectada

------------------------------------------------------------------------

## 8. Requerimientos del Sistema

-   Python 3.11+
-   OBS Studio con plugin WebSocket habilitado.
-   Conexión a Internet estable (para Twitch, Discord y TTS).
