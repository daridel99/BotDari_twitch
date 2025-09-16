from gtts import gTTS
import pygame
from pydub import AudioSegment
from pathlib import Path
import numpy as np
import librosa
from tkvideo import tkvideo
import imageio_ffmpeg as ffmpeg  # instalar: pip install imageio-ffmpeg
import tkinter as tk
from librosa.feature import zero_crossing_rate
import soundfile as sf
import time
from os import remove
from config import LANGUAGE_TTS
import win32gui
import win32con  # pywin32 para manejar la ventana

# Función para obtener rutas absolutas, compatible con PyInstaller
def resource_path(relative_path):
    import sys, os
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)


class AnimacionImagenSonido:
    def __init__(self, mytext, image_file_no, image_file_si, idioma_tts):
        self.mytext = mytext
        self.audio_path = Path(resource_path('example.mp3'))
        self.image_file_no = Path(resource_path(image_file_no))
        self.image_file_si = Path(resource_path(image_file_si))
        self.idioma_tts = idioma_tts

        # Genera el audio
        self.sound_file = self.preparar_audio()

        # Extrae features de audio con librosa
        self.signals = [sf.read(p)[0] for p in [self.sound_file]]
        self.features = np.array([sum(zero_crossing_rate(signal)) for signal in self.signals])

        # Inicializa pygame y carga imágenes/audio
        self.inicializar_pygame()

    def preparar_audio(self):
        audio = gTTS(text=self.mytext, lang=self.idioma_tts, slow=False)
        audio.save(self.audio_path)
        return self.audio_path

    def inicializar_pygame(self):
        pygame.init()
        self.screen_width = 255
        self.screen_height = 246
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption('Animación con Imagen y Sonido')

        # Enviar ventana al fondo
        self.enviar_ventana_al_fondo()

        # Carga y escala imágenes
        self.image_no = pygame.image.load(str(self.image_file_no))
        self.image_no = pygame.transform.scale(self.image_no, (self.screen_width, self.screen_height))
        self.image_si = pygame.image.load(str(self.image_file_si))
        self.image_si = pygame.transform.scale(self.image_si, (self.screen_width, self.screen_height))

        # Carga audio
        self.audio = AudioSegment.from_file(str(self.sound_file))
        pygame.mixer.init()
        self.sound = pygame.mixer.Sound(str(self.sound_file))

    def enviar_ventana_al_fondo(self):
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_BOTTOM,
                100, 100, self.screen_width, self.screen_height,
                win32con.SWP_NOACTIVATE
            )
        except Exception as e:
            print(f"Error al enviar ventana al fondo: {e}")

    def obtener_duracion_audio(self):
        return len(self.audio) / 1000.0  # duración en segundos

    def reproducir_animacion(self):
        self.sound.play()
        duracion_audio = self.obtener_duracion_audio()

        for feature in self.features[0]:
            if feature > (self.features[0].max()) / 11:
                self.screen.blit(self.image_no, (0, 0))
            else:
                self.screen.blit(self.image_si, (0, 0))

            time.sleep(duracion_audio / (len(self.features[0]) + 1))
            pygame.display.flip()
            pygame.time.delay(int(duracion_audio / len(self.features[0])))

        pygame.quit()

        # Borrar archivo de audio temporal
        try:
            remove(self.audio_path)
        except Exception as e:
            print(f"No se pudo eliminar {self.audio_path}: {e}")
