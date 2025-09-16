import os
import json
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()

# --- Cargar setting.txt ---
datos_secretos = {}
try:
    with open('./setting.txt', 'r', encoding='utf-8') as archivo:
        datos_secretos = json.loads(archivo.read())
except FileNotFoundError:
    print("⚠️ Archivo setting.txt no encontrado. Usando valores por defecto.")
except json.JSONDecodeError as e:
    print(f"⚠️ Error leyendo setting.txt: {e}. Usando valores por defecto.")

# --- Variables de entorno ---
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
CLIENT_ID_CLIP = os.getenv('CLIENT_ID')  # <- corregido mayúsculas
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
AUTHORIZATION_CLIP = os.getenv('AUTHORIZATION_CLIP')  # <- corregido mayúsculas
URL_WEBHOOK_DS = os.getenv('URL_WEBHOOK_DS')
STEAM_KEY = os.getenv('STEAM_CLAVE') 

# --- Variables desde settings (con fallback) ---
PREFIX = datos_secretos.get('prefix', '!')
CHANNEL = datos_secretos.get('channel', 'daridel_99')
JUEGOS = datos_secretos.get("games", "just chatting").split(',')
LANGUAGE_TTS = datos_secretos.get('lenguage_tts', 'es,en,fr,de,it,ja,pt,ru')
SET_GAME = datos_secretos.get('set_game', '!setgame')
STEAM_ID = datos_secretos.get('steam_id','')
PORT_OBS = datos_secretos.get('port_obs', 4455)
PSD_OBS = datos_secretos.get('psd_obs', '')