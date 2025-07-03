import datetime
import json
from pathlib import Path


class StateManager:
    def __init__(self, progress_file: str = "src/prompts/progress.json"):
        repo_root = Path(__file__).resolve().parents[2]
        self.progress_file = (repo_root / progress_file).resolve()

    def _read_state(self) -> dict:
        """Return persisted state or initialise blank structure when file is empty/missing."""
        if not self.progress_file.exists():
            default_state = {"sessions": []}
            self._write_state(default_state)
            return default_state

        content = self.progress_file.read_text(encoding="utf-8").strip()

        # Initialise blank state when file is empty
        if not content:
            default_state = {"sessions": []}
            self._write_state(default_state)
            return default_state

        return json.loads(content)

    def _write_state(self, state: dict):
        """Persist the current state to disk."""
        with self.progress_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def is_first_run(self) -> bool:
        """Return True when no previous sessions have been recorded."""
        state = self._read_state()
        return state.get("sessions") == []

    def update_progress(self, new_observation: str):
        """Append a raw observation string to today's session."""
        state = self._read_state()

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if not state.get("sessions") or state["sessions"][-1]["date"] != today:
            state.setdefault("sessions", []).append({"date": today, "observations": []})

        state["sessions"][-1]["observations"].append(new_observation)
        self._write_state(state)

    def get_context_summary(self) -> str:
        """Return a compact string summary for prompt injection."""
        state = self._read_state()
        lines = []
        if state.get("name"):
            lines.append(f"USER NAME: {state['name']}")
        for sess in state.get("sessions", [])[-5:]:
            lines.append(f"Session {sess['date']}:")
            for obs in sess["observations"][-5:]:
                lines.append(f"  - {obs}")
        return "\n".join(lines)

    def get_full_progress(self) -> str:
        """Return the complete progress JSON as a formatted string."""
        return json.dumps(self._read_state(), indent=2)

    def set_user_name(self, name: str, pronunciation: str | None = None):
        """Set the user's name and optional pronunciation."""
        state = self._read_state()
        state["name"] = name
        if pronunciation:
            state["pronunciation"] = pronunciation
        self._write_state(state)

    def update_field(self, field: str, value):
        """Update any top-level field and persist immediately."""
        state = self._read_state()
        state[field] = value
        self._write_state(state)
        return f"{field} updated"
