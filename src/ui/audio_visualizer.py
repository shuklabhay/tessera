import numpy as np


class AudioVisualizer:
    def __init__(self, window_size=1024, smoothing=0.3):
        self.window_size = window_size
        self.smoothing = smoothing
        self.current_amplitude = 0
        self.target_amplitude = 0

    def process_audio(self, audio_data):
        if audio_data is None:
            return 0.0
        if isinstance(audio_data, (float, int)):
            return 0.0
        if len(audio_data) == 0:
            return 0.0
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)
        abs_data = np.abs(audio_data)
        if len(abs_data) > 0:
            rms_amplitude = np.sqrt(np.mean(np.square(abs_data)))
            normalized = min(1.0, rms_amplitude / 10000.0)
            self.target_amplitude = normalized
            self.current_amplitude = (
                self.smoothing * self.current_amplitude
                + (1.0 - self.smoothing) * self.target_amplitude
            )
            return self.current_amplitude
        return 0.0

    def get_current_amplitude(self):
        return self.current_amplitude
