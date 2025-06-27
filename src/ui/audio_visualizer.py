import numpy as np


class AudioVisualizer:
    def __init__(self, window_size=1024, smoothing=0.9):
        self.window_size = window_size
        self.smoothing = smoothing
        self.current_amplitude = 0.0

    def process_audio(self, audio_data):
        """Process audio data to compute amplitude for visualization."""
        if not audio_data:
            # Apply decay when no audio
            self.current_amplitude *= 0.95
            return float(self.current_amplitude)

        # Convert bytes to numpy array
        audio_data_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)

        # Calculate RMS amplitude (root mean square of samples)
        rms_amplitude = np.sqrt(np.mean(np.square(audio_data_np)))

        # Normalize to 0–1 (16-bit signed range)
        normalized_amplitude = max(0.0, min(1.0, rms_amplitude / 32768.0))

        # Exponential moving average smoothing
        self.current_amplitude = (
            self.smoothing * self.current_amplitude
            + (1.0 - self.smoothing) * normalized_amplitude
        )

        return float(self.current_amplitude)

    def get_current_amplitude(self):
        """Get the current smoothed amplitude value."""
        return self.current_amplitude

    def update_orb(self, amplitude):
        """Update orb based on amplitude (placeholder method)."""
        pass
