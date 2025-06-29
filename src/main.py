from managers.llm_manager import LLMManager
from ui.main_app import UnlockHearingApp


def main():
    llm_manager = LLMManager()
    app = UnlockHearingApp(llm_manager=llm_manager)
    app.run()


if __name__ == "__main__":
    main()
