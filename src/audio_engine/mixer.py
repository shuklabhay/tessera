from threading import Lock

import pygame


class AudioMixer:
    def __init__(self, num_channels=8):
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
            self.channels[channel_idx].stop()

    def set_volume(self, channel_idx, volume):
        with self.lock:
            self.channels[channel_idx].set_volume(volume)

    def is_playing(self, channel_idx):
        return self.channels[channel_idx].get_busy()

    def stop_all(self):
        with self.lock:
            for ch in self.channels:
                ch.stop()
