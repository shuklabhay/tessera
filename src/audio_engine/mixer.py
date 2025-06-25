from threading import Lock

import pygame


class AudioMixer:
    def __init__(self, num_channels=8):
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.set_num_channels(num_channels)
        self.channels = [pygame.mixer.Channel(i) for i in range(num_channels)]
        self.lock = Lock()

    def play(self, sound, channel_idx, loops=0, volume=1.0):
        with self.lock:
            ch = self.channels[channel_idx]
            ch.set_volume(volume)
            ch.play(sound, loops=loops)

    def stop(self, channel_idx):
        with self.lock:
            if channel_idx < len(self.channels):
                self.channels[channel_idx].stop()

    def set_volume(self, channel_idx, volume):
        with self.lock:
            if channel_idx < len(self.channels):
                self.channels[channel_idx].set_volume(volume)

    def set_pan(self, channel_idx, pan):
        """
        Sets the stereo panning for a channel.
        """
        with self.lock:
            if channel_idx < len(self.channels):
                channel = self.channels[channel_idx]
                current_volume = channel.get_volume()

                left_multiplier = (-(pan - 1) / 2) ** 0.5
                right_multiplier = ((pan + 1) / 2) ** 0.5

                channel.set_volume(
                    current_volume * left_multiplier, current_volume * right_multiplier
                )

    def is_playing(self, channel_idx):
        if channel_idx < len(self.channels):
            return self.channels[channel_idx].get_busy()
        return False

    def stop_all(self):
        with self.lock:
            for ch in self.channels:
                ch.stop()
