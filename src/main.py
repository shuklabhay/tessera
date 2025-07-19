import logging
import os
import ssl

import certifi
from dotenv import load_dotenv

os.environ["KIVY_LOG_LEVEL"] = "warning"
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)

ssl._create_default_https_context = ssl._create_unverified_context
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
load_dotenv()


from audio_engine.audio_controller import AudioController
from services.conversation_service import ConversationService
from managers.state_manager import StateManager
from ui.main_app import TesseraApp


def main() -> None:
    """
    Launches the Tessera application.
    """
    state_manager = StateManager()
    audio_controller = AudioController()
    conversation_manager = ConversationService(audio_controller, state_manager)

    app = TesseraApp(conversation_manager=conversation_manager)
    app.run()


if __name__ == "__main__":
    main()
