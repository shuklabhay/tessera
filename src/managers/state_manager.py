import datetime
import json
from pathlib import Path
from typing import Any, Dict


class StateManager:
    """
    Manages the state of the application, including progress and session data.
    """

    def __init__(self, progress_file: str = "src/prompts/progress.json") -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.progress_file = (repo_root / progress_file).resolve()

    def _read_state(self) -> Dict[str, Any]:
        """Reads state from progress file, initializing if empty.

        Returns:
            Dict[str, Any]: The application state.
        """
        if not self.progress_file.exists():
            default_state = {"sessions": []}
            self._write_state(default_state)
            return default_state

        content = self.progress_file.read_text(encoding="utf-8").strip()

        if not content:
            default_state = {"sessions": []}
            self._write_state(default_state)
            return default_state

        return json.loads(content)

    def _write_state(self, state: Dict[str, Any]) -> None:
        """Writes the provided state to the progress file.

        Args:
            state (Dict[str, Any]): The state to persist.
        """
        with self.progress_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def is_first_run(self) -> bool:
        """Checks if this is the first run of the application.

        Returns:
            bool: True if no sessions are recorded, otherwise False.
        """
        state = self._read_state()
        return state.get("sessions") == []

    def update_progress(self, new_observation: str) -> None:
        """Adds a new observation to the current session.

        Args:
            new_observation (str): The observation to add.
        """
        state = self._read_state()
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        if not state.get("sessions") or state["sessions"][-1]["date"] != today:
            state.setdefault("sessions", []).append({"date": today, "observations": []})

        state["sessions"][-1]["observations"].append(new_observation)
        self._write_state(state)

    def get_context_summary(self) -> str:
        """Generates a summary of recent sessions.

        Returns:
            str: A summary of the last 5 sessions.
        """
        state = self._read_state()
        lines = []

        for sess in state.get("sessions", [])[-5:]:
            lines.append(f"Session {sess['date']}:")
            for obs in sess["observations"][-5:]:
                lines.append(f"  - {obs}")

        return "\n".join(lines)

    def get_full_progress(self) -> str:
        """Returns the complete progress data as a JSON string.

        Returns:
            str: The entire state as a JSON string.
        """
        return json.dumps(self._read_state(), indent=2)

    def update_field(self, field: str, value: Any) -> str:
        """Updates a top-level field in the state.

        Args:
            field (str): The field to update.
            value (Any): The new value for the field.

        Returns:
            str: A confirmation message.
        """
        state = self._read_state()
        state[field] = value
        self._write_state(state)
        return f"{field} updated"
