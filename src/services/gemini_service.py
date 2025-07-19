import os
from typing import Dict, List

import google.genai as genai
from google.genai import types

from managers.state_manager import StateManager


def load_system_prompt() -> str:
    """
    Loads the system prompt from a file.

    Returns:
        str: The system prompt.
    """
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "system_prompt.md"
    )
    with open(prompt_path, "r") as file:
        return file.read()


class GeminiService:
    """
    Handles all communication with the Gemini LLM.
    """

    def __init__(self, state_manager: StateManager, tools: List[types.Tool]) -> None:
        self.state_manager = state_manager
        self.tools = tools
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.conversation_history: List[types.Content] = []

    def generate_with_gemini(self, user_message: str) -> types.GenerateContentResponse:
        """
        Generates a response from the Gemini LLM.

        Args:
            user_message (str): The user's message.

        Returns:
            types.GenerateContentResponse: The response from the Gemini LLM.
        """
        system_prompt = load_system_prompt()
        progress_context = self.state_manager.get_context_summary()
        if progress_context:
            system_prompt += f"\n\n## Current Progress Context:\n{progress_context}"

        user_content = types.UserContent(
            parts=[types.Part.from_text(text=user_message)]
        )
        self.conversation_history.append(user_content)

        generation_config = types.GenerateContentConfig(
            system_instruction=system_prompt, tools=self.tools, temperature=0.7
        )

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=self.conversation_history,
            config=generation_config,
        )

        if response.candidates and response.candidates[0].content:
            self.conversation_history.append(response.candidates[0].content)

        return response

    def generate_tool_follow_up(
        self, tool_context: str
    ) -> types.GenerateContentResponse:
        """
        Generates a follow-up response after a tool has been executed.

        Args:
            tool_context (str): The context from the tool's execution.

        Returns:
            types.GenerateContentResponse: The response from the Gemini LLM.
        """
        tool_content = types.UserContent(
            parts=[types.Part.from_text(text=tool_context)]
        )
        self.conversation_history.append(tool_content)

        generation_config = types.GenerateContentConfig(
            system_instruction=load_system_prompt(), tools=self.tools, temperature=0.7
        )

        follow_up_response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=self.conversation_history,
            config=generation_config,
        )

        if follow_up_response.candidates and follow_up_response.candidates[0].content:
            self.conversation_history.append(follow_up_response.candidates[0].content)

        return follow_up_response
