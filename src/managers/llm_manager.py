import asyncio
import base64
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
from managers.state_manager import StateManager

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
    except Exception as e:
        print(f"Warning: Failed to load system prompt: {e}")
        return None


class LLMManager:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.viz_queue = None
        self.session = None
        self.input_stream = None
        self.output_stream = None
        self.running = True
        self.gemini_speaking = False
        self.last_gemini_audio = None
        self.speech_threshold = 300
        self.recording = False
        self.last_voice_detected = 0
        self.recording_duration = 1.5
        self.state_manager = StateManager()
        self.system_prompt = self._get_contextual_system_prompt()
        self.current_audio_amplitude = 0
        self.audio_controller = AudioController()

        # VAD parameters
        self.audio_buffer = []
        self.buffer_size = 10
        self.voice_confidence = 0.0
        self.voice_threshold = 0.6
        self.min_voice_duration = 0.3
        self.last_gemini_audio_time = 0
        self.gemini_timeout = 2.0

    def _get_contextual_system_prompt(self):
        base_prompt = load_system_prompt()
        context_summary = self.state_manager.get_context_summary()
        if context_summary:
            return f"{context_summary}\n\n{base_prompt}"
        return base_prompt

    def update_progress_log(self, summary: str) -> str:
        try:
            self.state_manager.update_progress(summary)
            return "Progress successfully logged."
        except Exception as e:
            print(f"Error updating progress log: {e}")
            return "An error occurred while trying to log progress."

    def get_tools(self):
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="play_environmental_sound",
                        description="Play a random environmental soundscape.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume from 0.0 to 1.0",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="play_speaker_sound",
                        description="Play a random audio clip of a person speaking.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume from 0.0 to 1.0",
                                )
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="generate_white_noise",
                        description="Generate continuous white noise.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume from 0.0 to 1.0",
                                ),
                                "duration": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Duration of the noise in seconds.",
                                ),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="generate_pink_noise",
                        description="Generate continuous pink noise.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume from 0.0 to 1.0",
                                ),
                                "duration": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Duration of the noise in seconds.",
                                ),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="generate_brown_noise",
                        description="Generate brown noise.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume from 0.0 to 1.0",
                                ),
                                "duration": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Duration in seconds",
                                ),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="stop_all_audio",
                        description="Stop all currently playing audio.",
                        parameters=types.Schema(type=types.Type.OBJECT),
                    ),
                    types.FunctionDeclaration(
                        name="get_status",
                        description="Get the current status of all background audio.",
                        parameters=types.Schema(type=types.Type.OBJECT),
                    ),
                    types.FunctionDeclaration(
                        name="update_progress_log",
                        description="Logs a new observation about the user's performance to their progress journal.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "summary": types.Schema(
                                    type=types.Type.STRING,
                                    description="A concise summary of the AI's observation.",
                                )
                            },
                            required=["summary"],
                        ),
                    ),
                ]
            )
        ]

    async def listen_audio(self):
        self.recording = False
        self.last_voice_detected = time_module.time()

        def audio_callback(indata, frames, time, status):
            if not self.running:
                return

            if self.gemini_speaking:
                if (
                    time_module.time() - self.last_gemini_audio_time
                    > self.gemini_timeout
                ):
                    print("🔇 GEMINI STOPPED - Timeout, resuming input")
                    self.gemini_speaking = False
                else:
                    return

            amplitude = np.linalg.norm(indata)
            self.current_audio_amplitude = amplitude

            self.audio_buffer.append(amplitude)
            if len(self.audio_buffer) > self.buffer_size:
                self.audio_buffer.pop(0)

            if len(self.audio_buffer) >= 3:
                smoothed_amplitude = np.mean(self.audio_buffer)
                amplitude_variance = np.var(self.audio_buffer)

                amplitude_score = min(1.0, smoothed_amplitude / self.speech_threshold)
                variance_score = min(1.0, amplitude_variance / 100.0)
                self.voice_confidence = 0.7 * amplitude_score + 0.3 * variance_score

                if self.voice_confidence > self.voice_threshold:
                    current_time = time_module.time()
                    self.last_voice_detected = current_time

                    if not self.recording:
                        if hasattr(self, "voice_start_time"):
                            if (
                                current_time - self.voice_start_time
                                >= self.min_voice_duration
                            ):
                                self.recording = True
                                print(
                                    f"🎤 USER SPEAKING - Started recording (confidence: {self.voice_confidence:.2f})"
                                )
                        else:
                            self.voice_start_time = current_time
                    else:
                        self.voice_start_time = current_time
                else:
                    if hasattr(self, "voice_start_time"):
                        delattr(self, "voice_start_time")

            if self.recording:
                self.audio_in_queue.put_nowait(bytes(indata))
                silence_duration = time_module.time() - self.last_voice_detected
                if silence_duration > self.recording_duration:
                    self.recording = False
                    print(
                        f"🔇 USER STOPPED - Stopped recording after {silence_duration:.1f}s of silence"
                    )
                    self.audio_in_queue.put_nowait(None)
                    if hasattr(self, "voice_start_time"):
                        delattr(self, "voice_start_time")

        self.input_stream = sd.InputStream(
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            callback=audio_callback,
            blocksize=CHUNK_SIZE,
            dtype=np.int16,
        )
        self.input_stream.start()

        while self.running:
            await asyncio.sleep(0.1)

        self.input_stream.stop()
        self.input_stream.close()

    async def send_realtime(self):
        while self.running:
            audio_chunk = await self.audio_in_queue.get()
            if self.session and audio_chunk is not None:
                await self.session.send(
                    input={"data": audio_chunk, "mime_type": "audio/pcm"}
                )
            elif self.session and audio_chunk is None:
                await self.session.send(end_of_turn=True)

    def execute_function(self, function_call):
        function_name = function_call.name
        args = function_call.args if hasattr(function_call, "args") else {}

        print(f"[EXECUTING] Function: {function_name} with args: {args}")

        if function_name == "play_environmental_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_environmental_sound(volume)
        elif function_name == "play_speaker_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_speaker_sound(volume)
        elif function_name == "generate_white_noise":
            volume = args.get("volume", 0.3)
            duration = args.get("duration", 10)
            return self.audio_controller.generate_white_noise(volume, duration)
        elif function_name == "generate_pink_noise":
            volume = args.get("volume", 0.3)
            duration = args.get("duration", 10)
            return self.audio_controller.generate_pink_noise(volume, duration)
        elif function_name == "generate_brown_noise":
            volume = args.get("volume", 0.3)
            duration = args.get("duration", 10)
            return self.audio_controller.generate_brown_noise(volume, duration)
        elif function_name == "stop_all_audio":
            return self.audio_controller.stop_all_audio()
        elif function_name == "get_status":
            return self.audio_controller.get_status()
        elif function_name == "update_progress_log":
            summary = args.get("summary")
            if summary:
                return self.update_progress_log(summary)
            return "Error: Summary not provided for progress log."
        else:
            return f"Unknown function: {function_name}"

    async def execute_function_call(self, function_call):
        try:
            result = await asyncio.to_thread(self.execute_function, function_call)
            await self.send_function_response(function_call.name, result)
        except Exception as e:
            print(f"Error executing function {function_call.name}: {e}")
            traceback.print_exc()

    async def send_function_response(self, function_name, result):
        try:
            function_response = types.Content(
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name, response={"result": result}
                        )
                    )
                ],
                role="user",
            )
            await self.session.send(input=function_response)
        except Exception as e:
            print(f"[ERROR] Failed to send function response: {e}")
            traceback.print_exc()

    async def _send_initial_prompt(self):
        if self.state_manager.is_first_run():
            initial_prompt = "I'm ready to start my first session."
        else:
            initial_prompt = "I'm ready to continue my training."

        if initial_prompt:
            await self.session.send(input=initial_prompt, end_of_turn=True)
            print(f"[SENT] Initial prompt to AI: {initial_prompt}")

    async def receive_audio(self):
        while self.running:
            try:
                turn = self.session.receive()
                async for response in turn:
                    if not self.running:
                        break

                    if hasattr(response, "server_content") and response.server_content:
                        content = response.server_content

                        if hasattr(content, "model_turn") and content.model_turn:
                            for part in content.model_turn.parts:
                                if hasattr(part, "text") and part.text:
                                    print(f"Narrator: {part.text}")

                                if (
                                    hasattr(part, "function_call")
                                    and part.function_call
                                ):
                                    await self.execute_function_call(part.function_call)

                        if hasattr(content, "turn_complete") and content.turn_complete:
                            if self.gemini_speaking:
                                print("🔇 GEMINI STOPPED - Turn complete")
                            self.gemini_speaking = False

                    if hasattr(response, "candidates") and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, "content") and candidate.content:
                                if (
                                    hasattr(candidate.content, "parts")
                                    and candidate.content.parts
                                ):
                                    for part in candidate.content.parts:
                                        if hasattr(part, "text") and part.text:
                                            print(f"Narrator: {part.text}")

                                        if (
                                            hasattr(part, "function_call")
                                            and part.function_call
                                        ):
                                            await self.execute_function_call(
                                                part.function_call
                                            )

                                        if (
                                            hasattr(part, "inline_data")
                                            and part.inline_data
                                        ):
                                            if hasattr(part.inline_data, "data"):
                                                audio_data = part.inline_data.data
                                                self.out_queue.put_nowait(audio_data)
                                                if not self.gemini_speaking:
                                                    print(
                                                        "🤖 GEMINI SPEAKING - Audio started"
                                                    )
                                                self.gemini_speaking = True
                                                self.last_gemini_audio_time = (
                                                    time_module.time()
                                                )

                    if hasattr(response, "function_calls") and response.function_calls:
                        for function_call in response.function_calls:
                            await self.execute_function_call(function_call)

                    if hasattr(response, "audio") and response.audio:
                        self.out_queue.put_nowait(response.audio)
                        if not self.gemini_speaking:
                            print("🤖 GEMINI SPEAKING - Audio started")
                        self.gemini_speaking = True
                        self.last_gemini_audio_time = time_module.time()

                    if hasattr(response, "end_of_turn") and response.end_of_turn:
                        if self.gemini_speaking:
                            print("🔇 GEMINI STOPPED - End of turn")
                        self.gemini_speaking = False

            except Exception as e:
                print(f"Error in receive_audio: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)

    async def play_audio(self):
        self.output_stream = sd.OutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.int16,
            blocksize=CHUNK_SIZE,
        )
        self.output_stream.start()

        while self.running:
            try:
                audio_chunk = await self.out_queue.get()
                self.last_gemini_audio = audio_chunk

                if isinstance(audio_chunk, bytes):
                    audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
                elif isinstance(audio_chunk, str):
                    try:
                        decoded_audio = base64.b64decode(audio_chunk)
                        audio_data = np.frombuffer(decoded_audio, dtype=np.int16)
                    except Exception as e:
                        print(f"Failed to decode base64 audio: {e}")
                        continue
                else:
                    if hasattr(audio_chunk, "data"):
                        audio_data = np.frombuffer(audio_chunk.data, dtype=np.int16)
                    else:
                        audio_data = np.array(audio_chunk, dtype=np.int16)

                if len(audio_data) > 0:
                    if CHANNELS == 1:
                        audio_data = audio_data.reshape(-1, 1)
                    self.output_stream.write(audio_data)
                    if not self.gemini_speaking:
                        print("🤖 GEMINI SPEAKING - Playing audio")
                    self.gemini_speaking = True
                    self.last_gemini_audio_time = time_module.time()

                self.out_queue.task_done()
            except Exception as e:
                print(f"Error in play_audio: {e}")
                traceback.print_exc()
                continue

        self.output_stream.stop()
        self.output_stream.close()

    async def run(self):
        self.running = True
        try:
            async with client.aio.live.connect(
                model=MODEL,
                config=types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Algenib"
                            )
                        )
                    ),
                    tools=self.get_tools(),
                    system_instruction=self.system_prompt,
                ),
            ) as session:
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=100)
                self.viz_queue = asyncio.Queue()

                await self._send_initial_prompt()

                listen_task = asyncio.create_task(self.listen_audio())
                sender_task = asyncio.create_task(self.send_realtime())
                receiver_task = asyncio.create_task(self.receive_audio())
                player_task = asyncio.create_task(self.play_audio())

                await asyncio.gather(
                    listen_task, sender_task, receiver_task, player_task
                )

        except Exception as e:
            print(f"Error in run: {e}")
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.audio_controller:
            self.audio_controller.stop_all_audio()
