import logging
import time
from config import PORT_OBS, PSD_OBS
from obswebsocket import obsws, requests
from obswebsocket.exceptions import ConnectionFailure


class OBSController:
    def __init__(self):
        self.host = "localhost"
        self.port = PORT_OBS
        self.password = PSD_OBS
        self.ws = None

    def is_connected(self):
        #return self.ws is not None and getattr(self.ws, "ws", None) and self.ws.ws.connected
        return self.ws and self.ws.ws.connected
    
    def connect(self):
        if not self.is_connected():
            try:
                self.ws = obsws(self.host, self.port, self.password)
                self.ws.connect()
                logging.info("Conexión establecida con OBS")
                return True
            except ConnectionFailure:
                logging.error("❌ No se pudo conectar a OBS. Verifica que esté abierto y con WebSocket activo.")
                self.ws = None
                return False
        return True

    def change_scene(self, name: str):
        if self.is_connected():
            try:
                self.ws.call(requests.SetCurrentProgramScene(sceneName=name))
                time.sleep(2)
                print(f"✅ Escena cambiada a: {name}")
                logging.info(f"✅ Escena cambiada a: {name}")
            except Exception as e:
                print(f"❌ Error al cambiar de escena: {e}")
                logging.error(f"❌ Error al cambiar de escena: {e}")
        else:
            logging.warning("⚠️ No se pudo cambiar de escena porque OBS no está conectado.")

    def start(self):
        return self.connect()

    def stop(self):
        if self.is_connected():
            try:
                self.ws.disconnect()
                logging.info("🔌 Conexión con OBS cerrada.")
            except Exception as e:
                logging.error(f"❌ Error al desconectar OBS: {e}")
        self.ws = None
