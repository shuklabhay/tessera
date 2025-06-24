import asyncio
import os
import threading

from ai.voice_chat import VoiceChat
from ui.main_app import UnlockHearingApp


def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.md")
    try:
        with open(prompt_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Warning: Failed to load system prompt: {e}")
        return None


def run_voice_chat_async(voice_chat):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(voice_chat.run())


def main():
    voice_chat = VoiceChat()
    system_prompt = load_system_prompt()
    if system_prompt:
        voice_chat.system_prompt = system_prompt
    voice_thread = threading.Thread(
        target=run_voice_chat_async, args=(voice_chat,), daemon=True
    )
    voice_thread.start()
    app = UnlockHearingApp(voice_chat=voice_chat)
    app.run()
    voice_chat.running = False


if __name__ == "__main__":
    main()
