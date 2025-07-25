import os
import ssl
import threading
from typing import Dict, List, Union

import certifi
from dotenv import load_dotenv
from google.genai import types

from audio_engine.audio_controller import AudioController
from managers.state_manager import StateManager
from services.gemini_service import GeminiService
from services.recording_service import RecordingService
from services.transcription_service import TranscriptionService
from services.tts_service import TextToSpeechService
from managers.tool_register import ToolRegister

ssl._create_default_https_context = ssl._create_unverified_context
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
load_dotenv()


class ConversationService:
    """
    Manages the complete voice conversation flow between user and AI.
    """

    def __init__(
        self, audio_controller: AudioController, state_manager: StateManager
    ) -> None:
        self.audio_controller = audio_controller
        self.state_manager = state_manager
        self.tool_registry = ToolRegister(audio_controller, state_manager)

        self.recording_service = RecordingService()
        self.transcription_service = TranscriptionService()
        self.tts_service = TextToSpeechService(
            model_path="models/en_US-hfc_male-medium.onnx",
            config_path="models/en_US-hfc_male-medium.onnx.json",
        )
        self.gemini_service = GeminiService(
            state_manager=self.state_manager, tools=self.tool_registry.get_tools()
        )

        self.turn_complete_event = threading.Event()
        self.turn_complete_event.set()
        self.has_welcomed = False
        self.running = False

    def start(self) -> None:
        """
        Starts the conversation with welcome message and voice loop.
        """
        self.running = True

        if not self.has_welcomed:
            self.has_welcomed = True
            welcome_prompt = "Give a brief greeting like 'Welcome back, glad to see you again' or similar, then ask if they're ready to get started again and recommend headphones. Wait for their response before proceeding with any training."
            response = self.gemini_service.generate_with_gemini(welcome_prompt)
            self._handle_ai_response(response)

        self._start_voice_loop()

    def _start_voice_loop(self) -> None:
        """
        Starts the main voice interaction loop in a separate thread.
        """

        def voice_interaction_loop():
            while self.running:
                self.turn_complete_event.wait()
                if not self.running:
                    break

                audio_bytes = self.recording_service.record_with_threshold()

                if audio_bytes:
                    user_text = self.transcription_service.transcribe_audio(audio_bytes)

                    if user_text.strip():
                        print(f"User: {user_text}")
                        response = self.gemini_service.generate_with_gemini(user_text)
                        self._handle_ai_response(response)
                    else:
                        print("Could not understand audio")
                else:
                    print("No audio recorded.")

        threading.Thread(target=voice_interaction_loop, daemon=True).start()

    def _handle_ai_response(self, response: types.GenerateContentResponse) -> None:
        """
        Handles the response from the AI service.

        Args:
            response: The response from the AI service.
        """
        response_text = ""
        tool_calls: List[types.FunctionCall] = []

        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text
                elif hasattr(part, "function_call") and part.function_call:
                    tool_calls.append(part.function_call)

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

    def _execute_tools_during_speech(
        self, response_text: str, tool_calls: List[types.FunctionCall]
    ) -> None:
        """
        Executes tools immediately while speech is playing.

        Args:
            response_text: The text to speak
            tool_calls: A list of tool calls to execute during speech.
        """

        def execute_tools_immediately():
            for tool_call in tool_calls:
                result = self.tool_registry.execute_function(tool_call)
                print(f"Tool executed during speech: {tool_call.name} -> {result}")

        threading.Thread(target=execute_tools_immediately, daemon=True).start()
        self.tts_service.text_to_speech(response_text, callback=self._complete_turn)

    def _execute_tools_and_follow_up(
        self, tool_calls: List[types.FunctionCall]
    ) -> None:
        """
        Executes tools and generates a follow-up response.

        Args:
            tool_calls: A list of tool calls to execute.
        """
        tool_results = []
        for tool_call in tool_calls:
            result = self.tool_registry.execute_function(tool_call)
            tool_results.append({"function_name": tool_call.name, "result": result})
            print(f"Tool executed: {tool_call.name} -> {result}")

        if tool_results:
            tool_context = self._format_tool_results(tool_results)
            follow_up_response = self.gemini_service.generate_tool_follow_up(
                tool_context
            )
            self._handle_ai_response(follow_up_response)
        else:
            self._complete_turn()

    def _format_tool_results(
        self, tool_results: List[Dict[str, Union[str, int]]]
    ) -> str:
        """
        Formats tool results into a context message for the LLM.

        Args:
            tool_results: A list of tool results.

        Returns:
            A formatted string of tool results.
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
        """
        Completes the assistant's turn and allows user input again.
        """

        def delayed_turn_completion():
            threading.Event().wait(1.5)
            self.recording_service.set_kai_is_speaking(False)
            self.audio_controller.restore_background_after_tts()
            self.turn_complete_event.set()
            print("Turn completed - ready for user input")

        threading.Thread(target=delayed_turn_completion, daemon=True).start()

    def is_speaking(self) -> bool:
        """
        Checks if the AI is currently speaking.

        Returns:
            True if speaking, False otherwise.
        """
        return not self.turn_complete_event.is_set()

    def stop(self) -> None:
        """
        Stops the conversation manager.
        """
        self.running = False
        self.turn_complete_event.set()
