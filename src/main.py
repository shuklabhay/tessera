from managers.llm_manager import LLMManager
from ui.main_app import TesseraApp


def main() -> None:
    """Launch the Tessera application."""
    llm_manager = LLMManager()
    app = TesseraApp(llm_manager=llm_manager)
    app.run()


if __name__ == "__main__":
    main()
