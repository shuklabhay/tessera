import io
import threading
import wave
from typing import Callable, Optional

import numpy as np
import pygame
from piper import PiperVoice, SynthesisConfig


class TextToSpeechService:
    """Handles text-to-speech conversion and playback."""

    def __init__(self, model_path: str, config_path: str):
        self.tts_voice = PiperVoice.load(model_path, config_path)
        self.syn_config = SynthesisConfig(length_scale=1.5, noise_scale=0.333)
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)

    def text_to_speech(
        self, text: str, callback: Optional[Callable[[], None]] = None
    ) -> None:
        """Converts text to speech and plays it, with an optional callback on completion.

        Args:
            text (str): The text to convert to speech.
            callback (Optional[Callable[[], None]]): A function to call when playback finishes.
        """
        if not text.strip():
            if callback:
                callback()
            return

        print(f"Kai: {text}")

        # Synthesize audio to an in-memory buffer
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            self.tts_voice.synthesize_wav(text, wav_file, syn_config=self.syn_config)

        # Reset buffer position to the beginning to read from it
        wav_buffer.seek(0)

        # Read audio data from the in-memory buffer
        with wave.open(wav_buffer, "rb") as wav_file:
            audio_bytes = wav_file.readframes(wav_file.getnframes())

        # Convert to numpy array for pygame
        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        # Convert mono to stereo for pygame mixer
        if audio_data.ndim == 1:
            audio_data = np.column_stack((audio_data, audio_data))

        # Create pygame sound and play
        sound = pygame.sndarray.make_sound(audio_data)
        channel = sound.play()

        if callback and channel:

            def monitor_completion():
                while channel.get_busy():
                    pygame.time.wait(10)
                callback()

            threading.Thread(target=monitor_completion, daemon=True).start()
