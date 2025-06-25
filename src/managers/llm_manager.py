import asyncio
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


class LLMManager:
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
        self.state_manager = StateManager()
        self.system_prompt = self._get_contextual_system_prompt()
        self.current_audio_amplitude = 0
        self.audio_controller = AudioController()

    def _get_contextual_system_prompt(self):
        """
        Gets the base system prompt and prepends the user's current context.
        """
        base_prompt = load_system_prompt()
        context_summary = self.state_manager.get_context_summary()
        if context_summary:
            return f"{context_summary}\n\n{base_prompt}"
        return base_prompt

    def update_progress_log(self, summary: str) -> str:
        """
        Updates the user's progress log with a new summary and advances them to the next stage.
        """
        try:
            # Get current state
            progress_content = self.state_manager.get_progress()
            current_stage = self.state_manager.get_current_stage_from_progress(
                progress_content
            )
            new_stage = current_stage + 1
            today_date = datetime.now().strftime("%Y-%m-%d")

            # Update Last Session Date
            progress_content = re.sub(
                r"(- \*\*Last Session Date\*\*: ).*",
                rf"\1{today_date}",
                progress_content,
            )

            # Update Current Stage
            progress_content = re.sub(
                r"(- \*\*Current Stage\*\*: ).*",
                rf"\1{new_stage}",
                progress_content,
            )

            # Append the new summary under AI Observations
            new_observation = f"- {today_date}: {summary}"
            progress_content = re.sub(
                r"(## AI Observations\n)",
                rf"\1\n{new_observation}",
                progress_content,
            )

            # Save the updated progress
            self.state_manager.save_progress(progress_content)

            return f"Progress successfully logged. User is now at stage {new_stage}."
        except Exception as e:
            print(f"Error updating progress log: {e}")
            return "An error occurred while trying to log progress."

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
                        description="Play speaker audio content",
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
                        description="Generate white noise for focus and relaxation",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
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
                        description="Generate pink noise for relaxation and sleep",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
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
                        description="Generate brown noise for deep relaxation",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Volume level from 0.0 to 1.0",
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
                        description="Stop all currently playing audio",
                        parameters=types.Schema(type=types.Type.OBJECT),
                    ),
                    types.FunctionDeclaration(
                        name="get_status",
                        description="Get current status of background audio",
                        parameters=types.Schema(type=types.Type.OBJECT),
                    ),
                    types.FunctionDeclaration(
                        name="update_progress_log",
                        description="Logs the user's performance summary and advances them to the next stage.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "summary": types.Schema(
                                    type=types.Type.STRING,
                                    description="A concise summary of the user's performance, including strengths and areas for improvement.",
                                )
                            },
                            required=["summary"],
                        ),
                    ),
                ]
            )
        ]

    def get_live_config(self):
        tools = self.get_tools()

        system_instruction = None
        if self.system_prompt:
            system_instruction = types.Content(
                parts=[types.Part.from_text(text=self.system_prompt)], role="user"
            )

        config = types.LiveConnectConfig(
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
            system_instruction=system_instruction,
        )
        return config

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
        """Execute a function call synchronously"""
        try:
            function_name = function_call.name
            args = function_call.args if hasattr(function_call, "args") else {}

            print(f"[EXECUTING SYNC] Function: {function_name} with args: {args}")

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
        except Exception as e:
            print(f"Error executing function {function_call.name}: {e}")
            return f"Error: {e}"

    async def _send_initial_prompt(self):
        """Sends an initial prompt to the AI based on the user's progress."""
        current_stage = self.state_manager.get_current_stage_from_progress(
            self.state_manager.get_progress()
        )
        initial_prompt = ""
        if current_stage == 0:
            initial_prompt = (
                "The user is new. Greet them warmly and begin the diagnostic test."
            )
        else:
            initial_prompt = "The user is returning. Greet them and ask if they want to begin their next stage of structured practice or do some freeform training."

        if initial_prompt:
            await self.session.send(input=initial_prompt)
            print(f"[SENT] Initial prompt to AI: {initial_prompt}")

    async def set_user_mode(self, mode_name: str):
        """Handles the user's mode selection from the UI."""
        prompt = ""
        if mode_name == "structured":
            prompt = "The user has selected 'Structured Practice'. Please begin the next stage for them."
        elif mode_name == "freeform":
            prompt = "The user has selected 'Freeform Training'. Please ask them what they would like to focus on."

        if prompt and self.session:
            await self.session.send(input=prompt)
            print(f"[SENT] User mode selection to AI: {prompt}")

    async def receive_audio(self):
        while self.running:
            turn = self.session.receive()
            async for response in turn:
                if not self.running:
                    break

                if data := response.data:
                    if not self.gemini_speaking:
                        self.gemini_speaking = True
                    self.last_gemini_audio = time_module.time()
                    self.audio_in_queue.put_nowait(data)

                if server_content := response.server_content:
                    if model_turn := server_content.model_turn:
                        for part in model_turn.parts:
                            if part.text:
                                print(f"Narrator: {part.text}")

                            if hasattr(part, "function_call") and part.function_call:
                                await self.execute_function_call(part.function_call)

                            elif (
                                hasattr(part, "executable_code")
                                and part.executable_code
                            ):
                                await self.handle_executable_code(part.executable_code)

                            elif hasattr(part, "functionCall") and part.functionCall:
                                await self.execute_function_call(part.functionCall)

                if hasattr(response, "function_calls") and response.function_calls:
                    for function_call in response.function_calls:
                        await self.execute_function_call(function_call)

            if self.gemini_speaking:
                self.gemini_speaking = False

    async def execute_function_call(self, function_call):
        """Execute a function call and send the response back to the model"""
        args = function_call.args if hasattr(function_call, "args") else {}
        print(f"[EXECUTING ASYNC] Function: {function_call.name} with args: {args}")
        try:
            result = await asyncio.to_thread(self.execute_function, function_call)
            await self.send_function_response(function_call.name, result)
        except Exception as e:
            print(f"Error executing function call: {e}")
            traceback.print_exc()

    async def send_function_response(self, function_name, result):
        """Sends the result of a function call back to the model."""
        try:
            function_response = types.Content(
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name,
                            response={"result": result},
                        )
                    )
                ],
                role="user",
            )
            await self.session.send(input=function_response)
        except Exception as e:
            print(f"[ERROR] Failed to send function response: {e}")
            traceback.print_exc()

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
                model=MODEL, config=self.get_live_config()
            ) as session:
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=100)

                # Send initial prompt to AI based on user's state
                await self._send_initial_prompt()

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

    async def handle_executable_code(self, executable_code):
        """Handle executable code that might contain audio function calls"""
        try:
            code = (
                executable_code.code
                if hasattr(executable_code, "code")
                else str(executable_code)
            )
            if "generate_white_noise" in code:
                self.audio_controller.generate_white_noise(0.3, 10)
            elif "generate_pink_noise" in code:
                self.audio_controller.generate_pink_noise(0.3, 10)
            elif "generate_brown_noise" in code:
                self.audio_controller.generate_brown_noise(0.3, 10)
            elif "play_environmental_sound" in code:
                self.audio_controller.play_environmental_sound(0.7)
            elif "play_speaker_sound" in code:
                self.audio_controller.play_speaker_sound(0.7)
            elif "get_status" in code:
                self.audio_controller.get_status()
            elif "stop_all_audio" in code:
                self.audio_controller.stop_all_audio()
        except Exception as e:
            print(f"[ERROR] Code execution failed: {e}")
            traceback.print_exc()
