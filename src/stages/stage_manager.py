import re
from pathlib import Path


class StageManager:
    def __init__(self, leveling_file: str = "src/state/leveling.md"):
        self.leveling_file = Path(leveling_file)
        self.stages = self._parse_leveling_file()

    def _parse_leveling_file(self):
        content = self.leveling_file.read_text()
        stages = {}

        # Parse diagnostic
        diagnostic_content_match = re.search(
            r"## Initial Diagnostic Assessment.*?\n(.*?)(?=## Stage Progression)",
            content,
            re.DOTALL,
        )
        if diagnostic_content_match:
            stages["diagnostic"] = self._parse_diagnostic(
                diagnostic_content_match.group(1)
            )

        # Parse stages by splitting the document by the stage marker
        stage_blocks = content.split("**Stage ")[1:]
        for block in stage_blocks:
            stage_number_match = re.match(r"(\d+)", block)
            if stage_number_match:
                stage_number = int(stage_number_match.group(1))
                stages[stage_number] = self._parse_stage(block)

        return stages

    def _parse_diagnostic(self, content):
        diagnostic_tests = {}
        test_pattern = re.compile(r"\*\*Diagnostic (\d+)\*\*: (.*?)\n")
        matches = test_pattern.finditer(content)
        for match in matches:
            test_num = int(match.group(1))
            description = match.group(2)
            diagnostic_tests[test_num] = {"description": description.strip()}
        return {"tests": diagnostic_tests}

    def _parse_stage(self, content):
        stage_data = {}

        # Extract title from "1: Single Stream Focus**"
        title_match = re.search(r": (.*?)\*\*", content)
        if title_match:
            stage_data["title"] = title_match.group(1).strip()

        elements_match = re.search(r"\*\*Audio Elements\*\*: (.*?)\n", content)
        if elements_match:
            stage_data["audio_elements"] = elements_match.group(1).strip()

        duration_match = re.search(r"\*\*Duration\*\*: (.*?)\n", content)
        if duration_match:
            stage_data["duration"] = duration_match.group(1).strip()

        return stage_data

    def get_stage(self, stage_number: int):
        return self.stages.get(stage_number)

    def get_diagnostic(self):
        return self.stages.get("diagnostic")

    def get_current_stage_from_progress(self, progress_content: str):
        match = re.search(r"- \*\*Current Stage\*\*: (\d+)", progress_content)
        if match:
            return int(match.group(1))
        return 0
