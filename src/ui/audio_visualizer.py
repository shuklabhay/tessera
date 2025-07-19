from typing import Optional

import numpy as np


class AudioVisualizer:
    """
    Processes audio data to calculate a smoothed amplitude for visualization.
    """

    def __init__(self, window_size: int = 1024, smoothing: float = 0.9) -> None:
        self.window_size = window_size
        self.smoothing = smoothing
        self.current_amplitude = 0.0

    def process_audio(self, audio_data: Optional[bytes]) -> float:
        """Processes a chunk of audio data and updates the smoothed amplitude.

        Args:
            audio_data: The input audio data in bytes, or None if no audio is received.

        Returns:
            The newly calculated and smoothed amplitude value as a float.
        """
        if not audio_data:
            self.current_amplitude *= 0.95
            return float(self.current_amplitude)

        audio_data_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        rms_amplitude = np.sqrt(np.mean(np.square(audio_data_np)))
        normalized_amplitude = max(0.0, min(1.0, rms_amplitude / 32768.0))
        self.current_amplitude = (
            self.smoothing * self.current_amplitude
            + (1.0 - self.smoothing) * normalized_amplitude
        )
        return float(self.current_amplitude)

    def get_current_amplitude(self) -> float:
        """Returns the current smoothed amplitude.

        Returns:
            The current smoothed amplitude value as a float.
        """
        return self.current_amplitude
