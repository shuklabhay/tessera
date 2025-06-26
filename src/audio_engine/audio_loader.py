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
        path = self.paths.get(category)
        if not path:
            print(f"Warning: No path configured for category '{category}'")
            return []

        if not os.path.exists(path):
            print(f"Warning: Audio directory {path} does not exist")
            return []

        try:
            files = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if f.lower().endswith((".wav", ".mp3", ".ogg"))
            ]
            print(
                f"Found {len(files)} audio files in {category}: {[os.path.basename(f) for f in files]}"
            )
            return files
        except Exception as e:
            print(f"Error scanning {path}: {e}")
            return []

    def get_random_file(self, category):
        files = self._scan_files(category)
        if not files:
            return None
        return random.choice(files)

    def load_audio(self, filepath):
        try:
            if filepath.lower().endswith(".wav"):
                return AudioSegment.from_wav(filepath)
            elif filepath.lower().endswith(".mp3"):
                return AudioSegment.from_mp3(filepath)
            elif filepath.lower().endswith(".ogg"):
                return AudioSegment.from_ogg(filepath)
            else:
                return AudioSegment.from_file(filepath)
        except Exception as e:
            print(f"Error loading audio file {filepath}: {e}")
            return None

    def get_random_audio(self, category):
        filepath = self.get_random_file(category)
        if not filepath:
            return None, None
        audio = self.load_audio(filepath)
        return audio, filepath

    def get_cached_audio(self, category):
        with self.lock:
            if category in self.cache and self.cache[category]:
                return random.choice(self.cache[category]), None
        audio, filepath = self.get_random_audio(category)
        return audio, filepath

    def _normalize_audio(self, audio):
        return audio.normalize()

    def preload_category(self, category):
        print(f"Preloading {category} audio files...")
        files = self._scan_files(category)
        loaded = []
        for f in files:
            try:
                audio = self.load_audio(f)
                if audio is not None:
                    normalized_audio = self._normalize_audio(audio)
                    loaded.append(normalized_audio)
            except Exception as e:
                print(f"Error loading {f}: {e}")
                continue
        with self.lock:
            self.cache[category] = loaded
        print(f"Cached {len(loaded)} {category} audio files")

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
