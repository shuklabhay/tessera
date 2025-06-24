import os
import random
from threading import Lock, Thread

from pydub import AudioSegment

AUDIO_DIRS = {
    "environmental": "audio/environmental",
    "noise": "audio/noise",
    "speakers": "audio/speakers",
}


class AudioLoader:
    def __init__(self):
        self.cache = {k: [] for k in AUDIO_DIRS}
        self.lock = Lock()
        self._start_background_cache()

    def _scan_files(self, category):
        path = AUDIO_DIRS[category]
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith(".wav")
        ]

    def get_random_file(self, category):
        files = self._scan_files(category)
        if not files:
            return None
        return random.choice(files)

    def load_audio(self, filepath):
        return AudioSegment.from_wav(filepath)

    def get_random_audio(self, category):
        filepath = self.get_random_file(category)
        if not filepath:
            return None
        return self.load_audio(filepath)

    def _cache_category(self, category):
        files = self._scan_files(category)
        loaded = []
        for f in files:
            try:
                loaded.append(self.load_audio(f))
            except Exception:
                continue
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
                return None
            return random.choice(self.cache[category])
