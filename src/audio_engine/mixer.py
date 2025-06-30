import time
from threading import Lock, Thread

import pygame


class AudioMixer:
    def __init__(self, num_channels=8):
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.set_num_channels(num_channels)
        self.channels = [pygame.mixer.Channel(i) for i in range(num_channels)]
        self.lock = Lock()
        self._orig_volumes = {}

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

    def duck_channels(self, enable: bool, factor: float = 0.3, exclude=None):
        """Duck tracks to help hear spoken tracks."""
        updated = {}

        # Helper for smooth fade
        def _fade(idx: int, target: float, duration: float = 0.25, steps: int = 5):
            start = self.channels[idx].get_volume()
            step_sleep = duration / steps
            for s in range(1, steps + 1):
                interp = start + (target - start) * (s / steps)
                with self.lock:
                    self.channels[idx].set_volume(interp)
                time.sleep(step_sleep)

        threads = []

        if enable:
            for idx, ch in enumerate(self.channels):
                if idx in exclude:
                    continue
                if idx not in self._orig_volumes:
                    self._orig_volumes[idx] = ch.get_volume()
                new_volume = self._orig_volumes[idx] * factor
                updated[idx] = new_volume
                t = Thread(target=_fade, args=(idx, new_volume), daemon=True)
                t.start()
                threads.append(t)
        else:
            for idx, orig_vol in list(self._orig_volumes.items()):
                if idx in exclude:
                    continue
                updated[idx] = orig_vol
                t = Thread(target=_fade, args=(idx, orig_vol), daemon=True)
                t.start()
                threads.append(t)
                del self._orig_volumes[idx]

        return updated
