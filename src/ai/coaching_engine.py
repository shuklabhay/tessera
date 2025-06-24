import re
from datetime import datetime

from session.session_manager import SessionManager
from stages.stage_manager import StageManager


class CoachingEngine:
    def __init__(self, session_manager: SessionManager, stage_manager: StageManager):
        self.session_manager = session_manager
        self.stage_manager = stage_manager

    def update_progress_log(self, summary: str) -> str:
        """
        Updates the user's progress log with a new summary and advances them to the next stage.
        """
        try:
            # Get current state
            progress_content = self.session_manager.get_progress()
            current_stage = self.stage_manager.get_current_stage_from_progress(
                progress_content
            )
            new_stage = current_stage + 1
            today_date = datetime.now().strftime("%Y-%m-%d")

            # Update Last Session Date
            progress_content = re.sub(
                r"(- \*\*Last Session Date\*\*: ).*",
                rf"\1{today_date}",
                progress_content,
            )

            # Update Current Stage
            progress_content = re.sub(
                r"(- \*\*Current Stage\*\*: ).*",
                rf"\1{new_stage}",
                progress_content,
            )

            # Append the new summary under AI Observations
            # We'll add it to the top of the list for easy reading.
            new_observation = f"- {today_date}: {summary}"
            progress_content = re.sub(
                r"(## AI Observations\n)",
                rf"\1\n{new_observation}",
                progress_content,
            )

            # Save the updated progress
            self.session_manager.save_progress(progress_content)

            return f"Progress successfully logged. User is now at stage {new_stage}."
        except Exception as e:
            # In a real scenario, you'd want more robust logging here
            print(f"Error updating progress log: {e}")
            return "An error occurred while trying to log progress."
