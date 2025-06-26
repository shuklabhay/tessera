import numpy as np


class NoiseGenerator:
    def white(self, duration_sec, sample_rate=44100, amplitude=0.5):
        """Generate white noise with normal distribution."""
        n = int(duration_sec * sample_rate)
        return (np.random.normal(0, amplitude, n)).astype(np.float32)

    def pink(self, duration_sec, sample_rate=44100, amplitude=0.5):
        """Generate pink noise using IIR filter on white noise."""
        n = int(duration_sec * sample_rate)
        white = np.random.normal(0, amplitude, n)

        # IIR filter coefficients for pink noise
        b = [0.02109238, 0.07113478, 0.68873558]
        a = [1, -1.73472577, 0.7660066]
        pink = np.zeros(n)

        # Apply filter
        for i in range(2, n):
            pink[i] = (
                b[0] * white[i]
                + b[1] * white[i - 1]
                + b[2] * white[i - 2]
                - a[1] * pink[i - 1]
                - a[2] * pink[i - 2]
            )
        return pink.astype(np.float32)

    def brown(self, duration_sec, sample_rate=44100, amplitude=0.5):
        """Generate brown noise by integrating white noise."""
        n = int(duration_sec * sample_rate)
        white = np.random.normal(0, amplitude, n)

        # Integrate white noise to get brown noise
        brown = np.cumsum(white)

        # Normalize to desired amplitude
        brown = brown / np.max(np.abs(brown)) * amplitude
        return brown.astype(np.float32)
