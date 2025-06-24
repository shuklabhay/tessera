import numpy as np


class NoiseGenerator:
    def white(self, duration_sec, sample_rate=44100, amplitude=0.5):
        n = int(duration_sec * sample_rate)
        return (np.random.normal(0, amplitude, n)).astype(np.float32)

    def pink(self, duration_sec, sample_rate=44100, amplitude=0.5):
        n = int(duration_sec * sample_rate)
        white = np.random.normal(0, amplitude, n)
        b = [0.02109238, 0.07113478, 0.68873558]
        a = [1, -1.73472577, 0.7660066]
        pink = np.zeros(n)
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
        n = int(duration_sec * sample_rate)
        white = np.random.normal(0, amplitude, n)
        brown = np.cumsum(white)
        brown = brown / np.max(np.abs(brown)) * amplitude
        return brown.astype(np.float32)
