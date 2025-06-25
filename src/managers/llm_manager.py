import asyncio
import base64
import os
import re
import ssl
import time as time_module
import traceback
from datetime import datetime

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

# Asynchronous client initialization
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)


def load_system_prompt():
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "system_prompt.md"
    )
    return open(prompt_path, "r").read()


class LLMManager:
    def __init__(self):
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue()
        self.session = None
        self.input_stream = None
        self.output_stream = None
        self.running = False
        self.gemini_speaking = False
        self.last_gemini_audio = None
        self.speech_threshold = 200  # Adjusted for np.linalg.norm
        self.recording = False
        self.last_voice_detected = 0
        self.recording_duration = 1.0  # Seconds of silence before stopping
        self.state_manager = StateManager()
        self.system_prompt = self._get_contextual_system_prompt()
        self.audio_controller = AudioController()

    def _get_contextual_system_prompt(self):
        """
        Gets the base system prompt and prepends the user's current context.
        """
        base_prompt = load_system_prompt()
        context_summary = self.state_manager.get_context_summary()
        return f"{context_summary}\n\n{base_prompt}"

    def update_progress_file(self, new_observation: str) -> str:
        """
        Updates the user's progress file with a new observation from the AI.
        """
        self.state_manager.update_progress(new_observation)
        return "Progress successfully logged."

    def get_tools(self):
        """Returns the list of tools available to the AI."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="play_environmental_sound",
                        description="Play a random environmental background sound.",
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
                        description="Generate white noise.",
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
                        name="generate_pink_noise",
                        description="Generate pink noise.",
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
                        name="update_progress_file",
                        description="Logs a new observation about the user's performance to their progress journal.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "new_observation": types.Schema(
                                    type=types.Type.STRING,
                                    description="A concise summary of the AI's observation.",
                                )
                            },
                            required=["new_observation"],
                        ),
                    ),
                ]
            )
        ]

    def get_live_config(self):
        """Builds the configuration for the Gemini LiveConnect session."""
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

    async def listen_audio(self):
        """Captures audio from the microphone and puts it into a queue."""
        self.recording = False
        self.last_voice_detected = time_module.time()

        def audio_callback(indata, frames, time, status):
            if not self.running:
                return
            amplitude = np.linalg.norm(indata)
            if amplitude > self.speech_threshold:
                self.last_voice_detected = time_module.time()
                if not self.recording:
                    self.recording = True
                    print("Voice detected, starting to send audio.")
            if self.recording:
                self.audio_in_queue.put_nowait(bytes(indata))
                if (
                    time_module.time() - self.last_voice_detected
                    > self.recording_duration
                ):
                    self.recording = False
                    print("Silence detected, stopping send.")
                    self.audio_in_queue.put_nowait(None)

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

    async def send_audio(self):
        """Sends audio from the queue to the Gemini session."""
        while self.running:
            audio_chunk = await self.audio_in_queue.get()
            if self.session and audio_chunk is not None:
                # Per reference, send a simple dictionary
                turn = {"data": audio_chunk, "mime_type": "audio/pcm"}
                await self.session.send(input=turn)
            if audio_chunk is None:
                # After sending None, wait for a new recording to start
                while self.running and not self.recording:
                    await asyncio.sleep(0.1)

    def execute_function(self, function_call):
        """Executes a function call from the AI."""
        function_name = function_call.name
        args = function_call.args
        print(f"Executing function: {function_name} with args: {args}")
        if function_name == "play_environmental_sound":
            return self.audio_controller.play_environmental_sound(
                volume=args.get("volume", 1.0)
            )
        elif function_name == "play_speaker_sound":
            return self.audio_controller.play_speaker_sound(
                volume=args.get("volume", 1.0)
            )
        elif function_name == "generate_white_noise":
            return self.audio_controller.generate_noise(
                "white",
                duration=args.get("duration", 10),
                volume=args.get("volume", 0.5),
            )
        elif function_name == "generate_pink_noise":
            return self.audio_controller.generate_noise(
                "pink",
                duration=args.get("duration", 10),
                volume=args.get("volume", 0.5),
            )
        elif function_name == "generate_brown_noise":
            return self.audio_controller.generate_noise(
                "brown",
                duration=args.get("duration", 10),
                volume=args.get("volume", 0.5),
            )
        elif function_name == "stop_all_audio":
            return self.audio_controller.stop_all_audio()
        elif function_name == "get_status":
            return self.audio_controller.get_status()
        elif function_name == "update_progress_file":
            return self.update_progress_file(args.get("new_observation"))

    async def _send_initial_prompt(self):
        """Sends an initial message to kick off the conversation if necessary."""
        if not self.state_manager.is_first_run():
            print("Returning user. Sending initial prompt to elicit greeting.")
            if self.session:
                await self.session.send(
                    input="I'm back and ready to continue.", end_of_turn=True
                )

    async def receive_and_process_responses(self):
        """Receives and processes responses from Gemini."""
        while self.running:
            turn = self.session.receive()
            async for response in turn:
                if not self.running:
                    break
                if hasattr(response, "text") and response.text:
                    print(f"AI: {response.text}")
                if hasattr(response, "data") and response.data:
                    self.gemini_speaking = True
                    self.out_queue.put_nowait(response.data)
                if hasattr(response, "function_call") and response.function_call:
                    result = self.execute_function(response.function_call)
                    function_response_part = types.Part(
                        function_response=types.FunctionResponse(
                            name=response.function_call.name,
                            response={"result": str(result)},
                        )
                    )
                    await self.session.send(input=function_response_part)
        self.gemini_speaking = False

    async def play_audio(self):
        """Plays audio from the output queue using sounddevice."""
        self.output_stream = sd.OutputStream(
            samplerate=RECEIVE_SAMPLE_RATE, channels=CHANNELS, dtype=np.int16
        )
        self.output_stream.start()
        while self.running:
            audio_chunk = await self.out_queue.get()
            self.last_gemini_audio = audio_chunk
            self.output_stream.write(np.frombuffer(audio_chunk, dtype=np.int16))
            self.out_queue.task_done()
        self.output_stream.stop()
        self.output_stream.close()

    async def run(self):
        """Main loop to run the manager."""
        self.running = True
        try:
            # The 'async with' statement is crucial for proper session management
            async with client.aio.live.connect(
                model=MODEL, config=self.get_live_config()
            ) as session:
                self.session = session
                print("Live session connected.")

                tasks = [
                    self.listen_audio(),
                    self.receive_and_process_responses(),
                    self.play_audio(),
                    self.send_audio(),
                ]

                initial_prompt_task = asyncio.create_task(self._send_initial_prompt())
                tasks.append(initial_prompt_task)

                await asyncio.gather(*tasks)
        finally:
            self.stop()

    def stop(self):
        """Stops all running processes cleanly."""
        print("Stopping LLM Manager.")
        self.running = False
        if self.audio_controller:
            self.audio_controller.stop_all_audio()
