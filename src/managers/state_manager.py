import datetime
from pathlib import Path


class StateManager:
    def __init__(self, progress_file: str = "src/state/progress.md"):
        self.progress_file = Path(progress_file)
        self._ensure_progress_file_exists()

    def _ensure_progress_file_exists(self):
        """
        Creates the progress file with a default template if it doesn't exist.
        """
        if not self.progress_file.exists():
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            self.progress_file.touch()
            self.reset_progress()

    def is_first_run(self) -> bool:
        """
        Checks if this is the user's first session.
        A first run is defined by the progress file being empty or containing
        the initial placeholder text.
        """
        content = self.get_progress().strip()
        return not content or "No sessions yet." in content

    def get_progress(self) -> str:
        """
        Reads the entire content of the progress file.
        """
        return self.progress_file.read_text()

    def update_progress(self, new_observation: str):
        """
        Appends a new observation to the progress file.
        """
        current_content = self.get_progress()
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # Prepare the new entry
        entry = f"- {date_str}: {new_observation}\n"

        # If it's the first real entry, replace the placeholder
        if "No sessions yet." in current_content:
            new_content = f"# User Progress Journal\n\n## AI Observations\n{entry}"
        else:
            new_content = current_content + entry

        self.progress_file.write_text(new_content)

    def reset_progress(self):
        """
        Resets the progress file to its initial state.
        """
        initial_content = """# User Progress Journal

## AI Observations
- No sessions yet.
"""
        self.progress_file.write_text(initial_content)

    def get_context_summary(self) -> str:
        """
        Generates a concise summary of the user's progress for the AI.
        If it's the first run, returns an empty string to trigger the diagnostic.
        """
        if self.is_first_run():
            return ""

        progress_content = self.get_progress()
        return f"USER CONTEXT:\n{progress_content}"
