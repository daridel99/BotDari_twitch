# 🎮 Twitch Bot con GUI, OBS y Animaciones TTS

## 📌 Descripción

Este proyecto implementa un **bot para Twitch** con interfaz gráfica
(Tkinter), integración con **OBS Studio** vía WebSocket y un sistema de
**animación con audio TTS**.

El bot permite: - Ejecutar comandos en el chat de Twitch. - Reproducir
animaciones de imagen y sonido basadas en mensajes del chat. - Cambiar
escenas de OBS automáticamente según la aplicación detectada. - Crear
clips de Twitch y enviar notificaciones a Discord. - Controlar comandos
mediante un panel web.

------------------------------------------------------------------------

## 🚀 Instalación

### 1. Clonar el repositorio

``` bash
git clone https://github.com/tu-repo/twitch-bot.git
cd twitch-bot
```

### 2. Crear entorno virtual

``` bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate    # Windows
```

### 3. Instalar dependencias

``` bash
pip install -r requirements.txt
```

### 4. Configuración

Crear un archivo `.env` con tus credenciales:

``` env
ACCESS_TOKEN_SECRET=tu_token_twitch
Client-Id_clip=tu_client_id
Authorization_clip=tu_auth_clip
URL_webhook_DS=https://discordapp.com/api/webhooks/...
```

Además, un archivo `setting.txt` en JSON con:

``` json
{
  "prefix": "!",
  "channel": "tunombrecanal",
  "games": "just chatting,unity,visual studio code",
  "lenguage_tts": "es,en",
  "set_game": "/setgame",
  "port_obs": 4455,
  "psd_obs": "tu_password_obs"
}
```

------------------------------------------------------------------------

## ▶️ Uso

Ejecutar:

``` bash
python main.py
```

1.  Aparecerá la GUI (Tkinter).
2.  Puedes iniciar/detener el bot y conectarlo a OBS.
3.  El panel web estará en `http://localhost:5000`.

------------------------------------------------------------------------

## 📜 Comandos del bot

Ejemplos: - `!hola` → Saluda al usuario. - `!galleta` → Regala una
galleta virtual. - `!kuak`, `!kia`, `!omg`, `!uwu` → Reproducen
sonidos/ASCII art. - `!s <texto>` → Convierte texto a animación TTS. -
`!clip` → Crea un clip en Twitch y lo manda a Discord. - `!enable <cmd>`
/ `!disable <cmd>` → Habilita o deshabilita comandos.

------------------------------------------------------------------------

## 🛠️ Tecnologías

-   **Python 3.11+**
-   [twitchio](https://twitchio.dev/)\
-   Flask + Tkinter\
-   OBS WebSocket (`obs-websocket-py`)\
-   gTTS, Librosa, Pygame, Pydub\
-   Discord Webhooks

------------------------------------------------------------------------

## 📌 Autores

Proyecto desarrollado por **DariBot** ✨
