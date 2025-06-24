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

from audio_engine.audio_controller import AudioController

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
        self.audio_controller = AudioController()

    def get_tools(self):
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="play_environmental_sound",
                        description="Play random environmental background sound (nature, rain, etc)",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="play_speaker_sound",
                        description="Play random speaker audio for training",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="play_noise_sound",
                        description="Play random noise audio for masking",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="generate_white_noise",
                        description="Generate procedural white noise",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="generate_pink_noise",
                        description="Generate procedural pink noise",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="adjust_volume",
                        description="Adjust volume of specific audio stream",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "audio_type": types.Schema(
                                    type=types.Type.STRING,
                                    description="Type of audio: environmental, speakers, noise, white_noise, pink_noise",
                                ),
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="New volume level from 0.0 to 1.0",
                                ),
                            },
                            required=["audio_type", "volume"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="stop_audio",
                        description="Stop specific audio stream or all audio",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "audio_type": types.Schema(
                                    type=types.Type.STRING,
                                    description="Type of audio to stop, or leave empty to stop all",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_audio_status",
                        description="Get current status of background audio",
                        parameters=types.Schema(type=types.Type.OBJECT),
                    ),
                ]
            )
        ]

    def get_config(self):
        tools = self.get_tools()
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
                tools=tools,
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
            tools=tools,
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

    def execute_function(self, function_call):
        func_name = function_call.name
        args = {k: v for k, v in function_call.args.items()}

        if hasattr(self.audio_controller, func_name):
            method = getattr(self.audio_controller, func_name)
            result = method(**args)
            return result
        else:
            return f"Unknown function: {func_name}"

    async def receive_audio(self):
        while self.running:
            turn = self.session.receive()
            async for response in turn:
                print(f"[RAW RESPONSE] {response}")
                if not self.running:
                    break

                if data := response.data:
                    if not self.gemini_speaking:
                        self.gemini_speaking = True
                    self.last_gemini_audio = time_module.time()
                    self.audio_in_queue.put_nowait(data)
                    continue

                if hasattr(response, "candidates") and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, "content") and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, "text") and part.text:
                                    print(f"Narrator: {part.text}")
                                if (
                                    hasattr(part, "function_call")
                                    and part.function_call
                                ):
                                    function_call = part.function_call
                                    print(f"Executing function: {function_call.name}")
                                    result = self.execute_function(function_call)
                                    await self.session.send(
                                        input=types.FunctionResponse(
                                            name=function_call.name,
                                            id=function_call.id,
                                            response={"result": result},
                                        )
                                    )
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
            if self.gemini_speaking:
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
            try:
                bytestream = await asyncio.wait_for(
                    self.audio_in_queue.get(), timeout=1.0
                )
                audio_data = np.frombuffer(bytestream, dtype=np.int16)
                audio_float = (audio_data.astype(np.float32) / 32767.0).reshape(-1, 1)
                await asyncio.to_thread(self.output_stream.write, audio_float)
            except asyncio.TimeoutError:
                self.gemini_speaking = False
                continue

    async def run(self):
        self.running = True
        try:
            async with client.aio.live.connect(
                model=MODEL, config=self.get_config()
            ) as session:
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=100)

                listen_task = asyncio.create_task(self.listen_audio())
                sender_task = asyncio.create_task(self.send_realtime())
                receiver_task = asyncio.create_task(self.receive_audio())
                player_task = asyncio.create_task(self.play_audio())

                await asyncio.gather(
                    listen_task, sender_task, receiver_task, player_task
                )
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()


def main():
    chat = VoiceChat()
    asyncio.run(chat.run())


if __name__ == "__main__":
    main()
