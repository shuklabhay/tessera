import logging
import os
import ssl
import sys
from pathlib import Path
from typing import Tuple

import certifi
from dotenv import load_dotenv

from audio_engine.audio_controller import AudioController
from managers.state_manager import StateManager, get_app_data_dir
from services.conversation_service import ConversationService
from ui.main_app import TesseraApp

os.environ["KIVY_LOG_LEVEL"] = "warning"
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)

ssl._create_default_https_context = ssl._create_unverified_context
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)


def is_valid_api_key(api_key: str) -> bool:
    """Validates if API key is legitimate and not a placeholder."""
    if not api_key:
        return False

    key = api_key.strip()

    if not key.startswith("AIza"):
        return False

    if len(key) < 20:
        return False

    placeholder_values = {"test_key", "your_api_key", "api_key_here"}
    if key.lower() in placeholder_values:
        return False

    return True


def get_api_key_source() -> Tuple[str, str]:
    """Determines where API key is coming from."""
    app_env_file = get_app_data_dir() / ".env"

    if app_env_file.exists():
        with open(app_env_file) as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip(), "app_file"

    system_key = os.environ.get("GEMINI_API_KEY")
    if system_key:
        return system_key, "system"

    return "", "none"


def load_environment() -> None:
    """Loads environment variables in correct priority order."""
    app_data_env = get_app_data_dir() / ".env"
    if app_data_env.exists():
        load_dotenv(app_data_env, override=True)
    else:
        load_dotenv(override=False)


def clear_system_api_key() -> None:
    """Clears system environment variable for current process."""
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]


def main() -> None:
    """Launches the Tessera application."""
    load_environment()

    api_key, source = get_api_key_source()
    conversation_manager = None

    if source == "system" and not is_valid_api_key(api_key):
        clear_system_api_key()
        api_key = ""

    if is_valid_api_key(api_key):
        state_manager = StateManager()
        audio_controller = AudioController()
        conversation_manager = ConversationService(audio_controller, state_manager)

    app = TesseraApp(conversation_manager=conversation_manager)
    app.run()


if __name__ == "__main__":
    main()
