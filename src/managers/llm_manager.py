import os
import ssl
import threading
from typing import Any, Dict, List, Union

import certifi
from dotenv import load_dotenv
from google.genai import types

from audio_engine.audio_controller import AudioController
from managers.state_manager import StateManager
from services.gemini_service import GeminiService
from services.recording_service import RecordingService
from services.transcription_service import TranscriptionService
from services.tts_service import TextToSpeechService

ssl._create_default_https_context = ssl._create_unverified_context
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
load_dotenv()


class LLMManager:
    """Orchestrates the voice interaction between the user and the system."""

    def __init__(
        self, audio_controller: AudioController, state_manager: StateManager
    ) -> None:
        self.audio_controller = audio_controller
        self.state_manager = state_manager

        self.recording_service = RecordingService()
        self.transcription_service = TranscriptionService()
        self.tts_service = TextToSpeechService(
            model_path="models/en_US-hfc_male-medium.onnx",
            config_path="models/en_US-hfc_male-medium.onnx.json",
        )
        self.gemini_service = GeminiService(
            state_manager=self.state_manager, tools=self.get_tools()
        )

        self.has_welcomed = False
        self.turn_complete_event = threading.Event()
        self.turn_complete_event.set()

    def start_conversation(self) -> None:
        """Starts the voice conversation with a welcome flow."""
        if not self.has_welcomed:
            self.has_welcomed = True
            welcome_prompt = "Give a brief greeting like 'Welcome back, glad to see you again' or similar, then ask if they're ready to get started again and recommend headphones. Wait for their response before proceeding with any training."
            response = self.gemini_service.generate_with_gemini(welcome_prompt)
            self.handle_gemini_response(response)

        threading.Thread(target=self.voice_interaction_loop, daemon=True).start()

    def voice_interaction_loop(self) -> None:
        """The main voice interaction loop."""
        while True:
            self.turn_complete_event.wait()
            audio_bytes = self.recording_service.record_with_threshold()

            if audio_bytes:
                user_text = self.transcription_service.transcribe_audio(audio_bytes)

                if user_text.strip():
                    print(f"User: {user_text}")
                    response = self.gemini_service.generate_with_gemini(user_text)
                    self.handle_gemini_response(response)
                else:
                    self.tts_service.text_to_speech(
                        "I couldn't make out what you're saying, please try again.",
                        callback=self._complete_turn,
                    )
            else:
                print("No audio recorded.")

    def handle_gemini_response(self, response: Dict[str, Any]) -> None:
        """Handles a response from the Gemini service.

        Args:
            response (Dict[str, Any]): The response from the Gemini service.
        """
        response_text = response.get("text")
        tool_calls = response.get("tool_calls")

        self.recording_service.set_kai_is_speaking(True)
        self.turn_complete_event.clear()

        if response_text and tool_calls:
            self._execute_tools_during_speech(response_text, tool_calls)
        elif response_text:
            self.tts_service.text_to_speech(response_text, callback=self._complete_turn)
        elif tool_calls:
            self._execute_tools_and_follow_up(tool_calls)
        else:
            self._complete_turn()

    def _execute_tools_during_speech(self, response_text: str, tool_calls: List[Any]) -> None:
        """Executes tools immediately while speech is playing, not after.

        Args:
            response_text (str): The text to speak
            tool_calls (List[Any]): A list of tool calls to execute during speech.
        """
        def execute_tools_immediately():
            for tool_call in tool_calls:
                result = self.execute_function(tool_call)
                print(f"Tool executed during speech: {tool_call.name} -> {result}")
        
        threading.Thread(target=execute_tools_immediately, daemon=True).start()
        self.tts_service.text_to_speech(response_text, callback=self._complete_turn)

    def _execute_tools_and_follow_up(self, tool_calls: List[Any]) -> None:
        """Executes tools and generates a follow-up response.

        Args:
            tool_calls (List[Any]): A list of tool calls to execute.
        """
        tool_results = []
        for tool_call in tool_calls:
            result = self.execute_function(tool_call)
            tool_results.append({"function_name": tool_call.name, "result": result})
            print(f"Tool executed: {tool_call.name} -> {result}")

        if tool_results:
            tool_context = self._format_tool_results(tool_results)
            follow_up_response = self.gemini_service.generate_tool_follow_up(
                tool_context
            )
            self.handle_gemini_response(follow_up_response)
        else:
            self._complete_turn()

    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        """Formats tool results into a context message for the LLM.

        Args:
            tool_results (List[Dict]): A list of tool results.

        Returns:
            str: A formatted string of tool results.
        """
        if not tool_results:
            return ""
        context_parts = [
            f"Tool '{result['function_name']}' executed: {result['result']}"
            for result in tool_results
        ]
        return (
            "Tool execution results: "
            + "; ".join(context_parts)
            + ". Now respond to the user based on these results."
        )

    def _complete_turn(self) -> None:
        """Completes the assistant's turn and allows user input again."""

        def delayed_turn_completion():
            threading.Event().wait(1.5)
            self.recording_service.set_kai_is_speaking(False)
            self.turn_complete_event.set()
            print("Turn completed - ready for user input")

        threading.Thread(target=delayed_turn_completion, daemon=True).start()

    def update_progress_file(self, new_observation: str) -> str:
        """Updates the progress file.

        Args:
            new_observation (str): The new observation to log.

        Returns:
            str: A confirmation message.
        """
        self.state_manager.update_progress(new_observation)
        return "Progress successfully logged."

    def get_tools(self) -> List[types.Tool]:
        """Gets the available tools.

        Returns:
            List[types.Tool]: A list of available tools.
        """
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
        """Executes a function call from the model.

        Args:
            function_call (Any): The function call to execute.

        Returns:
            Union[str, Dict[str, Any]]: The result of the function call.
        """
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

    def stop(self):
        """Stops the LLM manager."""
        pass
