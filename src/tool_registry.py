from typing import Dict, List, Union

from google.genai import types

from audio_engine.audio_controller import AudioController
from managers.state_manager import StateManager


class ToolRegistry:
    """
    Manages tool definitions and execution for the LLM.
    """

    def __init__(self, audio_controller: AudioController, state_manager: StateManager) -> None:
        self.audio_controller = audio_controller
        self.state_manager = state_manager

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

    def execute_function(self, function_call: types.FunctionCall) -> Union[str, Dict[str, Union[str, int]]]:
        """Executes a function call from the model.

        Args:
            function_call: The function call to execute.

        Returns:
            The result of the function call.
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
                args.get("volume", 0.7), args.get("clip_id")
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
                return self._update_progress_file(summary)
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

    def _update_progress_file(self, new_observation: str) -> str:
        """Updates the progress file with a new observation.

        Args:
            new_observation (str): The new observation to log.

        Returns:
            str: Success message.
        """
        self.state_manager.update_progress(new_observation)
        return "Progress successfully logged."