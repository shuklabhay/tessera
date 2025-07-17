import io
import os
import ssl
import tempfile
import threading
import time as time_module
import wave
from typing import Any, Dict, List, Union

import certifi
import numpy as np
import pygame
import sounddevice as sd
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from google import genai
from google.genai import types
from piper import PiperVoice, SynthesisConfig

from audio_engine.audio_controller import AudioController
from managers.state_manager import StateManager

# --- Environment Setup ---
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def load_system_prompt() -> str:
    """Loads the system prompt from a file."""
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "system_prompt.md"
    )
    with open(prompt_path, "r") as file:
        return file.read()


class LLMManager:
    def __init__(
        self, audio_controller: AudioController, state_manager: StateManager
    ) -> None:
        """Initialize the LLM manager with voice interaction capabilities."""
        self.audio_controller = audio_controller
        self.state_manager = state_manager

        # Voice recording settings
        self.sample_rate = 16000
        self.threshold = 0.01
        self.silence_duration = 1.5
        self.is_recording = False
        self.audio_buffer = []

        # Initialize Whisper for transcription
        self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")

        # Initialize Piper TTS
        self.tts_voice = PiperVoice.load(
            "models/en_US-hfc_male-medium.onnx",
            "models/en_US-hfc_male-medium.onnx.json",
        )
        self.syn_config = SynthesisConfig(length_scale=1.3)

        # Initialize pygame mixer for TTS playback
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)

        # Conversation state
        self.conversation_history = []
        self.has_welcomed = False
        self.last_tool_results = None  # Store tool results for context

        # Turn-based coordination state
        self.kai_is_speaking = False
        self.turn_complete_event = threading.Event()
        self.turn_complete_event.set()  # Initially ready for user input

    def record_with_threshold(self) -> bytes:
        """Record audio when voice threshold is exceeded, stop after silence."""
        # Check if Kai is currently speaking - if so, don't record
        if self.kai_is_speaking:
            return b""

        print("Listening for voice...")

        # Reset recording state
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start_time = None
        self.recording_complete = False

        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")

            # Double-check Kai isn't speaking during callback
            if self.kai_is_speaking:
                self.recording_complete = True
                return

            # Calculate RMS amplitude
            rms = np.sqrt(np.mean(indata**2))

            if rms > self.threshold:
                if not self.is_recording:
                    print("Voice detected, starting recording...")
                    self.is_recording = True
                    self.audio_buffer = []

                # Add audio data to buffer
                self.audio_buffer.extend(indata.flatten())
                self.silence_start_time = None
            elif self.is_recording:
                # Still recording but below threshold (silence)
                self.audio_buffer.extend(indata.flatten())

                if self.silence_start_time is None:
                    self.silence_start_time = time_module.time()
                elif (
                    time_module.time() - self.silence_start_time > self.silence_duration
                ):
                    print("Silence detected, stopping recording...")
                    self.recording_complete = True

        # Start recording stream
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=audio_callback,
            dtype=np.float32,
            blocksize=1024,
        ):
            # Use event-driven approach instead of polling with sleep
            import threading

            recording_event = threading.Event()

            def check_completion():
                while not self.recording_complete:
                    recording_event.wait(0.01)  # Non-blocking wait
                recording_event.set()

            completion_thread = threading.Thread(target=check_completion, daemon=True)
            completion_thread.start()

            # Wait for recording to complete
            recording_event.wait()

        if self.audio_buffer:
            # Convert to int16 for WAV format
            audio_data = np.array(self.audio_buffer, dtype=np.float32)
            audio_data = (audio_data * 32767).astype(np.int16)

            # Create WAV bytes
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data.tobytes())

            return wav_buffer.getvalue()

        return b""

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio using Whisper."""
        if not audio_bytes:
            return ""

        # Save to temporary file for Whisper
        temp_file = "temp_audio.wav"
        with open(temp_file, "wb") as f:
            f.write(audio_bytes)

        try:
            segments, _ = self.whisper_model.transcribe(temp_file)
            transcription = " ".join([segment.text for segment in segments])
            return transcription.strip()
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def generate_with_gemini(self, user_message: str) -> str:
        """Generate response using Gemini with tools and system prompt."""
        # Build system prompt with progress
        system_prompt = load_system_prompt()
        progress_context = self.state_manager.get_context_summary()
        if progress_context:
            system_prompt += f"\n\n## Current Progress Context:\n{progress_context}"

        # Add user message to conversation history
        self.conversation_history.append(
            {"role": "user", "parts": [{"text": user_message}]}
        )

        # Configure generation
        generation_config = types.GenerateContentConfig(
            system_instruction=system_prompt, tools=self.get_tools(), temperature=0.7
        )

        try:
            # Generate initial response
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self.conversation_history,
                config=generation_config,
            )

            # Process response and handle tools
            return self._process_response_with_tools(response, generation_config)

        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble processing that. Could you try again?"

    def _process_response_with_tools(self, response, generation_config) -> str:
        """Process response with SEQUENTIAL execution: TTS first, then tools."""
        # Set Kai speaking state to block recording
        self.kai_is_speaking = True
        self.turn_complete_event.clear()

        response_text = ""
        tool_calls = []

        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text
                elif hasattr(part, "function_call"):
                    # Collect tool calls but don't execute yet
                    tool_calls.append(part.function_call)

        # Add assistant response to history
        if response_text:
            self.conversation_history.append(
                {"role": "model", "parts": [{"text": response_text}]}
            )

        # SEQUENTIAL EXECUTION: TTS first, then tools
        if response_text and tool_calls:
            # Define callback to execute tools after TTS finishes
            def execute_tools_after_tts():
                self._execute_tools_and_follow_up(tool_calls, generation_config)

            # Play TTS with callback
            self.text_to_speech(response_text, callback=execute_tools_after_tts)
            return ""  # No immediate response, callback will handle follow-up

        elif response_text:
            # Just text, no tools - complete turn after TTS
            def complete_turn():
                self._complete_turn()

            self.text_to_speech(response_text, callback=complete_turn)
            return ""

        elif tool_calls:
            # Just tools, no text - execute tools directly
            self._execute_tools_and_follow_up(tool_calls, generation_config)
            return ""

        return ""

    def _execute_tools_and_follow_up(self, tool_calls, generation_config):
        """Execute tools and generate follow-up response."""
        tool_results = []
        for tool_call in tool_calls:
            result = self.execute_function(tool_call)
            tool_results.append({"function_name": tool_call.name, "result": result})
            print(f"Tool executed: {tool_call.name} -> {result}")

        # Generate follow-up response with tool results
        if tool_results:
            tool_context = self._format_tool_results(tool_results)
            follow_up_response = self._generate_tool_follow_up(
                tool_context, generation_config
            )

            # Play follow-up response with turn completion
            if follow_up_response:

                def complete_turn():
                    self._complete_turn()

                self.text_to_speech(follow_up_response, callback=complete_turn)
            else:
                # No follow-up response, complete turn directly
                self._complete_turn()
        else:
            # No tool results, complete turn
            self._complete_turn()

    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        """Format tool results into a context message for Kai."""
        if not tool_results:
            return ""

        context_parts = []
        for result in tool_results:
            context_parts.append(
                f"Tool '{result['function_name']}' executed: {result['result']}"
            )

        return (
            "Tool execution results: "
            + "; ".join(context_parts)
            + ". Now respond to the user based on these results."
        )

    def _generate_tool_follow_up(self, tool_context: str, generation_config) -> str:
        """Generate a follow-up response after tool execution."""
        # Add tool results as context to conversation
        self.conversation_history.append(
            {"role": "user", "parts": [{"text": tool_context}]}
        )

        try:
            # Generate follow-up response
            follow_up_response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=self.conversation_history,
                config=generation_config,
            )

            # Process follow-up (could have more tools)
            return self._process_response_with_tools(
                follow_up_response, generation_config
            )

        except Exception as e:
            print(f"Error in follow-up generation: {e}")
            return ""

    def _complete_turn(self) -> None:
        """Complete Kai's turn and allow user to speak again."""

        def delayed_turn_completion():
            # Add 1.5 second buffer to prevent TTS audio pickup
            threading.Event().wait(1.5)

            # Release speaking state and signal turn completion
            self.kai_is_speaking = False
            self.turn_complete_event.set()
            print("Turn completed - ready for user input")

        threading.Thread(target=delayed_turn_completion, daemon=True).start()

    def update_progress_file(self, new_observation: str) -> str:
        """Update the progress file."""
        self.state_manager.update_progress(new_observation)
        return "Progress successfully logged."

    def text_to_speech(self, text: str, callback=None) -> None:
        """Convert text to speech using Piper TTS and play it with optional callback."""
        if not text.strip():
            if callback:
                callback()
            return

        print(f"Kai: {text}")

        # Generate audio with Piper using temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        # Create WAV file object for Piper
        with wave.open(temp_path, "wb") as wav_file:
            self.tts_voice.synthesize_wav(text, wav_file, syn_config=self.syn_config)

        # Read the audio data from file
        with open(temp_path, "rb") as f:
            # Skip WAV header (44 bytes) and read raw audio data
            f.seek(44)
            audio_bytes = f.read()

        # Clean up temp file
        os.unlink(temp_path)

        # Convert to numpy array for pygame
        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        # Convert mono to stereo for pygame mixer
        if audio_data.ndim == 1:
            audio_data = np.column_stack((audio_data, audio_data))

        # Create pygame sound and play
        sound = pygame.sndarray.make_sound(audio_data)
        channel = sound.play()

        # If callback provided, monitor completion without blocking
        if callback and channel:

            def monitor_completion():
                # Use pygame's channel monitoring instead of sleep
                while channel.get_busy():
                    pass  # Busy-wait loop is more responsive than sleep
                callback()

            threading.Thread(target=monitor_completion, daemon=True).start()

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

    def execute_function(self, function_call: Any) -> Union[str, Dict[str, Any]]:
        """Execute a function call from the model."""
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
                args.get("audio_type"), args.get("volume", 0.7), args.get("clip_id")
            )
        elif function_name == "stop_audio":
            return self.audio_controller.stop_audio(args.get("audio_type"))
        elif function_name == "stop_all_audio":
            return self.audio_controller.stop_all_audio()
        elif function_name == "get_status":
            status = self.audio_controller.get_status()
            return status if isinstance(status, (str, dict)) else str(status)
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
                args.get("clip_id", 0),
                args.get("direction", "left_to_right"),
                args.get("speed", "moderate"),
            )
        elif function_name == "pan_pattern_pendulum":
            return self.audio_controller.pan_pattern_pendulum(
                args.get("clip_id", 0),
                args.get("cycles", 3),
                args.get("duration_per_cycle", 2.0),
            )
        elif function_name == "pan_pattern_alternating":
            return self.audio_controller.pan_pattern_alternating(
                args.get("clip_id", 0), args.get("interval", 1.0), args.get("cycles", 4)
            )
        elif function_name == "pan_to_side":
            return self.audio_controller.pan_to_side(
                args.get("clip_id", 0), args.get("side", "center")
            )
        elif function_name == "stop_panning_patterns":
            return self.audio_controller.stop_panning_patterns(args.get("clip_id"))
        elif function_name == "play_alert_sound":
            volume = args.get("volume", 0.7)
            return self.audio_controller.play_alert_sound(volume)
        else:
            return f"Unknown function: {function_name}"

    def start_conversation(self) -> None:
        """Start the voice conversation with welcome flow (only once)."""
        if not self.has_welcomed:
            self.has_welcomed = True
            # Brief greeting and readiness check
            welcome_prompt = "Give a brief greeting like 'Welcome back, glad to see you again' or similar, then ask if they're ready to get started again and recommend headphones. Wait for their response before proceeding with any training."

            # Generate and speak welcome message (handled internally now)
            self.generate_with_gemini(welcome_prompt)

        # Start the voice interaction loop
        threading.Thread(target=self.voice_interaction_loop, daemon=True).start()

    def voice_interaction_loop(self) -> None:
        """Main voice interaction loop - continuous listening and responding."""
        while True:
            try:
                # Wait for turn to be complete before starting new recording
                self.turn_complete_event.wait()

                # Double-check Kai isn't speaking
                if self.kai_is_speaking:
                    continue

                # Record audio when voice is detected
                audio_bytes = self.record_with_threshold()

                if audio_bytes:
                    # Transcribe the audio
                    user_text = self.transcribe_audio(audio_bytes)

                    if user_text.strip():
                        print(f"User: {user_text}")

                        # Generate response using Gemini
                        # The new system handles TTS and tool execution internally
                        self.generate_with_gemini(user_text)
                    else:
                        # Empty transcription - handle locally without sending to model
                        print("Empty transcription detected.")

                        def retry_turn():
                            self._complete_turn()

                        self.text_to_speech(
                            "I couldn't make out what you're saying, please try again.",
                            callback=retry_turn,
                        )
                else:
                    print("No audio recorded.")

            except KeyboardInterrupt:
                print("\nConversation ended by user.")
                self.text_to_speech("Goodbye! Great work today.")
                break
            except Exception as e:
                print(f"Error in conversation loop: {e}")
                continue
