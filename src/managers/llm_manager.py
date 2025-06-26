import asyncio
import os
import ssl
import threading
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
        print(f"Warning: Failed to load system prompt: {e}", flush=True)
        return None


class LLMManager:
    def __init__(self):
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue()
        self.viz_queue = []
        self.session = None
        self.input_stream = None
        self.output_stream = None
        self.running = False
        self.gemini_speaking = False
        self.speech_threshold = 200
        self.recording = False
        self.last_voice_detected = 0
        self.recording_duration = 1.0
        self.state_manager = StateManager()
        self.system_prompt = self._get_contextual_system_prompt()
        self.audio_controller = AudioController()
        self.loop = None
        self.thread = None

    def _get_contextual_system_prompt(self):
        base_prompt = load_system_prompt()
        context_summary = self.state_manager.get_context_summary()
        if context_summary:
            return f"{context_summary}\n\n{base_prompt}"
        return base_prompt

    def update_progress_file(self, new_observation: str) -> str:
        try:
            self.state_manager.update_progress(new_observation)
            return "Progress successfully logged."
        except Exception as e:
            print(f"Error updating progress log: {e}", flush=True)
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
                        name="play_noise_sound",
                        description="Play a random pre-recorded noise sound.",
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
                        name="adjust_volume",
                        description="Adjust the volume of a specific audio type.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "audio_type": types.Schema(
                                    type=types.Type.STRING,
                                    description="The type of audio to adjust.",
                                ),
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="The new volume from 0.0 to 1.0.",
                                ),
                            },
                            required=["audio_type", "volume"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="pan_audio",
                        description="Pan an audio source to the left or right.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "audio_type": types.Schema(
                                    type=types.Type.STRING,
                                    description="The type of audio to pan.",
                                ),
                                "pan": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Pan value from -1.0 (left) to 1.0 (right).",
                                ),
                            },
                            required=["audio_type", "pan"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="stop_audio",
                        description="Stop a specific type of audio stream.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "audio_type": types.Schema(
                                    type=types.Type.STRING,
                                    description="The type of audio to stop.",
                                )
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
                        name="update_progress_file",
                        description="Logs a new observation about the user's performance.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "new_observation": types.Schema(
                                    type=types.Type.STRING,
                                    description="A concise summary of the observation.",
                                )
                            },
                            required=["new_observation"],
                        ),
                    ),
                ]
            )
        ]

    def get_live_config(self):
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Algenib"
                    )
                )
            ),
            realtime_input_config=types.RealtimeInputConfig(
                turn_coverage="TURN_INCLUDES_ALL_INPUT"
            ),
            tools=self.get_tools(),
            system_instruction=self.system_prompt,
        )

    def audio_callback(self, indata, frames, time, status):
        if not self.running:
            return

        amplitude = np.linalg.norm(indata)

        if amplitude > self.speech_threshold:
            self.last_voice_detected = time_module.time()
            if not self.recording:
                self.recording = True
                print("🎤 Voice detected, starting to record!", flush=True)

        if self.recording:
            try:
                self.audio_in_queue.put_nowait(bytes(indata))
            except:
                pass  # Queue might be full

            silence_duration = time_module.time() - self.last_voice_detected
            if silence_duration > self.recording_duration:
                self.recording = False
                print(
                    f"🔇 Silence detected ({silence_duration:.1f}s), stopping recording.",
                    flush=True,
                )
                try:
                    self.audio_in_queue.put_nowait(None)  # End of turn marker
                except:
                    pass

    async def listen_audio(self):
        self.recording = False
        self.last_voice_detected = time_module.time()

        self.input_stream = sd.InputStream(
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            callback=self.audio_callback,
            blocksize=CHUNK_SIZE,
            dtype=np.int16,
        )
        self.input_stream.start()
        print("🎙️ Audio input started", flush=True)

        while self.running:
            await asyncio.sleep(0.1)

        self.input_stream.stop()
        self.input_stream.close()

    async def send_audio(self):
        while self.running:
            try:
                audio_chunk = await self.audio_in_queue.get()
                if self.session and audio_chunk is not None:
                    turn = {"data": audio_chunk, "mime_type": "audio/pcm"}
                    await self.session.send(input=turn)
                elif self.session and audio_chunk is None:
                    await self.session.send(end_of_turn=True)
            except Exception as e:
                print(f"❌ Error sending audio: {e}", flush=True)

    def execute_function(self, function_call):
        function_name = function_call.name
        args = function_call.args if hasattr(function_call, "args") else {}

        print(f"🔧 Executing function: {function_name} with args: {args}", flush=True)

        if function_name == "play_environmental_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_environmental_sound(volume)
        elif function_name == "play_speaker_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_speaker_sound(volume)
        elif function_name == "play_noise_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_noise_sound(volume)
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
        elif function_name == "adjust_volume":
            return self.audio_controller.adjust_volume(
                args.get("audio_type"), args.get("volume")
            )
        elif function_name == "pan_audio":
            return self.audio_controller.pan_audio(
                args.get("audio_type"), args.get("pan")
            )
        elif function_name == "stop_audio":
            return self.audio_controller.stop_audio(args.get("audio_type"))
        elif function_name == "stop_all_audio":
            return self.audio_controller.stop_all_audio()
        elif function_name == "get_status":
            return self.audio_controller.get_status()
        elif function_name == "update_progress_file":
            new_observation = args.get("new_observation")
            if new_observation:
                return self.update_progress_file(new_observation)
            return "Error: new_observation not provided for progress log."
        else:
            return f"Unknown function: {function_name}"

    async def receive_and_process_responses(self):
        while self.running:
            try:
                turn = self.session.receive()
                async for response in turn:
                    if not self.running:
                        break

                    if response.tool_call and response.tool_call.function_calls:
                        for function_call in response.tool_call.function_calls:
                            result = self.execute_function(function_call)
                            function_response = types.FunctionResponse(
                                name=function_call.name,
                                response={"result": str(result)},
                            )
                            await self.session.send(input=function_response)
                        continue

                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                print("🤖 Gemini speaking...", flush=True)
                                self.gemini_speaking = True
                                audio_data = part.inline_data.data
                                self.out_queue.put_nowait(audio_data)
                                self.viz_queue.append(audio_data)
                            if part.text:
                                print(f"💬 AI: {part.text}", flush=True)

            except Exception as e:
                if "no response available" not in str(e).lower():
                    print(f"❌ Error processing responses: {e}", flush=True)
                await asyncio.sleep(0.1)

    async def play_audio(self):
        self.output_stream = sd.OutputStream(
            samplerate=RECEIVE_SAMPLE_RATE, channels=CHANNELS, dtype=np.int16
        )
        self.output_stream.start()
        print("🔊 Audio output started", flush=True)

        while self.running:
            try:
                audio_chunk = await self.out_queue.get()
                if audio_chunk:
                    audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                    self.output_stream.write(audio_array)
                self.out_queue.task_done()
            except Exception as e:
                print(f"❌ Error playing audio: {e}", flush=True)

        self.output_stream.stop()
        self.output_stream.close()

    async def _send_initial_prompt(self):
        if not self.state_manager.is_first_run():
            print("👋 Sending greeting for returning user", flush=True)
            await self.session.send(
                input="I'm back and ready to continue.", end_of_turn=True
            )

    async def run_async(self):
        self.running = True
        try:
            async with client.aio.live.connect(
                model=MODEL, config=self.get_live_config()
            ) as session:
                self.session = session
                print("✅ Connected to Gemini Live!", flush=True)

                await self._send_initial_prompt()

                tasks = [
                    self.listen_audio(),
                    self.send_audio(),
                    self.receive_and_process_responses(),
                    self.play_audio(),
                ]

                await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ Error in async run: {e}", flush=True)
            traceback.print_exc()
        finally:
            self.stop()

    def run_in_thread(self):
        """Run the async event loop in a separate thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run_async())

    def start(self):
        print("🚀 Starting LLM Manager...", flush=True)
        self.running = True

        # Start the async code in a separate thread
        self.thread = threading.Thread(target=self.run_in_thread, daemon=True)
        self.thread.start()

        print("✅ LLM Manager started successfully!", flush=True)
        return True

    def stop(self):
        print("🛑 Stopping LLM Manager...", flush=True)
        self.running = False

        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()

        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()

        if self.audio_controller:
            self.audio_controller.stop_all_audio()

        print("✅ LLM Manager stopped", flush=True)
