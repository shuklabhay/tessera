from pathlib import Path


class SessionManager:
    def __init__(self, progress_file: str = "src/state/progress.md"):
        self.progress_file = Path(progress_file)
        self._ensure_progress_file_exists()

    def _ensure_progress_file_exists(self):
        if not self.progress_file.exists():
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            self.progress_file.touch()
            self.reset_progress()

    def get_progress(self) -> str:
        return self.progress_file.read_text()

    def save_progress(self, content: str):
        self.progress_file.write_text(content)

    def reset_progress(self):
        initial_content = """# User Progress Journal

This file is maintained by the AI coach to track the user's progress, strengths, and areas for improvement. It serves as the foundation for creating personalized, freeform training sessions.

## Session Summary

- **Last Session Date**: None
- **Current Stage**: 0
- **Total Training Time**: 0 minutes

## AI Observations

### Strengths

- None noted yet.

### Areas for Improvement

- None noted yet.

## Freeform Goals

- Start with the diagnostic test.
"""
        self.save_progress(initial_content)
