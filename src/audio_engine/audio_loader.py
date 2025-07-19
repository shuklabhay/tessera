import os
import random
from threading import Lock, Thread
from typing import List, Optional, Tuple

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
    """
    A class to load and process audio files from specified directories.
    """

    def __init__(self) -> None:
        self.paths = AUDIO_DIRS

    def _scan_files(self, category: str) -> List[str]:
        """Scans a directory for audio files in the given category.

        Args:
            category: The category of audio files to scan for.

        Returns:
            A list of file paths for the found audio files.
        """
        path = self.paths.get(category)
        if not path:
            print(f"Warning: No path configured for category '{category}'")
            return []

        if not os.path.exists(path):
            print(f"Warning: Audio directory {path} does not exist")
            return []

        files = [
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith((".wav", ".mp3", ".ogg"))
        ]

        return files

    def get_random_file(self, category: str) -> Optional[str]:
        """Gets a random audio file path from the specified category.

        Args:
            category: The category from which to get a random file.

        Returns:
            The path to a random audio file, or None if no files are found.
        """
        files = self._scan_files(category)
        if not files:
            return None
        return random.choice(files)

    def load_audio(self, filepath: str) -> np.ndarray:
        """Loads and processes an audio file to a 24kHz stereo format.

        Args:
            filepath: The path to the audio file to load.

        Returns:
            The audio data as a NumPy array.
        """
        data, sample_rate = sf.read(filepath, dtype="float32")

        if len(data.shape) == 1:
            data = np.column_stack([data, data])
        elif data.shape[1] > 2:
            data = data[:, :2]

        if sample_rate != 24000:
            target_length = int(len(data) * 24000 / sample_rate)
            if len(data.shape) == 2:
                resampled_left = np.interp(
                    np.linspace(0, len(data) - 1, target_length),
                    np.arange(len(data)),
                    data[:, 0],
                )
                resampled_right = np.interp(
                    np.linspace(0, len(data) - 1, target_length),
                    np.arange(len(data)),
                    data[:, 1],
                )
                data = np.column_stack([resampled_left, resampled_right])
            else:
                resampled = np.interp(
                    np.linspace(0, len(data) - 1, target_length),
                    np.arange(len(data)),
                    data,
                )
                data = np.column_stack([resampled, resampled])

        return data

    def get_random_audio(
        self, category: str
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """Gets a randomly loaded audio file and its path from the specified category.

        Args:
            category: The category from which to get random audio.

        Returns:
            A tuple containing the audio data and filepath.
        """
        filepath = self.get_random_file(category)
        if not filepath:
            return None, None
        audio = self.load_audio(filepath)
        return audio, filepath

    def get_cached_audio(
        self, category: str
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """Returns a freshly loaded and normalized random audio file.

        Args:
            category: The category from which to get the audio.

        Returns:
            A tuple containing the normalized audio data and filepath.
        """
        audio, filepath = self.get_random_audio(category)
        if audio is not None:
            audio = self._normalize_audio(audio)
        return audio, filepath

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalizes audio data to a range of [-1, 1].

        Args:
            audio: The audio data to normalize.

        Returns:
            The normalized audio data.
        """
        if audio is None:
            return None
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val
        return audio
