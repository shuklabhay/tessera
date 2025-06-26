import numpy as np


class AudioVisualizer:
    def __init__(self, window_size=1024, smoothing=0.3):
        self.window_size = window_size
        self.smoothing = smoothing
        self.current_amplitude = 0
        self.target_amplitude = 0

    def process_audio(self, audio_data):
        """Process audio data to compute amplitude for visualization."""
        if not audio_data:
            return 0.0

        # Convert bytes to numpy array and calculate amplitude
        audio_data_np = np.frombuffer(audio_data, dtype=np.int16)
        amplitude = np.mean(np.abs(audio_data_np))

        # Normalize to 0-1 range (int16 max is 32767)
        normalized_amplitude = amplitude / 32767.0
        self.target_amplitude = normalized_amplitude

        # Apply smoothing
        self.current_amplitude = (
            self.smoothing * self.current_amplitude
            + (1.0 - self.smoothing) * self.target_amplitude
        )

        # Amplify for visibility and clamp to [0, 1]
        return float(min(normalized_amplitude * 5, 1.0))

    def get_current_amplitude(self):
        """Get the current smoothed amplitude value."""
        return self.current_amplitude

    def update_orb(self, amplitude):
        """Update orb based on amplitude (placeholder method)."""
        pass
