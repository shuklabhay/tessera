import os
import random
from threading import Lock, Thread

import numpy as np
import soundfile as sf

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

AUDIO_DIRS = {
    "environmental": os.path.join(PROJECT_ROOT, "audio", "environmental"),
    "noise": os.path.join(PROJECT_ROOT, "audio", "noise"),
    "speakers": os.path.join(PROJECT_ROOT, "audio", "speakers"),
    "alerts": os.path.join(PROJECT_ROOT, "audio", "alerts"),
}


class AudioLoader:
    def __init__(self):
        self.paths = AUDIO_DIRS

    def _scan_files(self, category):
        """Scan directory for audio files in the given category."""
        path = self.paths.get(category)
        if not path:
            print(f"Warning: No path configured for category '{category}'")
            return []

        if not os.path.exists(path):
            print(f"Warning: Audio directory {path} does not exist")
            return []

        # Find supported audio files
        files = [
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith((".wav", ".mp3", ".ogg"))
        ]
        print(
            f"Found {len(files)} audio files in {category}: {[os.path.basename(f) for f in files]}"
        )
        return files

    def get_random_file(self, category):
        """Get a random audio file path from the specified category."""
        files = self._scan_files(category)
        if not files:
            return None
        return random.choice(files)

    def load_audio(self, filepath):
        """Load and process audio file to 24kHz stereo format."""
        data, _ = sf.read(
            filepath,
            dtype="float32",
            always_2d=True,
        )
        return data

    def get_random_audio(self, category):
        """Get a random loaded audio file and its path from the specified category."""
        filepath = self.get_random_file(category)
        if not filepath:
            return None, None
        audio = self.load_audio(filepath)
        return audio, filepath

    def get_cached_audio(self, category):
        """Return freshly loaded random audio (no caching)."""
        audio, filepath = self.get_random_audio(category)
        if audio is not None:
            audio = self._normalize_audio(audio)
        return audio, filepath

    def _normalize_audio(self, audio):
        """Normalize audio to [-1, 1] range."""
        if audio is None:
            return None
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val
        return audio
