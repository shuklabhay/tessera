import logging
import os

# Disable debug logging
os.environ["KIVY_LOG_LEVEL"] = "warning"
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)

from audio_engine.audio_controller import AudioController
from managers.llm_manager import LLMManager
from managers.state_manager import StateManager
from ui.main_app import TesseraApp


def main() -> None:
    """Launch the Tessera application."""
    # Initialize components
    state_manager = StateManager()
    audio_controller = AudioController()
    llm_manager = LLMManager(audio_controller, state_manager)
    
    app = TesseraApp(llm_manager=llm_manager)
    app.run()


if __name__ == "__main__":
    main()
