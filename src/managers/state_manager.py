import re
from pathlib import Path


class StateManager:
    def __init__(
        self,
        progress_file: str = "src/state/progress.md",
        leveling_file: str = "src/state/leveling.md",
    ):
        self.progress_file = Path(progress_file)
        self.leveling_file = Path(leveling_file)
        self.stages = self._parse_leveling_file()
        self._ensure_progress_file_exists()

    # --- Session Management Methods ---

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

This file is maintained by the AI coach to track the user's progress, strengths, and areas for improvement.

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

    # --- Stage Management Methods ---

    def _parse_leveling_file(self):
        content = self.leveling_file.read_text()
        stages = {}
        diagnostic_match = re.search(
            r"## Initial Diagnostic Assessment.*?\n(.*?)(?=## Stage Progression)",
            content,
            re.DOTALL,
        )
        if diagnostic_match:
            stages["diagnostic"] = self._parse_diagnostic(diagnostic_match.group(1))

        stage_blocks = content.split("**Stage ")[1:]
        for block in stage_blocks:
            num_match = re.match(r"(\d+)", block)
            if num_match:
                stage_num = int(num_match.group(1))
                stages[stage_num] = self._parse_stage(block)
        return stages

    def _parse_diagnostic(self, content):
        tests = {}
        pattern = re.compile(r"\*\*Diagnostic (\d+)\*\*: (.*?)\n")
        for match in pattern.finditer(content):
            tests[int(match.group(1))] = {"description": match.group(2).strip()}
        return {"tests": tests}

    def _parse_stage(self, content):
        data = {}
        title_match = re.search(r": (.*?)\*\*", content)
        if title_match:
            data["title"] = title_match.group(1).strip()
        elements_match = re.search(r"\*\*Audio Elements\*\*: (.*?)\n", content)
        if elements_match:
            data["audio_elements"] = elements_match.group(1).strip()
        duration_match = re.search(r"\*\*Duration\*\*: (.*?)\n", content)
        if duration_match:
            data["duration"] = duration_match.group(1).strip()
        return data

    def get_stage(self, stage_number: int):
        return self.stages.get(stage_number)

    def get_diagnostic(self):
        return self.stages.get("diagnostic")

    def get_current_stage_from_progress(self, progress_content: str):
        match = re.search(r"- \*\*Current Stage\*\*: (\d+)", progress_content)
        return int(match.group(1)) if match else 0

    def get_context_summary(self) -> str:
        """
        Generates a concise summary of the user's current state for the AI.
        """
        progress_content = self.get_progress()
        current_stage = self.get_current_stage_from_progress(progress_content)

        # Extract the last two AI observations
        observations_section = re.search(
            r"## AI Observations\n(.*?)(?=\n##|$)", progress_content, re.DOTALL
        )
        recent_observations = []
        if observations_section:
            # Find all observations, which start with "- YYYY-MM-DD:"
            all_obs = re.findall(
                r"- \d{4}-\d{2}-\d{2}:.*", observations_section.group(1)
            )
            # Take the most recent two
            recent_observations = [obs.strip() for obs in all_obs[:2]]

        # Build the summary string
        summary = f"USER CONTEXT: The user is currently at Stage {current_stage}."
        if recent_observations:
            obs_string = " ".join(recent_observations)
            summary += f" Recent observations: {obs_string}"

        # Don't add context if user is at stage 0 (first run)
        if current_stage == 0:
            return ""

        return summary
