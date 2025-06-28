import datetime
import json
from pathlib import Path


class StateManager:
    def __init__(self, progress_file: str = "src/prompts/progress.json"):
        root = Path(__file__).resolve().parents[2]  # project root
        self.progress_file = (root / progress_file).resolve()
        self._ensure_progress_file_exists()

    def _ensure_progress_file_exists(self):
        if not self.progress_file.exists():
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_state({"name": None, "pronunciation": None, "sessions": []})

    def _read_state(self) -> dict:
        """Return persisted state, falling back to an empty schema if file is missing or malformed."""
        try:
            with self.progress_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Reset to a blank structure on corruption/missing file
            default_state = {"name": None, "pronunciation": None, "sessions": []}
            self._write_state(default_state)
            return default_state

    def _write_state(self, state: dict):
        with self.progress_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def is_first_run(self) -> bool:
        state = self._read_state()
        return state.get("sessions") == []

    def update_progress(self, new_observation: str):
        """Append an observation to the latest session (create session if needed)."""
        state = self._read_state()
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        if not state["sessions"] or state["sessions"][-1]["date"] != today:
            state["sessions"].append({"date": today, "observations": []})

        # Name capture heuristics
        lower_obs = new_observation.lower()
        name_candidate = None

        if lower_obs.startswith("user name captured:"):
            # Expected pattern from system prompt
            name_candidate = new_observation.split(":", 1)[1].strip()
        elif lower_obs.startswith("name:"):
            name_candidate = new_observation.split(":", 1)[1].strip()
        elif lower_obs.startswith("my name is"):
            name_candidate = new_observation.split("is", 1)[1].strip()

        if name_candidate:
            state["name"] = name_candidate
            state["pronunciation"] = None  # Placeholder for future extension

        state["sessions"][-1]["observations"].append(new_observation)
        self._write_state(state)

    def get_context_summary(self) -> str:
        """Return a compact string summary for prompt injection."""
        state = self._read_state()
        lines = []
        if state.get("name"):
            lines.append(f"USER NAME: {state['name']}")
        for sess in state.get("sessions", [])[-5:]:  # last 5 sessions
            lines.append(f"Session {sess['date']}:")
            for obs in sess["observations"][-5:]:
                lines.append(f"  - {obs}")
        return "\n".join(lines)

    # Optional future helper
    def set_user_name(self, name: str, pronunciation: str | None = None):
        state = self._read_state()
        state["name"] = name
        if pronunciation:
            state["pronunciation"] = pronunciation
        self._write_state(state)

    # Generic field updater exposed to LLM tools
    def update_field(self, field: str, value):
        """Update a top-level field (e.g., name or pronunciation) and persist immediately."""
        allowed = {"name", "pronunciation", "progress"}
        if field not in allowed:
            return f"Unsupported field: {field}"

        state = self._read_state()
        if field == "progress":
            # Expect value to be a JSON-serialisable object; store inside today's session
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            if not state["sessions"] or state["sessions"][-1]["date"] != today:
                state["sessions"].append({"date": today, "observations": []})
            state["sessions"][-1]["observations"].append(value)
        else:
            state[field] = value
        self._write_state(state)
        return f"{field} updated"
