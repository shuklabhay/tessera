import logging
import os

# Disable debug logging
os.environ["KIVY_LOG_LEVEL"] = "warning"
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)

from managers.llm_manager import LLMManager
from ui.main_app import TesseraApp


def main() -> None:
    """Launch the Tessera application."""
    llm_manager = LLMManager()
    app = TesseraApp(llm_manager=llm_manager)
    app.run()


if __name__ == "__main__":
    main()
