import time
from threading import Lock, Thread
from typing import Dict, List, Optional

import pygame


class AudioMixer:
    """A class to manage audio playback using pygame.mixer."""

    def __init__(self, num_channels: int = 8) -> None:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.set_num_channels(num_channels)
        self.channels: List[pygame.mixer.Channel] = [
            pygame.mixer.Channel(i) for i in range(num_channels)
        ]
        self.lock: Lock = Lock()
        self._orig_volumes: Dict[int, float] = {}

    def play(
        self,
        sound: pygame.mixer.Sound,
        channel_idx: int,
        loops: int = 0,
        volume: float = 1.0,
    ) -> None:
        """Plays a sound on a specified channel.

        Args:
            sound: The sound to play.
            channel_idx: The index of the channel to play the sound on.
            loops: The number of times to loop the sound.
            volume: The volume to play the sound at.
        """
        with self.lock:
            ch = self.channels[channel_idx]
            ch.set_volume(volume)
            ch.play(sound, loops=loops)

    def queue_sound(self, channel_idx: int, sound: pygame.mixer.Sound) -> None:
        """Queues a sound on a channel or plays it immediately if the channel is free.

        Args:
            channel_idx: The index of the channel to queue the sound on.
            sound: The sound to queue.
        """
        with self.lock:
            ch = self.channels[channel_idx]
            if not ch.get_busy():
                ch.play(sound)
            else:
                ch.queue(sound)

    def stop(self, channel_idx: int) -> None:
        """Stops playback on a specified channel.

        Args:
            channel_idx: The index of the channel to stop.
        """
        with self.lock:
            if channel_idx < len(self.channels):
                self.channels[channel_idx].stop()

    def set_volume(self, channel_idx: int, volume: float) -> None:
        """Sets the volume for a specified channel.

        Args:
            channel_idx: The index of the channel to set the volume for.
            volume: The volume to set.
        """
        with self.lock:
            if channel_idx < len(self.channels):
                self.channels[channel_idx].set_volume(volume)

    def set_pan(self, channel_idx: int, pan: float) -> None:
        """Sets the stereo panning for a specified channel.

        Args:
            channel_idx: The index of the channel to set the pan for.
            pan: The panning value, from -1.0 (left) to 1.0 (right).
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

    def is_playing(self, channel_idx: int) -> bool:
        """Checks if a specified channel is currently playing a sound.

        Args:
            channel_idx: The index of the channel to check.

        Returns:
            True if the channel is playing, False otherwise.
        """
        if channel_idx < len(self.channels):
            return self.channels[channel_idx].get_busy()
        return False

    def stop_all(self) -> None:
        """Stops playback on all channels."""
        with self.lock:
            for ch in self.channels:
                ch.stop()

    def get_free_channel_index(self) -> int:
        """Returns the index of the first free channel, or expands the mixer if all are busy.

        Returns:
            The index of a free channel.
        """
        for idx, ch in enumerate(self.channels):
            if not ch.get_busy():
                return idx
        new_idx = len(self.channels)
        pygame.mixer.set_num_channels(new_idx + 1)
        self.channels.append(pygame.mixer.Channel(new_idx))
        return new_idx

    def duck_channels(
        self, enable: bool, factor: float = 0.3, exclude: Optional[List[int]] = None
    ) -> Dict[int, float]:
        """Ducks the volume of channels to help another track be heard more clearly.

        Args:
            enable: Whether to enable or disable ducking.
            factor: The factor to reduce the volume by.
            exclude: A list of channel indices to exclude from ducking.

        Returns:
            A dictionary of the updated channel volumes.
        """
        updated: Dict[int, float] = {}

        def _fade(
            idx: int, target: float, duration: float = 0.25, steps: int = 5
        ) -> None:
            start = self.channels[idx].get_volume()
            step_sleep = duration / steps
            for s in range(1, steps + 1):
                interp = start + (target - start) * (s / steps)
                with self.lock:
                    self.channels[idx].set_volume(interp)
                import threading

                delay_event = threading.Event()
                threading.Timer(step_sleep, delay_event.set).start()
                delay_event.wait()

        threads: List[Thread] = []
        if enable:
            for idx, ch in enumerate(self.channels):
                if exclude and idx in exclude:
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
                if exclude and idx in exclude:
                    continue
                updated[idx] = orig_vol
                t = Thread(target=_fade, args=(idx, orig_vol), daemon=True)
                t.start()
                threads.append(t)
                del self._orig_volumes[idx]
        return updated
