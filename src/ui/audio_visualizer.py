import numpy as np


class AudioVisualizer:
    def __init__(self, window_size=1024, smoothing=0.3):
        self.window_size = window_size
        self.smoothing = smoothing
        self.current_amplitude = 0
        self.target_amplitude = 0

    def process_audio(self, audio_data):
        """
        Process audio data to compute amplitude for visualization.
        """
        if not audio_data:
            return 0.0

        audio_data_np = np.frombuffer(audio_data, dtype=np.int16)

        # Now calculate amplitude
        amplitude = np.mean(np.abs(audio_data_np))

        # Normalize the amplitude to a 0-1 range
        # The max value for int16 is 32767
        normalized_amplitude = amplitude / 32767.0
        self.target_amplitude = normalized_amplitude
        self.current_amplitude = (
            self.smoothing * self.current_amplitude
            + (1.0 - self.smoothing) * self.target_amplitude
        )
        # Amplify for visibility and convert to standard Python float for Kivy
        return float(min(normalized_amplitude * 5, 1.0))

    def get_current_amplitude(self):
        return self.current_amplitude

    def update_orb(self, amplitude):
        """
        Update the orb based on the given amplitude.
        """
        # Implementation of update_orb method
        pass
