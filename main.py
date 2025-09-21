import os
import sys
import json
import requests
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

ws= OBSController()

LANGUAGE_TTS_COMBO = 'es'

# Variable global para indicar si la funcionalidad está habilitada o no
FUNCIONALIDAD_HABILITADA = {}
FUNCIONALIDAD_HABILITADA['cambio_scena']=False
RUTINAS_ACTIVAS = {}
is_on_obs = False

def descargar_clip_twitch(url, output_dir=r"C:\Users\daria\Desktop\clips"):
    """Descarga un clip de Twitch y retorna la ruta del archivo."""
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        "format": "mp4",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)  # ruta completa del archivo
    
def normalizar(texto: str) -> str:
    """Convierte a minúsculas, quita acentos y normaliza & -> and"""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto.lower().replace("&", "and").strip()

def update_twitch_category(broadcaster_id: str, category_name: str):
    """
    Busca el ID de una categoría usando /helix/search/categories
    y actualiza el canal con esa categoría.
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN_BROADCAST}",  # 👈 usa tu token con scope channel:manage:broadcast
        "Client-Id": CLIENT_ID_CLIP
    }

    # 1) Buscar la categoría por nombre
    search_url = f"https://api.twitch.tv/helix/search/categories?query={category_name}"
    resp = requests.get(search_url, headers=headers)

    if resp.status_code != 200:
        if resp.status_code == 401:
            new_access, new_refresh = refresh_tokens(REFRESH_TOKEN)
            if new_access:
            # actualiza variable global sin depender de .env
                globals()["ACCESS_TOKEN_BROADCAST"] = new_access
                globals()["REFRESH_TOKEN"] = new_refresh
                return update_twitch_category(broadcaster_id, category_name)  # reintenta SOLO una vez
        elif resp.status_code == 400:
            print(f"❌ Error 400 (Bad Request). Revisa el query o parámetros: {resp.text}")
        else:
            print(f"❌ Error buscando categoría: {resp.status_code} {resp.text}")
        return False

    data = resp.json().get("data", [])
    if not data:
        print(f"❌ No se encontró ninguna categoría con '{category_name}'")
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
        print(f"⚠️ '{category_name}' no coincidió exactamente. Usando '{real_name}' (ID={category_id})")

    # 4) PATCH para actualizar la categoría del canal
    patch_url = f"https://api.twitch.tv/helix/channels?broadcaster_id={broadcaster_id}"
    payload = {"game_id": category_id}

    resp = requests.patch(patch_url, headers=headers, json=payload)
    if resp.status_code == 204:
        print(f"✅ Categoría cambiada a: {real_name} (ID={category_id})")
        return True
    else:
        print(f"❌ Error al cambiar categoría: {resp.status_code} {resp.text}")
        return False


def obtener_clip(broadcaster_id: str, first: int = 5):
    
    try:
        url = f"https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}&first={first}"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN_BROADCAST}",#AUTHORIZATION_CLIP
            "Client-Id": CLIENT_ID_CLIP
        }
        resp = requests.get(url, headers=headers)
        data = resp.json().get("data", [])
        if not data:
            print("⚠️ No encontré clips recientes.")
            return None
        else:
            clip = random.choice(data)  # elige un clip aleatorio
            print("🎬 Clip seleccionado:")
            print(f"Título: {clip['title']}")
            print(f"URL: {clip['url']}")
            print(f"Duración: {clip['duration']}s")
            mp4_url = clip["thumbnail_url"].split("-preview-")[0] + ".mp4"
            return {
                "id": clip["id"],
                "title": clip.get("title", "Sin título"),
                "url": clip["url"],
                "embed_url": clip["embed_url"],
                "mp4": mp4_url,
                "duration": clip.get("duration", 30),
                "broadcaster": clip.get("broadcaster_name")
            }
    except Exception as e:
        print(f"[Clips] Error al obtener clip: {e}")
        return None


def obtener_juego_steam(steam_id: str, api_key: str) -> Optional[str]:
    """
    Consulta la API de Steam para ver si el steam_id está jugando algo.
    Devuelve el nombre del juego si está jugando (gameextrainfo), o None si no.
    """
    if not api_key or not steam_id:
        print(f"campos vacios de steam")
        return None
    try:
        url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={api_key}&steamids={steam_id}"
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            print(f"[Steam] Error en la solicitud: {resp.status_code}")
            return None
        data = resp.json()
        players = data.get('response', {}).get('players', [])
        if not players:
            return None
        player = players[0]
        # 'gameextrainfo' aparece solo si está en un juego
        juego = player.get('gameextrainfo')
        return juego  # puede ser string o None
    except Exception as e:
        print(f"[Steam] Excepción al consultar Steam: {e}")
        return None

def play_sound(file):
    pygame.mixer.init()
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()

# Determina la ruta correcta al archivo 'icon.ico' dependiendo de si el programa está empaquetado o no.
def resource_path(relative_path):
    try:
        # PyInstaller crea una carpeta temporal para las dependencias, así que este bloque ayuda a encontrar archivos dentro de esa carpeta.
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

def list_comandos_(self,routines):
    global FUNCIONALIDAD_HABILITADA

    comandos_list = list(self.commands.keys())
    
    for i in comandos_list:
        if i not in FUNCIONALIDAD_HABILITADA:
            FUNCIONALIDAD_HABILITADA[i] = True

# Decorador para habilitar o deshabilitar funciones
def comando_habilitable(nombre_comando: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):

            global FUNCIONALIDAD_HABILITADA

            if nombre_comando not in FUNCIONALIDAD_HABILITADA:
                FUNCIONALIDAD_HABILITADA[nombre_comando] = True

            if FUNCIONALIDAD_HABILITADA[nombre_comando]:
                return await func(*args, **kwargs)
            
            else:
                ctx = args[1] if len(args) > 1 else None
                if ctx:
                    await ctx.send(f"⚠️ El comando !{nombre_comando} está deshabilitado.")
                
                return
        return wrapper
    return decorator

def obtener_lang():
    global LANGUAGE_TTS_COMBO
    return LANGUAGE_TTS_COMBO

def enviar_imagen(url_imagen):
    url_servidor_flask = "http://localhost:5000/upload"  # Cambia la URL según la configuración de tu servidor Flask
    files = {'image': open(url_imagen, 'rb')}
    response = requests.post(url_servidor_flask, files=files)
    if response.status_code == 200:
        return response.text
    else:
        return f'Error al enviar la imagen al servidor Flask. Código de estado: {response.status_code}'

async def cambio_scena(self, name):
    print(ws.is_connected())
    if ws.is_connected():
        ws.change_scene(name)
    
def chanel_active():
    global CHANNEL
    canal_activo_data= CHANNEL
    CHANNEL = simpledialog.askstring("Canal", "Escriba el canal", initialvalue=canal_activo_data)
        
def data_raw_data():
    global data_raw
    data=data_raw.split(';')
    diccionario = {}
    for par in data:
        clave, valor = par.split('=')
        diccionario[clave] = valor
    return diccionario

async def texto_sin_emotes(self, ctx, mensaje_):
        diccionario = data_raw_data()
        emotes = diccionario['emotes'].split('/')
        diccionario_emotes = {}
        if len(emotes) == 1 and emotes[0]=='':
            return mensaje_
        
        for par in emotes:
            clave, valor = par.split(':')
            diccionario_emotes[clave] = valor

        ubicaciones_emotes=list(diccionario_emotes.values())
        ubicaciones_emotes.sort(key=lambda x: int(x.split('-')[0]))
        texto = mensaje_
        texto_sin_emotes = []
        inicio = 0

        for ubicacion in ubicaciones_emotes:
            if ubicacion.split(','):
                ubiseparados=ubicacion.split(',')
                for ubisep in ubiseparados:
                    ubi=ubisep.split('-')
                    ini=int(ubi[0])
                    fin=int(ubi[1])
                    texto_sin_emotes.append(texto[inicio:ini])
                    inicio = fin + 1

        texto_sin_emotes.append(texto[inicio:])
        resultado = ''.join(texto_sin_emotes)
        return resultado

def animacion_chat(texto):
    my_animation=animacion_chat_class.AnimacionImagenSonido(
        texto, 
        './noopaca_.png', 
        './opaca_.png', 
        obtener_lang())
    my_animation.reproducir_animacion()

def info_menssage(title,body):
    MessageBox.showinfo(title,body)

def listar_aplicaciones(): #considerar poner el if channel
    envio = 'just chatting'
    ventanas_abiertas = gw.getAllTitles()
    if ventanas_abiertas:
        for ventana in ventanas_abiertas:
            for juego in JUEGOS:
                if juego.rstrip().lstrip().lower() in ventana.lower():
                    if juego.rstrip().lstrip().lower() in 'unity':
                        envio='art'
                    elif juego.rstrip().lstrip().lower() in 'visual studio code':
                        envio='Software and Game Development'
                    else:
                        envio = juego.rstrip().lstrip().lower()
    return envio

async def get_game(self):
    channel = self.connected_channels
    if channel:
        information = await self.fetch_channel(broadcaster=CHANNEL)
        return information.game_name

def send_message_ds(text):
    mensaje = {
        'content': f'Se ha creado un clip y lo mas seguro es que esta chido, miralo aquí {text}'
    }
    mensaje_json = json.dumps(mensaje)
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(URL_WEBHOOK_DS, data=mensaje_json, headers=headers)

    if response.status_code == 200:
        print('Mensaje enviado con éxito!')
    else:
        print('Error al enviar el mensaje. Código de estado:', response.status_code, 'Respuesta del servidor:', response.text)

async def send_menssage(message,self):
    channel = self.connected_channels
    if channel:
        await channel[0].send(message)

async def info_comandos_funcion(self):
    channel = self.connected_channels
    if channel:
        global FUNCIONALIDAD_HABILITADA

        active_commands = [cmd for cmd, estado in FUNCIONALIDAD_HABILITADA.items() if estado]

        if active_commands:
            lista = ", ".join(f"!{cmd}" for cmd in active_commands)
            await send_menssage(f"✅ Comandos Activos: {lista}", self)
        else:
            await send_menssage("⚠️ No hay comandos activos actualmente.", self) #list(self.commands.keys())

@routines.routine(seconds=420)
async def info_comandos(self):
    await info_comandos_funcion(self)

@routines.routine(seconds=600)
async def info_streamer(self):  
    channel = self.connected_channels
    if channel:
        info=await self.fetch_channel(broadcaster=CHANNEL)
        await send_menssage(f'Informacion actual del Streamer: game -> {info.game_name}, titulo -> {info.title}',self)#delay -> {info.delay},

class PageBot:
    def __init__(self):
        # ruta absoluta hacia la carpeta templates
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
        self.app = Flask(__name__, template_folder=template_dir)

        self.app.add_url_rule('/', 'index', self.index, methods=["GET", "POST"])
        self.app.register_error_handler(404, self.pagina_no_encontrada)

    def run(self):
        # Debug y reloader desactivados porque va en un thread
        self.app.run(debug=False, use_reloader=False, port=5000)

    def index(self):
        global FUNCIONALIDAD_HABILITADA

        if request.method == "POST":
            for comando in FUNCIONALIDAD_HABILITADA.keys():
                FUNCIONALIDAD_HABILITADA[comando] = (comando in request.form)

        return render_template("comandos.html", comandos=FUNCIONALIDAD_HABILITADA)

    def pagina_no_encontrada(self, error):
        return redirect(url_for('index'))


class TwitchBotGUI:

    def __init__(self, root):
        self.root = root
        self.root.geometry('300x250')
        self.root.resizable(0,0)
        # Usar la función resource_path para obtener la ruta al icono
        ruta_icono = resource_path("icon.ico")
        #self.root.iconbitmap(ruta_icono)
        self.root.title("DariBot GUI")

        self.label = tk.Label(root, text="¡Bienvenido a Twitch Bot!")
        self.label.pack(pady=10)

        self.button_start_bot = tk.Button(root, text="Iniciar Bot", command=self.start_bot)
        self.button_start_bot.pack(pady=10)

        self.button_stop_bot = tk.Button(root, text="Detener Bot", command=self.stop_bot)
        self.button_stop_bot.pack(pady=10)
        #self.button_stop_bot.pack_forget()

        self.button_channel_bot = tk.Button(root, text="Asignar Canal", command=chanel_active)
        self.button_channel_bot.pack(pady=10)

        self.button_ = tk.Button(root, text="Info Comandos", command=self.list_comandos)
        self.button_.pack(pady=10)
        self.button_.config(state=tk.DISABLED)

        self.lang_list_label = tk.Label(root, text="Lang TTS Bot!")
        self.lang_list_label.place(x=10, y=220)
        lang_list=LANGUAGE_TTS.split(',')
        self.combo = ttk.Combobox(
                width=2,
                state="readonly",
                values=lang_list
                                )
        self.combo.set(lang_list)
        self.combo.bind("<<ComboboxSelected>>", self.selection_lang_changed)
        self.combo.place(x=10, y=200)

        self.bandera=True
        self.bot_thread = None
        self.bot_instance = None

        self.label_obs = tk.Label(root, 
        text = "Obs", 
        fg = "grey", 
        font = ("Helvetica", 12))
    
        self.label_obs.place(x=220, y=180)

        self.button_obs = tk.Button(root, bd = 5, text="off",
                   command = self.Switch)
        self.button_obs.place(x=230, y=200)

        #self.ws= OBSController()
    
    def Switch(self):
        global is_on_obs
        global FUNCIONALIDAD_HABILITADA
        
        if is_on_obs:
            self.button_obs.config(text= "Off")
            self.label_obs.config(text = "Obs Off", 
                            fg = "grey")
            is_on_obs = False

            ws.stop()

        else:
            if (ws.connect()):
                self.button_obs.config(text="On")
                self.label_obs.config(text = "Obs On", fg = "green")
                is_on_obs = True

    def selection_lang_changed(self, event):
        global LANGUAGE_TTS_COMBO
        LANGUAGE_TTS_COMBO = self.combo.get()

    def habilitar(self):
        self.button_start_bot.config(state=tk.NORMAL)
        self.button_start_bot.config(text="Detener Bot")

    def start_bot(self):
        #self.combo.config(state=tk.DISABLED)
        if self.bandera:
            self.bot_instance = Bot()
            self.bot_thread = Thread(target=self.bot_instance.run)
            self.bot_thread.daemon = True
            self.bandera=False
            try:
                self.bot_thread.start()
                self.button_start_bot.config(state=tk.DISABLED)
                self.button_channel_bot.config(state=tk.DISABLED)
                self.button_.config(state=tk.NORMAL)
            except KeyboardInterrupt:
                self.root.destroy()
                sys.exit()
        else: 
            self.root.destroy()
            sys.exit()

    def stop_bot(self):
            self.root.destroy()
            sys.exit()


    def callback(self, url):
        webbrowser.open_new(url)

    def list_comandos(self):#commands.keys()
        global FUNCIONALIDAD_HABILITADA

        if hasattr(self, "label_page") and self.label_page.winfo_exists():
            self.label_page.destroy()

        self.label_page = tk.Label(root, text="Page Comandos", fg="blue")
        self.label_page.pack()
        self.label_page.bind("<Button-1>", lambda e: self.callback("http://localhost:5000"))


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=ACCESS_TOKEN_SECRET, 
            prefix=(PREFIX), 
            initial_channels=[CHANNEL]
            )
        
        ws.start()
        print("init de bot" , ws.is_connected())

        @routines.routine(minutes=1)
        async def set_game():

            juego_steam = None
            try:
                juego_steam = obtener_juego_steam(STEAM_ID, STEAM_KEY)
            except Exception as e:
                print(f"Error al obtener juego desde Steam: {e}")

            if juego_steam:
                Juego_activo = juego_steam
            else:
                Juego_activo = listar_aplicaciones()
            Juego_actual = await get_game(self)
            scene = "Just Chatting" if ("Just Chatting").lower() == str(Juego_actual).lower() else "Juego"
            await cambio_scena(self,scene)
            if str(Juego_actual).lower() != Juego_activo.lower():
                info = await self.fetch_channel(broadcaster=CHANNEL)
                update_twitch_category(info.user.id, Juego_activo)
                #await send_menssage(f'{SET_GAME} {Juego_activo}',self)
                
        texto = '¿Desea habilitar el cambio de categoría automático? \n (Esta en versión de prueba)'
        enable_setgame = MessageBox.askokcancel("Habilitar", texto)
        if enable_setgame:
            set_game.start() 
        #info_comandos.start(self)

    async def event_ready(self):
        info = await self.fetch_channel(broadcaster=CHANNEL)        
        info_menssage('BOT Ready',f'Logged in as | {self.nick}\n'+
                f'User id is | {self.user_id}\n'+
                f'connected channels name is | {self.connected_channels[0].name}\n'+
                f'Connected channel id is | {info.user.id}')
        list_comandos_(self,routines)
        
    async def event_message(self, ctx):
        global data_raw
        data_raw = ctx.raw_data
        if unidecode(ctx.content[:4].lower()) in ['que ','khe','que','que?','khe?','khe ']:
            await ctx.channel.send(f'so :v')
        await self.handle_commands(ctx) #obligatoria

    async def event_error(self, error, data=None):
        pass
        print(f"Error: {error}")
     
    #no funciona porque solo detecta sub bits etc etc
    async def event_raw_usernotice(self, channel, tags):
        msg_id = tags.get("msg-id")

        if msg_id == "follow":
            usuario = tags.get("login")
            message = f"🎉 Gracias @{usuario} por dar follow"
            await channel.send(message)
            animacion_chat(message)
        return await super().event_raw_usernotice(channel, tags)

    async def close_bot(self):
        info_comandos.cancel()
        info_streamer.cancel()
        await self.close()
        info_menssage("Desconexión exitosa","Para Cerrar la Gui puede presionar el boton")
        app.habilitar()

    async def connect_bot(self):
        await self.connect()

    @commands.cooldown(rate=1, per=3600, bucket=commands.Bucket.user) #1 vez cada 3600seg por usuario
    @commands.command(aliases=['HOLA'])
    @comando_habilitable("hola")
    async def hola(self, ctx: commands.Context):
        await ctx.send(f'Hola {ctx.author.name}, espero que disfrutes del directo!')

    @commands.command(aliases=['GALLETA'])
    @comando_habilitable("galleta")
    async def galleta(self, ctx: commands.Context, user: twitchio.PartialChatter | None) -> None:
        if user is None:
            user = ctx.author
        await ctx.send(f'@{user.name} toma una galleta <3')

    @commands.cooldown(rate=1, per=60, bucket=commands.Bucket.channel) #1 vez cada 60seg por canal
    @commands.command(aliases=['KUAK','Kuak'])
    @comando_habilitable("kuak")
    async def kuak(self, ctx: commands.Context):
        await ctx.send(f'⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⠿⠿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿ ⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⣉⡥⠶⢶⣿⣿⣿⣿⣷⣆⠉⠛⠿⣿⣿⣿⣿⣿⣿⣿ ⣿⣿⣿⣿⣿⣿⣿⡿⢡⡞⠁⠀⠀⠤⠈⠿⠿⠿⠿⣿⠀⢻⣦⡈⠻⣿⣿⣿⣿⣿ ⣿⣿⣿⣿⣿⣿⣿⡇⠘⡁⠀⢀⣀⣀⣀⣈⣁⣐⡒⠢⢤⡈⠛⢿⡄⠻⣿⣿⣿⣿ ⣿⣿⣿⣿⣿⣿⣿⡇⠀⢀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣶⣄⠉⠐⠄⡈⢀⣿⣿⣿⣿ ⣿⣿⣿⣿⣿⣿⣿⠇⢠⣿⣿⣿⣿⡿⢿⣿⣿⣿⠁⢈⣿⡄⠀⢀⣀⠸⣿⣿⣿⣿ ⣿⣿⣿⣿⡿⠟⣡⣶⣶⣬⣭⣥⣴⠀⣾⣿⣿⣿⣶⣾⣿⣧⠀⣼⣿⣷⣌⡻⢿⣿ ⣿⣿⠟⣋⣴⣾⣿⣿⣿⣿⣿⣿⣿⡇⢿⣿⣿⣿⣿⣿⣿⡿⢸⣿⣿⣿⣿⣷⠄⢻ ⡏⠰⢾⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⢂⣭⣿⣿⣿⣿⣿⠇⠘⠛⠛⢉⣉⣠⣴⣾ ⣿⣷⣦⣬⣍⣉⣉⣛⣛⣉⠉⣤⣶⣾⣿⣿⣿⣿⣿⣿⡿⢰⣿⣿⣿⣿⣿⣿⣿⣿ ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⡘⣿⣿⣿⣿⣿⣿⣿⣿⡇⣼⣿⣿⣿⣿⣿⣿⣿⣿ ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⢸⣿⣿⣿⣿⣿⣿⣿⠁⣿⣿⣿⣿⣿⣿⣿⣿⣿')
        play_sound("kuak.wav")

    @commands.cooldown(rate=1, per=60, bucket=commands.Bucket.channel) #1 vez cada 60seg por canal
    @commands.command(aliases=['KIA'])
    @comando_habilitable("kia")
    async def kia(self, ctx: commands.Context):
        await ctx.send(f'⣿⣿⣷⡁⢆⠈⠕⢕⢂⢕⢂⢕⢂⢔⢂⢕⢄⠂⣂⠂⠆⢂⢕⢂⢕⢂⢕⢂⢕⢂ ⣿⣿⣿⡷⠊⡢⡹⣦⡑⢂⢕⢂⢕⢂⢕⢂⠕⠔⠌⠝⠛⠶⠶⢶⣦⣄⢂⢕⢂⢕ ⣿⣿⠏⣠⣾⣦⡐⢌⢿⣷⣦⣅⡑⠕⠡⠐⢿⠿⣛⠟⠛⠛⠛⠛⠡⢷⡈⢂⢕⢂ ⠟⣡⣾⣿⣿⣿⣿⣦⣑⠝⢿⣿⣿⣿⣿⣿⡵⢁⣤⣶⣶⣿⢿⢿⢿⡟⢻⣤⢑⢂ ⣾⣿⣿⡿⢟⣛⣻⣿⣿⣿⣦⣬⣙⣻⣿⣿⣷⣿⣿⢟⢝⢕⢕⢕⢕⢽⣿⣿⣷⣔ ⣿⣿⠵⠚⠉⢀⣀⣀⣈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣗⢕⢕⢕⢕⢕⢕⣽⣿⣿⣿⣿ ⢷⣂⣠⣴⣾⡿⡿⡻⡻⣿⣿⣴⣿⣿⣿⣿⣿⣿⣷⣵⣵⣵⣷⣿⣿⣿⣿⣿⣿⡿ ⢌⠻⣿⡿⡫⡪⡪⡪⡪⣺⣿⣿⣿⣿⣿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃ ⠣⡁⠹⡪⡪⡪⡪⣪⣾⣿⣿⣿⣿⠋⠐⢉⢍⢄⢌⠻⣿⣿⣿⣿⣿⣿⣿⣿⠏⠈ ⡣⡘⢄⠙⣾⣾⣾⣿⣿⣿⣿⣿⣿⡀⢐⢕⢕⢕⢕⢕⡘⣿⣿⣿⣿⣿⣿⠏⠠⠈ ⠌⢊⢂⢣⠹⣿⣿⣿⣿⣿⣿⣿⣿⣧⢐⢕⢕⢕⢕⢕⢅⣿⣿⣿⣿⡿⢋⢜⠠⠈ ⠄⠁⠕⢝⡢⠈⠻⣿⣿⣿⣿⣿⣿⣿⣷⣕⣑⣑⣑⣵⣿⣿⣿⡿⢋⢔⢕⣿⠠⠈ ⠨⡂⡀⢑⢕⡅⠂⠄⠉⠛⠻⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢋⢔⢕⢕⣿⣿⠠⠈ ⠄⠪⣂⠁⢕⠆⠄⠂⠄⠁⡀⠂⡀⠄⢈⠉⢍⢛⢛⢛⢋⢔⢔⢕⢕⢔⣿⣿⠠⠈')
        play_sound("yamete.wav")


    @commands.command(aliases=['OMG'])
    @comando_habilitable("omg")
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel) #1 vez cada 10seg por canal
    async def omg(self, ctx: commands.Context):
        await ctx.send(f'⣿⣿⣿⣿⣿⢟⡛⣍⢭⢩⡹⡛⢿⣿⡿⠿⣛⢩⡩⡩⡛⢿⣿⣿⣿⣿⣿⣿⣿⣿ ⣿⣿⡿⡫⡢⣷⢸⢜⢜⠜⠜⢎⢇⢆⠪⣪⢪⡪⡪⡎⡾⡆⣍⢻⣿⣿⣿⣿⣿⣿ ⣿⡟⡜⣜⠼⡘⡌⡖⣜⢜⡕⡖⣆⢅⡃⢑⢅⢭⡨⢬⢌⢎⣘⠠⠻⣿⣿⣿⣿⣿ ⡟⡜⣼⢸⢸⢪⢺⡸⡘⣬⣬⣶⣶⣶⣾⣬⣕⠱⣑⣥⣥⣵⣬⣭⣭⣌⠛⣿⣿⣿ ⠰⡱⡽⡸⡱⢙⣴⣶⣿⣿⣿⣿⡿⠋⠙⢻⣿⡎⣿⣿⣿⣿⣿⠟⠙⢻⣷⡌⣿⣿ ⡪⡪⡺⡸⡱⡱⡌⡛⠿⣿⣿⣿⣷⣭⣴⣿⡿⠱⣿⣿⣿⣿⣿⣧⣥⡾⠿⢇⣿⣿ ⡪⡪⣣⢫⢺⡸⡜⡬⡡⣂⢍⠍⡍⡍⡕⠐⡨⡰⣰⢰⡰⡰⡰⡔⣔⢌⣥⣾⣿⣿ ⡪⡪⡎⣎⢇⢇⢧⢳⢹⢰⢕⠵⣑⢡⢲⢩⡪⣪⢢⡁⢃⡩⣈⢬⠰⣿⣿⣿⣿⣿ ⡪⡪⡎⡮⡪⡣⡇⡗⡕⡇⡧⡳⡸⡪⡣⡣⡳⡱⡱⡍⡖⡼⡸⡸⡱⡘⣿⣿⣿⣿ ⡪⡪⡺⡸⣪⠺⡘⣈⢃⢋⠪⠎⠞⡜⣕⢝⡜⣕⢵⢱⡹⡸⡪⡣⠫⢒⠘⣿⣿⣿ ⡪⡪⣣⢫⠐⡜⡨⡐⡅⢕⢑⢑⢑⠆⠆⠆⠆⡬⡨⡡⡩⡨⡰⠰⢑⢡⣵⣿⣿⣿ ⡪⣪⢪⡘⢕⠤⠤⡤⢤⢡⢌⡊⣂⡑⠅⠣⠱⠐⠢⠢⠢⡒⡘⠜⢌⣸⣿⣿⣿⣿ ⠪⢪⢪⢎⢖⢭⢣⡣⣣⢣⡣⡣⡣⡪⡝⡍⡇⣏⢭⠣⢫⣨⣶⣾⣿⣿⣿⣿⣿⣿ ⢉⢒⠰⠤⢅⢇⡓⣑⢃⡓⣑⣙⣘⣊⢪⠺⢘⢈⢤⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿ ⢐⢐⢐⠔⡐⠀⠢⢐⢐⠠⠡⢂⠢⢐⠐⠌⡂⡂⡂⠌⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿')

    @commands.command(aliases=["UWU"])
    @comando_habilitable("uwu")
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel) #1 vez cada 10seg por canal
    async def uwu(self, ctx: commands.Context):
        await ctx.send(f'⡆⣐⢕⢕⢕⢕⢕⢕⢕⢕⠅⢗⢕⢕⢕⢕⢕⢕⢕⠕⠕⢕⢕⢕⢕⢕⢕⢕⢕⢕ ⢐⢕⢕⢕⢕⢕⣕⢕⢕⠕⠁⢕⢕⢕⢕⢕⢕⢕⢕⠅⡄⢕⢕⢕⢕⢕⢕⢕⢕⢕ ⢕⢕⢕⢕⢕⠅⢗⢕⠕⣠⠄⣗⢕⢕⠕⢕⢕⢕⠕⢠⣿⠐⢕⢕⢕⠑⢕⢕⠵⢕ ⢕⢕⢕⢕⠁⢜⠕⢁⣴⣿⡇⢓⢕⢵⢐⢕⢕⠕⢁⣾⢿⣧⠑⢕⢕⠄⢑⢕⠅⢕ ⢕⢕⠵⢁⠔⢁⣤⣤⣶⣶⣶⡐⣕⢽⠐⢕⠕⣡⣾⣶⣶⣶⣤⡁⢓⢕⠄⢑⢅⢑ ⠍⣧⠄⣶⣾⣿⣿⣿⣿⣿⣿⣷⣔⢕⢄⢡⣾⣿⣿⣿⣿⣿⣿⣿⣦⡑⢕⢤⠱⢐ ⢠⢕⠅⣾⣿⠋⢿⣿⣿⣿⠉⣿⣿⣷⣦⣶⣽⣿⣿⠈⣿⣿⣿⣿⠏⢹⣷⣷⡅⢐ ⣔⢕⢥⢻⣿⡀⠈⠛⠛⠁⢠⣿⣿⣿⣿⣿⣿⣿⣿⡀⠈⠛⠛⠁⠄⣼⣿⣿⡇⢔ ⢕⢕⢽⢸⢟⢟⢖⢖⢤⣶⡟⢻⣿⡿⠻⣿⣿⡟⢀⣿⣦⢤⢤⢔⢞⢿⢿⣿⠁⢕ ⢕⢕⠅⣐⢕⢕⢕⢕⢕⣿⣿⡄⠛⢀⣦⠈⠛⢁⣼⣿⢗⢕⢕⢕⢕⢕⢕⡏⣘⢕ ⢕⢕⠅⢓⣕⣕⣕⣕⣵⣿⣿⣿⣾⣿⣿⣿⣿⣿⣿⣿⣷⣕⢕⢕⢕⢕⡵⢀⢕⢕ ⢑⢕⠃⡈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢃⢕⢕⢕ ⣆⢕⠄⢱⣄⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⢁⢕⢕⠕⢁ ⣿⣦⡀⣿⣿⣷⣶⣬⣍⣛⣛⣛⡛⠿⠿⠿⠛⠛⢛⣛⣉⣭⣤⣂⢜⠕⢑⣡⣴⣿')
    
    @commands.command()
    @comando_habilitable("role")
    async def role(self, ctx:commands.Context):
        user_info= ctx.get_user(name=str(ctx.author.name))
        if user_info:
            print(user_info, ctx.channel,ctx.view.count, ctx.author.is_vip,ctx.author.is_mod)

    @commands.command()
    @comando_habilitable("enable")
    async def enable(self, ctx: commands.Context, nombre: str):
        global FUNCIONALIDAD_HABILITADA
        if ctx.author.is_mod:
            FUNCIONALIDAD_HABILITADA[nombre] = True
            await ctx.send(f"✅ El comando !{nombre} ha sido habilitado.")

    @commands.command()
    @comando_habilitable("disable")
    async def disable(self, ctx: commands.Context, nombre: str):
        global FUNCIONALIDAD_HABILITADA
        if ctx.author.is_mod:
            FUNCIONALIDAD_HABILITADA[nombre] = False
            await ctx.send(f"⛔ El comando !{nombre} ha sido deshabilitado.")

    @commands.command()
    @comando_habilitable("img1")
    async def img1(self, ctx:commands.Context):
        """# Lógica para obtener la URL de la imagen
        url_imagen = "https://pbs.twimg.com/media/F5XUBjTWQAALweU?format=jpg&name=large"  # Reemplaza con la ruta de tu imagen
        # Envia la imagen al servidor Flask y obtén la URL de la imagen
        url_flask = enviar_imagen(url_imagen)
        # Usa la URL obtenida para mostrar la imagen en OBS
        if url_flask:
            await ctx.send(f'Imagen enviada con éxito. URL: {url_flask}')
        else:
            await ctx.send('Error al enviar la imagen.')"""
        pass

    @commands.command()
    @comando_habilitable("img2")
    async def img2(self, ctx:commands.Context):
        """app_flask=MultimediaApp()
        app_flask.recargar_img()"""
        pass

    @commands.command(aliases=["S"])
    @comando_habilitable("s")
    async def s(self, ctx, amount):
        mensaje = await texto_sin_emotes(self, ctx, ctx.message.content)
        mytext = ctx.author.name+' dice '+ mensaje[3:153]
        animacion_chat(mytext)
    
    @commands.command(aliases=["CLIP"])
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel) #1 vez cada 10seg por canal
    @comando_habilitable("clip")
    async def clip(self, ctx:commands.Context):
        try:    
            #libreria twitchio
            info = await self.fetch_channel(broadcaster=CHANNEL)
            #con la api de twitch "post"
            url = f'https://api.twitch.tv/helix/clips?broadcaster_id={info.user.id}'
            headers = {
                'Authorization': f"Bearer {ACCESS_TOKEN_BROADCAST}",#AUTHORIZATION_CLIP
                'Client-Id': f"{CLIENT_ID_CLIP}"
                        }
            response = requests.post(url, headers=headers)
            if response:
                url_clip= response.json()["data"][0]['edit_url'][:-4]
                await ctx.send(f'El clip fue creado -> {url_clip}')
                send_message_ds(url_clip)
            else:
                await ctx.send(f'/me El clip no pudo ser creado')

        except requests.exceptions.RequestException as e:
            # Manejar excepciones de solicitudes HTTP
            print(f"Error en la solicitud HTTP: {e}")
            await ctx.send(f'/me Ocurrió un error al intentar crear el clip. Por favor, inténtalo nuevamente.')
            
    @commands.command(aliases=["SO"])
    @comando_habilitable("so")
    async def so(self, ctx: commands.Context, user: twitchio.PartialChatter | None) -> None:
        if ctx.author.is_mod:
            try:
                if user is None:
                    user = ctx.author

                info = await self.fetch_channel(broadcaster=user.name)
                await ctx.send(f'💜 Sigan a @{info.user.name} en https://www.twitch.tv/{info.user.name} '
                            f'¡Estaba jugando {info.game_name}!')

                clip = obtener_clip(info.user.id, first=10)
                if clip:
                    await ctx.send(f'🎬 Mira este clip: {clip["url"]}')
                    file_path=descargar_clip_twitch(clip["url"])
                    ws.set_media_source("ClipTwitch", file_path)
                    # Mostrar animación en ventana pygame
                    def mostrar():
                        anim = animacion_chat_class.AnimacionClip(clip["mp4"], clip["duration"])
                        anim.reproducir_clip()

                    #threading.Thread(target=mostrar, daemon=True).start()
                else:
                    await ctx.send(f'/me No encontré clips recientes de @{info.user.name}.')
            except Exception as e:
                print(f"[Clips] Error en !so: {e}")
                await ctx.send(f'/me Ocurrió un error al intentar mostrar un clip.')

    @commands.command()
    @comando_habilitable("salir")
    async def salir(self, ctx:commands.Context):
        if ctx.author.is_mod:
            await self.close_bot()

    @commands.command(aliases=["comandos","comando"])
    @comando_habilitable("coman2")
    async def coman2(self, ctx:commands.Context):
        await info_comandos_funcion(self)

if __name__ == "__main__":
    #ws= OBSController()
    root = tk.Tk()
    app = TwitchBotGUI(root)

    flask_app = PageBot()
    flask_thread = threading.Thread(target=flask_app.run, daemon=True)
    flask_thread.start()

    root.mainloop()