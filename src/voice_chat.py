import asyncio
import os
import ssl
import time as time_module
import traceback

import certifi
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from google import genai
from google.genai import types

ssl._create_default_https_context = ssl._create_stdlib_context
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
load_dotenv()

CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
MODEL = "models/gemini-2.5-flash-preview-native-audio-dialog"

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)


def load_system_prompt():
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "system_prompt.md"
    )
    try:
        with open(prompt_path, "r") as file:
            return file.read()
    except Exception:
        return None


class VoiceChat:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.input_stream = None
        self.output_stream = None
        self.running = False
        self.gemini_speaking = False
        self.last_gemini_audio = 0
        self.speech_threshold = 500
        self.recording = False
        self.last_voice_detected = 0
        self.recording_duration = 1.5
        self.system_prompt = load_system_prompt()
        self.current_audio_amplitude = 0

    def get_config(self):
        if self.system_prompt:
            return types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                media_resolution="MEDIA_RESOLUTION_MEDIUM",
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Algenib"
                        )
                    )
                ),
                context_window_compression=types.ContextWindowCompressionConfig(
                    trigger_tokens=25600,
                    sliding_window=types.SlidingWindow(target_tokens=12800),
                ),
                system_instruction=types.Content(
                    parts=[types.Part.from_text(text=self.system_prompt)], role="user"
                ),
            )
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            media_resolution="MEDIA_RESOLUTION_MEDIUM",
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Algenib"
                    )
                )
            ),
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=25600,
                sliding_window=types.SlidingWindow(target_tokens=12800),
            ),
        )

    async def listen_audio(self):
        self.input_stream = await asyncio.to_thread(
            sd.InputStream,
            channels=CHANNELS,
            samplerate=SEND_SAMPLE_RATE,
            blocksize=CHUNK_SIZE,
            dtype=np.float32,
        )
        self.input_stream.start()
        while self.running:
            current_time = time_module.time()
            if self.gemini_speaking or (current_time - self.last_gemini_audio < 0.5):
                await asyncio.sleep(0.01)
                continue
            data = await asyncio.to_thread(self.input_stream.read, CHUNK_SIZE)
            audio_data = (data[0][:, 0] * 32767).astype(np.int16)
            amplitude = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            current_time = time_module.time()
            if amplitude > self.speech_threshold:
                if not self.recording:
                    self.recording = True
                    print("[DEBUG] User speaking detected: recording started")
                self.last_voice_detected = current_time
            if self.recording:
                if current_time - self.last_voice_detected > self.recording_duration:
                    self.recording = False
                    print("[DEBUG] User speaking ended: recording stopped")
                else:
                    audio_bytes = audio_data.tobytes()
                    await self.out_queue.put(
                        {"data": audio_bytes, "mime_type": "audio/pcm"}
                    )

    async def send_realtime(self):
        while self.running:
            try:
                audio_data = await asyncio.wait_for(self.out_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            await self.session.send_realtime_input(audio=audio_data)

    async def receive_audio(self):
        while self.running:
            turn = self.session.receive()
            async for response in turn:
                if not self.running:
                    break
                if data := response.data:
                    if not self.gemini_speaking:
                        print("[DEBUG] Gemini speaking started")
                    self.gemini_speaking = True
                    self.last_gemini_audio = time_module.time()
                    self.audio_in_queue.put_nowait(data)
                    continue
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
            if self.gemini_speaking:
                print("[DEBUG] Gemini speaking ended")
            self.gemini_speaking = False

    async def play_audio(self):
        self.output_stream = await asyncio.to_thread(
            sd.OutputStream,
            channels=CHANNELS,
            samplerate=RECEIVE_SAMPLE_RATE,
            dtype=np.float32,
        )
        self.output_stream.start()
        while self.running:
            bytestream = await self.audio_in_queue.get()
            print("[DEBUG] Playing audio chunk")
            audio_data = np.frombuffer(bytestream, dtype=np.int16)
            audio_float = (audio_data.astype(np.float32) / 32767.0).reshape(-1, 1)
            await asyncio.to_thread(self.output_stream.write, audio_float)

    async def run(self):
        self.running = True
        config = self.get_config()
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)
                tg.create_task(self.listen_audio())
                tg.create_task(self.send_realtime())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print("[ERROR]", e)
            traceback.print_exc()


def main():
    chat = VoiceChat()
    asyncio.run(chat.run())


if __name__ == "__main__":
    main()
