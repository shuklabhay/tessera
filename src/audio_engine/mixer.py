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
        """Play sound on specified channel."""
        with self.lock:
            ch = self.channels[channel_idx]
            ch.set_volume(volume)
            ch.play(sound, loops=loops)

    def queue_sound(self, channel_idx, sound):
        """Queue sound on channel or play immediately if channel is free."""
        with self.lock:
            ch = self.channels[channel_idx]
            if not ch.get_busy():
                ch.play(sound)
            else:
                ch.queue(sound)

    def stop(self, channel_idx):
        """Stop playback on specified channel."""
        with self.lock:
            if channel_idx < len(self.channels):
                self.channels[channel_idx].stop()

    def set_volume(self, channel_idx, volume):
        """Set volume for specified channel."""
        with self.lock:
            if channel_idx < len(self.channels):
                self.channels[channel_idx].set_volume(volume)

    def set_pan(self, channel_idx, pan):
        """Set stereo panning for specified channel."""
        with self.lock:
            if channel_idx < len(self.channels):
                channel = self.channels[channel_idx]
                current_volume = channel.get_volume()

                # Calculate left/right multipliers
                left_multiplier = (-(pan - 1) / 2) ** 0.5
                right_multiplier = ((pan + 1) / 2) ** 0.5

                # Apply panning
                channel.set_volume(
                    current_volume * left_multiplier, current_volume * right_multiplier
                )

    def is_playing(self, channel_idx):
        """Check if specified channel is currently playing."""
        if channel_idx < len(self.channels):
            return self.channels[channel_idx].get_busy()
        return False

    def stop_all(self):
        """Stop playback on all channels."""
        with self.lock:
            for ch in self.channels:
                ch.stop()

    def get_free_channel_index(self):
        """Return index of first free channel, or None if all busy."""
        for idx, ch in enumerate(self.channels):
            if not ch.get_busy():
                return idx

        # Expand mixer channels if all are busy
        new_idx = len(self.channels)
        pygame.mixer.set_num_channels(new_idx + 1)
        self.channels.append(pygame.mixer.Channel(new_idx))
        return new_idx
