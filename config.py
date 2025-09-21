import os
import json
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()

# --- Configuración logging ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,  # cambia a DEBUG para más detalle
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # consola
        RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    ]
)

# Ejemplo de logger de configuración
logger = logging.getLogger("config")

# --- Cargar setting.txt ---
datos_secretos = {}
try:
    with open('./setting.txt', 'r', encoding='utf-8') as archivo:
        datos_secretos = json.loads(archivo.read())
except FileNotFoundError:
    logger.warning("Archivo setting.txt no encontrado. Usando valores por defecto.")
except json.JSONDecodeError as e:
    logger.warning(f"Error leyendo setting.txt: {e}. Usando valores por defecto.")

# --- Variables de entorno ---
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
CLIENT_ID_CLIP = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
URL_WEBHOOK_DS = os.getenv('URL_WEBHOOK_DS')
STEAM_KEY = os.getenv('STEAM_CLAVE')
ACCESS_TOKEN_BROADCAST = os.getenv('ACCESS_TOKEN_BROADCAST')
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# --- Variables desde settings (con fallback) ---
PREFIX = datos_secretos.get('prefix', '!')
CHANNEL = datos_secretos.get('channel', 'daridel_99')
JUEGOS = datos_secretos.get("games", "just chatting").split(',')
LANGUAGE_TTS = datos_secretos.get('lenguage_tts', 'es,en,fr,de,it,ja,pt,ru')
SET_GAME = datos_secretos.get('set_game', '!setgame')
STEAM_ID = datos_secretos.get('STEAM_ID','')
PORT_OBS = datos_secretos.get('port_obs', 4455)
PSD_OBS = datos_secretos.get('psd_obs', '')