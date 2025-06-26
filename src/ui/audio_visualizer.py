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

        # Convert bytes to numpy array
        audio_data_np = np.frombuffer(audio_data, dtype=np.int16)

        # Calculate RMS amplitude
        rms_amplitude = np.sqrt(np.mean(audio_data_np.astype(np.float64) ** 2))

        # Normalize amplitude to 0-1 range
        normalized_amplitude = rms_amplitude / 32767.0

        # Convert to dB, handling case of silence
        if normalized_amplitude > 0:
            db_amplitude = 20 * np.log10(normalized_amplitude)
        else:
            db_amplitude = -60.0  # Represents silence

        # Map dB to a 0-1 scale for visualization (-60dB to 0dB range)
        min_db = -60.0
        scaled_amplitude = (db_amplitude - min_db) / (-min_db)
        scaled_amplitude = max(0.0, min(1.0, scaled_amplitude))  # Clamp to 0-1

        # Apply smoothing
        self.target_amplitude = scaled_amplitude
        self.current_amplitude = (
            self.smoothing * self.current_amplitude
            + (1.0 - self.smoothing) * self.target_amplitude
        )

        return float(self.current_amplitude)

    def get_current_amplitude(self):
        """Get the current smoothed amplitude value."""
        return self.current_amplitude

    def update_orb(self, amplitude):
        """Update orb based on amplitude (placeholder method)."""
        pass
