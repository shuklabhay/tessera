import os
from typing import Any, Dict, List

import google.genai as genai
from google.genai import types

from managers.state_manager import StateManager


def load_system_prompt() -> str:
    """Loads the system prompt from a file.

    Returns:
        str: The system prompt.
    """
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "system_prompt.md"
    )
    with open(prompt_path, "r") as file:
        return file.read()


class GeminiService:
    """Handles all communication with the Gemini LLM."""

    def __init__(self, state_manager: StateManager, tools: List[types.Tool]):
        self.state_manager = state_manager
        self.tools = tools
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.conversation_history = []

    def generate_with_gemini(self, user_message: str) -> Dict[str, Any]:
        """Generates a response from the Gemini LLM.

        Args:
            user_message (str): The user's message.

        Returns:
            Dict[str, Any]: A dictionary containing the response text and any tool calls.
        """
        system_prompt = load_system_prompt()
        progress_context = self.state_manager.get_context_summary()
        if progress_context:
            system_prompt += f"\n\n## Current Progress Context:\n{progress_context}"

        self.conversation_history.append(
            {"role": "user", "parts": [{"text": user_message}]}
        )

        generation_config = types.GenerateContentConfig(
            system_instruction=system_prompt, tools=self.tools, temperature=0.7
        )

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=self.conversation_history,
            config=generation_config,
        )
        return self._process_response(response)

    def _process_response(
        self, response: types.GenerateContentResponse
    ) -> Dict[str, Any]:
        """Processes the LLM's response.

        Args:
            response (GenerateContentResponse): The response from the Gemini LLM.

        Returns:
            Dict[str, Any]: A dictionary containing the response text and any tool calls.
        """
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
                    tool_calls.append(part.function_call)

        if response_text:
            self.conversation_history.append(
                {"role": "model", "parts": [{"text": response_text}]}
            )

        return {"text": response_text, "tool_calls": tool_calls}

    def generate_tool_follow_up(self, tool_context: str) -> Dict[str, Any]:
        """Generates a follow-up response after a tool has been executed.

        Args:
            tool_context (str): The context from the tool's execution.

        Returns:
            Dict[str, Any]: A dictionary containing the response text and any tool calls.
        """
        self.conversation_history.append(
            {"role": "user", "parts": [{"text": tool_context}]}
        )

        generation_config = types.GenerateContentConfig(
            system_instruction=load_system_prompt(), tools=self.tools, temperature=0.7
        )

        follow_up_response = self.client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=self.conversation_history,
            config=generation_config,
        )
        return self._process_response(follow_up_response)
