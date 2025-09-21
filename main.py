import os
import sys
import json
import requests
import logging
from config import LANGUAGE_TTS, URL_WEBHOOK_DS, CLIENT_SECRET, ACCESS_TOKEN_SECRET, CLIENT_ID_CLIP, PREFIX, CHANNEL, SET_GAME, JUEGOS, STEAM_KEY, STEAM_ID, ACCESS_TOKEN_BROADCAST, REFRESH_TOKEN
from typing import Optional
import twitchio
import webbrowser
import tkinter as tk
import pygame
from tkinter import messagebox, ttk, simpledialog
import pygetwindow as gw
import animacion_chat_class
import threading
from threading import Thread
from playsound import playsound
from unidecode import unidecode
from twitchio.ext import commands, routines
from tkinter import messagebox as MessageBox
from websocket_obs_class import OBSController
from flask import Flask, render_template, request, url_for, redirect, jsonify
from flask_mysqldb import MySQL
from functools import wraps
import unicodedata
import random
from auth import refresh_tokens
import yt_dlp

# Configuración del sistema de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),  # Guardar en archivo
        logging.StreamHandler()          # Mostrar en consola
    ]
)

ws= OBSController()

LANGUAGE_TTS_COMBO = 'es'

# Variable global para indicar si la funcionalidad está habilitada o no
FUNCIONALIDAD_HABILITADA = {}
FUNCIONALIDAD_HABILITADA['cambio_scena']=False
RUTINAS_ACTIVAS = {}
is_on_obs = False

def descargar_clip_twitch(url, output_dir=r"C:\Users\daria\Desktop\clips"):
    """Descarga un clip de Twitch y retorna la ruta del archivo."""
    logging.info(f"Descargando clip desde: {url}")
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        "format": "mp4",
        "outtmpl": os.path.join(output_dir, "%\(id\)s.\%(ext\)s"),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)  # ruta completa del archivo
            logging.info(f"Clip descargado exitosamente: {file_path}")
            return file_path
    except Exception as e:
        logging.error(f"Error al descargar clip: {e}")
        return None
    
def normalizar(texto: str) -> str:
    """Convierte a minúsculas, quita acentos y normaliza & -> and"""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto.lower().replace("&", "and").strip()

def update_twitch_category(broadcaster_id: str, category_name: str):
    """
    Busca el ID de una categoría usando /helix/search/categories
    y actualiza el canal con esa categoría.
    """
    logging.debug(f"Iniciando actualización de categoría: {category_name}")
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN_BROADCAST}",  # 👈 usa tu token con scope channel:manage:broadcast
        "Client-Id": CLIENT_ID_CLIP
    }

    # 1) Buscar la categoría por nombre
    search_url = f"https://api.twitch.tv/helix/search/categories?query={category_name}"
    resp = requests.get(search_url, headers=headers)

    if resp.status_code != 200:
        if resp.status_code == 401:
            logging.warning("Token expirado, intentando refrescar...")
            new_access, new_refresh = refresh_tokens(REFRESH_TOKEN)
            if new_access:
                globals()["ACCESS_TOKEN_BROADCAST"] = new_access
                globals()["REFRESH_TOKEN"] = new_refresh
                return update_twitch_category(broadcaster_id, category_name)  # reintenta SOLO una vez
        elif resp.status_code == 400:
            logging.error(f"Error 400 (Bad Request). Respuesta: {resp.text}")
        else:
            logging.error(f"Error al buscar categoría: {resp.status_code} {resp.text}")
        return False

    data = resp.json().get("data", [])
    if not data:
        logging.warning(f"No se encontró ninguna categoría con '{category_name}'")
        return False

    # 2) Intentar coincidencia exacta (ignorando mayúsculas/acentos/&)
    category_id, real_name = None, None
    category_norm = normalizar(category_name)

    for cat in data:
        if normalizar(cat["name"]) == category_norm:
            category_id = cat["id"]
            real_name = cat["name"]
            break

    # 3) Si no hay exacta → usar la primera sugerencia
    if not category_id:
        category_id = data[0]["id"]
        real_name = data[0]["name"]
        logging.info(f"'{category_name}' no coincidió exactamente. Usando '{real_name}' (ID={category_id})")

    # 4) PATCH para actualizar la categoría del canal
    patch_url = f"https://api.twitch.tv/helix/channels?broadcaster_id={broadcaster_id}"
    payload = {"game_id": category_id}

    resp = requests.patch(patch_url, headers=headers, json=payload)
    if resp.status_code == 204:
        logging.info(f"Categoría cambiada a: {real_name} (ID={category_id})")
        return True
    else:
        logging.error(f"Error al cambiar categoría: {resp.status_code} {resp.text}")
        return False

# Más funciones aquí con logs añadidos...

if __name__ == "__main__":
    logging.info("Iniciando aplicación Twitch Bot")
    root = tk.Tk()
    app = TwitchBotGUI(root)

    flask_app = PageBot()
    flask_thread = threading.Thread(target=flask_app.run, daemon=True)
    flask_thread.start()

    root.mainloop()