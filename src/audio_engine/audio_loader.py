import os
import random
from threading import Lock, Thread

from pydub import AudioSegment

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

AUDIO_DIRS = {
    "environmental": os.path.join(PROJECT_ROOT, "audio", "environmental"),
    "noise": os.path.join(PROJECT_ROOT, "audio", "noise"),
    "speakers": os.path.join(PROJECT_ROOT, "audio", "speakers"),
}


class AudioLoader:
    def __init__(self):
        self.cache = {k: [] for k in AUDIO_DIRS}
        self.lock = Lock()
        self._start_background_cache()

    def _scan_files(self, category):
        path = AUDIO_DIRS[category]
        if not os.path.exists(path):
            return []

        files = [
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith((".wav", ".mp3", ".ogg"))
        ]
        return files

    def get_random_file(self, category):
        files = self._scan_files(category)
        if not files:
            return None
        return random.choice(files)

    def load_audio(self, filepath):
        if filepath.lower().endswith(".wav"):
            return AudioSegment.from_wav(filepath)
        elif filepath.lower().endswith(".mp3"):
            return AudioSegment.from_mp3(filepath)
        elif filepath.lower().endswith(".ogg"):
            return AudioSegment.from_ogg(filepath)
        else:
            return AudioSegment.from_file(filepath)

    def get_random_audio(self, category):
        filepath = self.get_random_file(category)
        if not filepath:
            return None
        return self.load_audio(filepath)

    def _normalize_audio(self, audio_segment, target_dbfs=-20.0):
        """Normalizes the audio to a target dBFS."""
        if audio_segment.dBFS == float("-inf"):
            return audio_segment  # Avoid division by zero for silent audio
        change_in_dbfs = target_dbfs - audio_segment.dBFS
        return audio_segment.apply_gain(change_in_dbfs)

    def _cache_category(self, category):
        files = self._scan_files(category)
        loaded = []
        for f in files:
            audio = self.load_audio(f)
            if audio is not None:
                normalized_audio = self._normalize_audio(audio)
                # Store both the audio object and its original file path
                loaded.append({"audio": normalized_audio, "filepath": f})
        with self.lock:
            self.cache[category] = loaded

    def _background_cache(self):
        for category in AUDIO_DIRS:
            self._cache_category(category)

    def _start_background_cache(self):
        t = Thread(target=self._background_cache, daemon=True)
        t.start()

    def get_cached_audio(self, category):
        with self.lock:
            if not self.cache[category]:
                return None, None
            selected_item = random.choice(self.cache[category])
            audio = selected_item["audio"]
            filepath = selected_item["filepath"]
            return audio, filepath
