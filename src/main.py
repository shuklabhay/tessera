import asyncio
import threading

from managers.llm_manager import LLMManager
from ui.main_app import UnlockHearingApp


def run_llm_manager_async(llm_manager):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(llm_manager.run())


def main():
    llm_manager = LLMManager()

    voice_thread = threading.Thread(
        target=run_llm_manager_async, args=(llm_manager,), daemon=True
    )
    voice_thread.start()
    app = UnlockHearingApp(llm_manager=llm_manager)
    app.run()
    llm_manager.running = False


if __name__ == "__main__":
    main()
