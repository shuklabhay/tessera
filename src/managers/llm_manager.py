import asyncio
import os
import ssl
import threading
import time as time_module
import traceback
from typing import Any, Dict, List, Optional, Union

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


def load_system_prompt() -> str:
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "system_prompt.md"
    )
    with open(prompt_path, "r") as file:
        return file.read()


class LLMManager:
    def __init__(self) -> None:
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue()
        self.viz_queue = []
        self.session = None
        self.input_stream = None
        self.output_stream = None
        self.running = False
        self.gemini_speaking = False
        self.turn_ended = asyncio.Event()
        self.speech_threshold = 400
        self.recording = False
        self.last_voice_detected = 0
        self.recording_duration = 1.5
        self.check_time = 0
        self.silence_start_time = None
        self.state_manager = StateManager()
        self.system_prompt = self._get_contextual_system_prompt()
        self.audio_controller = AudioController()
        self.startup_phase = self._determine_startup_phase()
        self._log_intro_pending = False
        self.loop = None
        self.thread = None

    def _get_contextual_system_prompt(self) -> str:
        """Get the contextual system prompt."""
        base_prompt = load_system_prompt()
        context_summary = self.state_manager.get_context_summary()
        if context_summary:
            return f"{base_prompt}\n\n---\n\n## Current Session Context\n\n{context_summary}"
        return base_prompt

    def _determine_startup_phase(self) -> str:
        """Determine the startup phase."""
        state = self.state_manager._read_state()

        # Set phase based on session history
        if not state.get("sessions"):
            return "intro"
        if len(state["sessions"]) < 5:
            return "training"
        return "diagnostic"

    def update_progress_file(self, new_observation: str) -> str:
        """Update the progress file."""
        self.state_manager.update_progress(new_observation)
        return "Progress successfully logged."

    def get_tools(self) -> List[types.Tool]:
        """Get the available tools."""
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
                        name="adjust_volume",
                        description="Adjust the volume of a specific audio type.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "audio_type": types.Schema(
                                    type=types.Type.STRING,
                                    description="The type of audio to adjust.",
                                ),
                                "clip_id": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="clip_id returned by get_status identifying which clip to adjust.",
                                ),
                                "volume": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="The new volume from 0.0 to 1.0.",
                                ),
                            },
                            required=["clip_id", "volume"],
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
                        name="add_session_observation",
                        description="Log a high-level summary of the user's performance on a specific skill, observed over several trials.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "summary": types.Schema(
                                    type=types.Type.STRING,
                                    description="A concise summary of the user's demonstrated ability (e.g., 'User can reliably identify two streams') or inability (e.g., 'User struggles to discriminate speech from noise').",
                                )
                            },
                            required=["summary"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="read_progress_log",
                        description="Return a concise textual summary of the user progress JSON.",
                        parameters=types.Schema(type=types.Type.OBJECT),
                    ),
                    types.FunctionDeclaration(
                        name="see_full_progress",
                        description="Return the entire progress JSON file as formatted text.",
                        parameters=types.Schema(type=types.Type.OBJECT),
                    ),
                    types.FunctionDeclaration(
                        name="pan_pattern_sweep",
                        description="Sweep audio across stereo field with smooth motion.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "clip_id": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="clip_id to apply sweep pattern to.",
                                ),
                                "direction": types.Schema(
                                    type=types.Type.STRING,
                                    description="Direction: 'left_to_right', 'right_to_left', or 'center_out'.",
                                ),
                                "speed": types.Schema(
                                    type=types.Type.STRING,
                                    description="Speed: 'slow', 'moderate', or 'fast'.",
                                ),
                            },
                            required=["clip_id"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="pan_pattern_pendulum",
                        description="Create rhythmic back-and-forth panning motion.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "clip_id": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="clip_id to apply pendulum pattern to.",
                                ),
                                "cycles": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="Number of complete swing cycles.",
                                ),
                                "duration_per_cycle": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Seconds per complete cycle.",
                                ),
                            },
                            required=["clip_id"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="pan_pattern_alternating",
                        description="Alternate between left and right positions at intervals.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "clip_id": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="clip_id to apply alternating pattern to.",
                                ),
                                "interval": types.Schema(
                                    type=types.Type.NUMBER,
                                    description="Seconds between position changes.",
                                ),
                                "cycles": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="Number of position changes.",
                                ),
                            },
                            required=["clip_id"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="pan_to_side",
                        description="Quickly position audio to a specific side.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "clip_id": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="clip_id to position.",
                                ),
                                "side": types.Schema(
                                    type=types.Type.STRING,
                                    description="Position: 'left', 'right', 'center', 'hard_left', 'hard_right', 'slight_left', 'slight_right'.",
                                ),
                            },
                            required=["clip_id", "side"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="stop_panning_patterns",
                        description="Stop active panning animations for a clip or all clips.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "clip_id": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="clip_id to stop patterns for, or omit to stop all patterns.",
                                ),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="play_alert_sound",
                        description="Play a random alert/notification sound once (no loop).",
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
                ]
            )
        ]

    def get_live_config(self) -> types.LiveConnectConfig:
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

    def audio_callback(
        self, indata: np.ndarray, frames: int, time: Any, status: Any
    ) -> None:
        """Process incoming audio."""
        if not self.running or self.gemini_speaking:
            return
        current_time = time_module.time()
        amplitude = np.linalg.norm(indata)

        # Process audio if recording
        if self.recording:
            self.audio_in_queue.put_nowait(bytes(indata))

            # Update voice detection timestamp
            if amplitude > self.speech_threshold:
                self.last_voice_detected = current_time

            if current_time >= self.check_time:
                # Check if still speaking
                still_speaking = (
                    current_time - self.last_voice_detected
                ) < self.recording_duration

                # Handle turn change
                if still_speaking:
                    self.check_time = current_time + self.recording_duration
                else:
                    self.recording = False
                    self.audio_in_queue.put_nowait(None)

        # Start recording if speech detected
        elif amplitude > self.speech_threshold:
            self.recording = True
            self.audio_controller._auto_duck_background(True)
            self.last_voice_detected = current_time
            self.check_time = current_time + self.recording_duration
            self.audio_in_queue.put_nowait(bytes(indata))

        # Mark turn end after silence
        elif not self.recording and amplitude < self.speech_threshold:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
            elif (current_time - self.silence_start_time) >= self.recording_duration:
                self.audio_in_queue.put_nowait(None)
                self.silence_start_time = None
        else:
            # Reset silence timer
            self.silence_start_time = None

    async def listen_audio(self) -> None:
        """Listen for audio from the input stream."""
        self.recording = False
        self.last_voice_detected = time_module.time()

        # Create and start audio stream
        self.input_stream = sd.InputStream(
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            callback=self.audio_callback,
            blocksize=CHUNK_SIZE,
            dtype=np.int16,
        )
        self.input_stream.start()

        # Keep stream running
        while self.running:
            await asyncio.sleep(0.1)
        self.input_stream.stop()
        self.input_stream.close()

    async def send_audio(self) -> None:
        """Send audio to the session."""
        chunk_sent = False
        while self.running:
            audio_chunk = await self.audio_in_queue.get()

            # Send audio chunk
            if self.session and audio_chunk is not None:
                await self.session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_chunk,
                        mime_type="audio/pcm;rate=16000",
                    )
                )
                chunk_sent = True

            # Send end-of-turn signal
            elif self.session and audio_chunk is None:
                if chunk_sent:
                    await self.session.send_realtime_input(audio_stream_end=True)
                chunk_sent = False

    def execute_function(self, function_call: Any) -> Union[str, Dict[str, Any]]:
        """Execute a function call from the model."""
        print(function_call)
        function_name = function_call.name
        args = function_call.args if hasattr(function_call, "args") else {}

        if function_name == "play_environmental_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_environmental_sound(volume)
        elif function_name == "play_speaker_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_speaker_sound(volume)
        elif function_name == "play_noise_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_noise_sound(volume)
        elif function_name == "adjust_volume":
            return self.audio_controller.adjust_volume(
                args.get("audio_type"), args.get("volume"), args.get("clip_id")
            )
        elif function_name == "stop_audio":
            return self.audio_controller.stop_audio(args.get("audio_type"))
        elif function_name == "stop_all_audio":
            return self.audio_controller.stop_all_audio()
        elif function_name == "get_status":
            return self.audio_controller.get_status()
        elif function_name == "add_session_observation":
            summary = args.get("summary")
            if summary:
                return self.update_progress_file(summary)
            return "Error: summary not provided."
        elif function_name == "read_progress_log":
            return self.state_manager.get_context_summary()
        elif function_name == "see_full_progress":
            return self.state_manager.get_full_progress()
        elif function_name == "pan_pattern_sweep":
            return self.audio_controller.pan_pattern_sweep(
                args.get("clip_id"), args.get("direction"), args.get("speed")
            )
        elif function_name == "pan_pattern_pendulum":
            return self.audio_controller.pan_pattern_pendulum(
                args.get("clip_id"), args.get("cycles"), args.get("duration_per_cycle")
            )
        elif function_name == "pan_pattern_alternating":
            return self.audio_controller.pan_pattern_alternating(
                args.get("clip_id"), args.get("interval"), args.get("cycles")
            )
        elif function_name == "pan_to_side":
            return self.audio_controller.pan_to_side(
                args.get("clip_id"), args.get("side")
            )
        elif function_name == "stop_panning_patterns":
            return self.audio_controller.stop_panning_patterns(args.get("clip_id"))
        elif function_name == "play_alert_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_alert_sound(volume)

        else:
            return f"Unknown function: {function_name}"

    async def receive_and_process_responses(self) -> None:
        """Receive and process responses from the model."""
        while self.running:
            has_audio_in_turn = False
            turn = self.session.receive()
            async for response in turn:
                if not self.running:
                    break

                # Handle tool calls
                if (
                    hasattr(response, "tool_call")
                    and response.tool_call
                    and hasattr(response.tool_call, "function_calls")
                ):
                    fc_list = list(response.tool_call.function_calls)
                    function_responses = []
                    for function_call in fc_list:
                        result = self.execute_function(function_call)
                        function_responses.append(
                            types.FunctionResponse(
                                id=(
                                    function_call.id
                                    if hasattr(function_call, "id")
                                    else None
                                ),
                                name=function_call.name,
                                response=(
                                    result
                                    if isinstance(result, dict)
                                    else {"result": str(result)}
                                ),
                            )
                        )

                    # Send responses
                    await self.session.send_tool_response(
                        function_responses=function_responses
                    )

                # Handle server content
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            if not self.gemini_speaking:
                                self.gemini_speaking = True
                                self.audio_controller._auto_duck_background(True)
                            has_audio_in_turn = True
                            audio_data = part.inline_data.data
                            self.out_queue.put_nowait(audio_data)
                            self.viz_queue.append(audio_data)

            if has_audio_in_turn:
                self.turn_ended.set()

    async def play_audio(self) -> None:
        """Play audio from the output stream."""
        self.output_stream = sd.OutputStream(
            samplerate=RECEIVE_SAMPLE_RATE, channels=CHANNELS, dtype=np.int16
        )
        self.output_stream.start()

        while self.running:
            # Play audio chunk
            audio_chunk = await self.out_queue.get()
            if audio_chunk:
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                self.output_stream.write(audio_array)
            self.out_queue.task_done()

        self.output_stream.stop()
        self.output_stream.close()

    async def manage_speaking_state(self) -> None:
        """Manage the speaking state of the model."""
        while self.running:
            await self.turn_ended.wait()
            await self.out_queue.join()
            self.gemini_speaking = False
            self.audio_controller._auto_duck_background(False)

            # Log introduction completion
            if self._log_intro_pending:
                self.state_manager.update_progress("Introduction finished.")
                self._log_intro_pending = False
            self.turn_ended.clear()

    async def _send_initial_prompt(self) -> None:
        """Send the initial prompt to the model."""
        if self.startup_phase == "intro":
            text = "Initialize introduction phase for new user."
            self._log_intro_pending = True
        elif self.startup_phase == "training":
            text = "Resume appropriate training stage based on prior sessions."
        else:
            text = "Begin diagnostic assessment session."

        await self.session.send_client_content(
            turns={"role": "user", "parts": [{"text": text}]},
            turn_complete=True,
        )

    async def run_async(self) -> None:
        """Run the asynchronous event loop."""
        self.running = True
        async with client.aio.live.connect(
            model=MODEL, config=self.get_live_config()
        ) as session:
            self.session = session

            await self._send_initial_prompt()

            tasks = [
                self.listen_audio(),
                self.send_audio(),
                self.receive_and_process_responses(),
                self.play_audio(),
                self.manage_speaking_state(),
            ]

            await asyncio.gather(*tasks)
        self.stop()

    def run_in_thread(self) -> None:
        """Run the async event loop in a thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run_async())

    def start(self) -> bool:
        """Start the LLM manager."""
        self.running = True

        # Start async code in a thread
        self.thread = threading.Thread(target=self.run_in_thread, daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        """Stop the LLM manager."""
        self.running = False

        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()

        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()

        if self.audio_controller:
            self.audio_controller.stop_all_audio()
