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

    def set_source_visibility(self, scene_name: str, source_name: str, visible: bool):
        if self.is_connected():
            try:
                self.ws.call(requests.SetSceneItemEnabled(
                    sceneName=scene_name,
                    sceneItemId=self.get_scene_item_id(scene_name, source_name),
                    sceneItemEnabled=visible
                ))
                estado = "visible" if visible else "oculto"
                print(f"✅ {source_name} ahora está {estado} en {scene_name}")
            except Exception as e:
                logging.error(f"❌ Error al cambiar visibilidad de {source_name}: {e}")

    def get_scene_item_id(self, scene_name: str, source_name: str):
        try:
            items = self.ws.call(requests.GetSceneItemList(sceneName=scene_name)).getSceneItems()
            for item in items:
                print(item)
                if item["sourceName"] == source_name:
                    return item["sceneItemId"]
            raise ValueError(f"No se encontró el recurso '{source_name}' en la escena '{scene_name}'")
        except Exception as e:
            logging.error(f"❌ Error al obtener SceneItemId: {e}")
            return None

    def set_browser_url(self, source_name: str, new_url: str):
        if self.is_connected():
            try:
                self.ws.call(requests.SetInputSettings(
                    inputName=source_name,
                    inputSettings={"url": new_url},
                    overlay=True
                ))
                print(f"🌐 URL de {source_name} cambiada a {new_url}")
            except Exception as e:
                logging.error(f"❌ Error al cambiar URL de {source_name}: {e}")

    def set_image_source(self, source_name: str, file_path: str):
        if self.is_connected():
            try:
                self.ws.call(requests.SetInputSettings(
                    inputName=source_name,
                    inputSettings={"file": file_path},
                    overlay=True
                ))
                print(f"🖼️ Imagen de {source_name} cambiada a {file_path}")
            except Exception as e:
                logging.error(f"❌ Error al cambiar imagen: {e}")

    def set_media_source(self, source_name: str, file_path: str):
        if self.is_connected():
            try:
                self.ws.call(requests.SetInputSettings(
                    inputName=source_name,
                    inputSettings={"local_file": file_path},
                    overlay=True
                ))
                print(f"🎬 Video de {source_name} cambiado a {file_path}")
            except Exception as e:
                logging.error(f"❌ Error al cambiar video: {e}")


# if __name__ == "__main__":
#     clip_url = "https://www.twitch.tv/thefox14k/clip/UnusualImpossibleBeaverOhMyDog-oy1qhnhXJJDzLW8B"

#     # 1. Descargar clip
#     file_path = descargar_clip_twitch(clip_url)
#     print(f"✅ Clip descargado: {file_path}")

#     # 2. Conectar con OBS
#     obs = OBSController()
#     obs.start()

#     # 3. Cambiar a la escena donde está tu fuente "ClipTwitch"
#     obs.change_scene("Escena_Clip")

#     # 4. Cargar clip en la fuente
#     obs.set_media_source("ClipTwitch", file_path)

#     # 5. Esperar la duración del clip (opcional)
#     print("▶️ Reproduciendo clip en OBS...")
#     #time.sleep(10)  # aquí podrías calcular la duración real del clip

#     # 6. Cerrar conexión OBS
#     obs.stop()

#     # 7. Borrar archivo si no quieres guardarlo
#     # os.remove(file_path)
#     # print("🗑️ Clip eliminado después de reproducirlo")