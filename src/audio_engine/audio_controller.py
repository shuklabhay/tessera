import os
import threading
import time

import numpy as np
import pygame

from audio_engine.audio_loader import AudioLoader
from audio_engine.mixer import AudioMixer

MAX_VOLUME = 0.8


class AudioController:
    def __init__(self):
        pygame.mixer.pre_init(frequency=24000, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        self.loader = AudioLoader()
        self.mixer = AudioMixer()
        self.clips = {}
        self._next_clip_id = 1
        self.channel_map = {"gemini": 7}
        self._ducked = False
        self._panning_threads = {}

    def play_gemini_chunk(self, audio_chunk_bytes):
        """Play raw audio chunk from Gemini as stereo sound."""
        if not audio_chunk_bytes:
            return

        # Convert bytes to numpy array
        mono_array = np.frombuffer(audio_chunk_bytes, dtype=np.int16)

        # Convert mono to stereo
        stereo_array = np.column_stack([mono_array, mono_array])

        # Create and queue sound
        sound_chunk = pygame.sndarray.make_sound(stereo_array)
        self.mixer.queue_sound(self.channel_map["gemini"], sound_chunk)

    def _get_audio_description(self, filepath):
        """Get description from companion .txt file if it exists."""
        if not filepath:
            return "No description available."

        # Look for description file
        dir_name, file_name = os.path.split(filepath)
        base_name, _ = os.path.splitext(file_name)
        desc_path = os.path.join(dir_name, f"{base_name}.txt")

        # Try to read description
        if os.path.exists(desc_path):
            with open(desc_path, "r") as f:
                return f.read().strip()
        return "No description available."

    def play_environmental_sound(self, volume=0.7):
        """Play a random environmental soundscape on loop."""
        volume = max(0.0, min(MAX_VOLUME, volume))
        audio, filepath = self.loader.get_cached_audio("environmental")
        if audio is not None:
            # Convert for pygame
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            # Allocate channel
            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            self.mixer.play(sound, channel, loops=-1, volume=volume)

            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "environmental",
                "channel": channel,
                "volume": volume,
                "pan": 0.0,
                "description": description,
            }
            return {
                "clip_id": clip_id,
                "description": description,
                "type": "environmental",
            }
        return "No environmental sounds available"

    def play_speaker_sound(self, volume=0.7):
        """Play a random person speaking audio on loop."""
        volume = max(0.0, min(MAX_VOLUME, volume))
        audio, filepath = self.loader.get_cached_audio("speakers")
        if audio is not None:
            # Convert to int16 for pygame and ensure contiguous memory
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            # Allocate channel
            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            self.mixer.play(sound, channel, loops=-1, volume=volume)

            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "speakers",
                "channel": channel,
                "volume": volume,
                "pan": 0.0,
                "description": description,
            }
            return {"clip_id": clip_id, "description": description, "type": "speakers"}
        return "No speaker audio available"

    def play_noise_sound(self, volume=0.7):
        """Play a random noise sound on loop."""
        volume = max(0.0, min(MAX_VOLUME, volume))
        audio, filepath = self.loader.get_cached_audio("noise")
        if audio is not None:
            # Convert to int16 for pygame and ensure contiguous memory
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            # Allocate channel
            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            self.mixer.play(sound, channel, loops=-1, volume=volume)

            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "noise",
                "channel": channel,
                "volume": volume,
                "pan": 0.0,
                "description": description,
            }
            return {"clip_id": clip_id, "description": description, "type": "noise"}
        return "No noise audio available"

    def play_alert_sound(self, volume=0.7):
        """Play a random alert sound one-shot (no loop)."""
        volume = max(0.0, min(MAX_VOLUME, volume))
        audio, filepath = self.loader.get_cached_audio("alerts")
        if audio is not None:
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            self.mixer.play(sound, channel, loops=0, volume=volume)

            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "alerts",
                "channel": channel,
                "volume": volume,
                "pan": 0.0,
                "description": description,
            }
            return {"clip_id": clip_id, "description": description, "type": "alerts"}
        return "No alert sounds available"

    def pan_audio(self, audio_type, pan, clip_id=None):
        """Pan an audio source left or right. If clip_id given, target that clip only."""
        pan = max(-1.0, min(1.0, pan))

        if clip_id is None:
            return "clip_id required."

        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        clip = self.clips.get(cid_int)
        if not clip:
            return f"Unknown clip_id {clip_id}."
        self.mixer.set_pan(clip["channel"], pan)
        clip["pan"] = pan
        return f"Panned clip {cid_int} to {pan}."

    def adjust_volume(self, audio_type, volume, clip_id=None):
        """Adjust volume globally for type or for specific clip."""
        volume = max(0.0, min(1.0, volume))
        volume = min(MAX_VOLUME, volume)

        if clip_id is None:
            return "clip_id required."

        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        clip = self.clips.get(cid_int)
        if not clip:
            return f"Unknown clip_id {clip_id}."
        self.mixer.set_volume(clip["channel"], volume)
        clip["volume"] = volume
        return f"Volume for clip {cid_int} set to {int(volume*100)}%"

    def stop_audio(self, audio_type=None):
        """Stop a specific audio type or all audio if none specified."""
        if audio_type and not audio_type == "clip":
            to_remove = [
                cid for cid, m in self.clips.items() if m["type"] == audio_type
            ]
            for cid in to_remove:
                self.mixer.stop(self.clips[cid]["channel"])
                del self.clips[cid]
            return f"Stopped {audio_type} audio"
        elif audio_type == "clip":
            return "Use stop_audio with clip_id parameter (not implemented via tools)."
        elif not audio_type:
            # Stop all audio
            return self.stop_all_audio()
        return f"No active {audio_type} stream to stop"

    def get_status(self):
        """Get current audio playback status."""
        if not self.clips:
            return []
        return [
            {
                "clip_id": cid,
                "type": meta["type"],
                "volume": meta["volume"],
                "pan": meta["pan"],
                "description": meta["description"],
            }
            for cid, meta in self.clips.items()
        ]

    def stop_all_audio(self):
        """Stop all active audio streams."""
        # Stop all panning patterns first
        for cid in list(self._panning_threads.keys()):
            self._stop_panning_thread(cid)

        self.mixer.stop_all()
        self.clips.clear()
        return "Stopped all audio streams."

    def duck_background(self, enable: bool, factor: float = 0.3):
        """Duck or restore background volumes using the mixer utility."""
        # Skip if state unchanged
        if (enable and self._ducked) or (not enable and not self._ducked):
            return

        # Exclude Gemini narration channel from ducking
        exclude = (
            [self.channel_map.get("gemini")] if "gemini" in self.channel_map else []
        )

        # Perform ducking via mixer and get updated volumes
        updated = self.mixer.duck_channels(enable, factor, exclude=exclude)

        # Sync metadata with new volumes
        for _, meta in self.clips.items():
            ch_idx = meta["channel"]
            if ch_idx in updated:
                if enable:
                    meta["_orig_volume"] = meta.get("_orig_volume", meta["volume"])
                else:
                    if "_orig_volume" in meta:
                        del meta["_orig_volume"]
                meta["volume"] = updated[ch_idx]

        self._ducked = enable

    # Internal util
    def _get_free_non_reserved_channel(self):
        reserved = set(self.channel_map.values())
        for idx in range(len(self.mixer.channels)):
            if idx in reserved:
                continue
            if not self.mixer.channels[idx].get_busy():
                return idx
        return None

    # Advanced Panning Pattern Methods
    def _stop_panning_thread(self, clip_id):
        """Stop any active panning animation for a clip."""
        if clip_id in self._panning_threads:
            self._panning_threads[clip_id]["stop"] = True
            self._panning_threads[clip_id]["thread"].join(timeout=1.0)
            del self._panning_threads[clip_id]

    def _smooth_pan_transition(
        self, clip_id, start_pan, end_pan, duration_seconds, steps=20
    ):
        """Smoothly transition pan position over time."""
        clip = self.clips.get(clip_id)
        if not clip:
            return

        sleep_time = duration_seconds / steps
        step_size = (end_pan - start_pan) / steps

        thread_info = self._panning_threads.get(clip_id, {})

        for step in range(steps + 1):
            if thread_info.get("stop", False):
                break

            current_pan = start_pan + (step_size * step)
            current_pan = max(-1.0, min(1.0, current_pan))

            self.mixer.set_pan(clip["channel"], current_pan)
            clip["pan"] = current_pan

            if step < steps:  # Don't sleep on last iteration
                time.sleep(sleep_time)

    def pan_pattern_sweep(self, clip_id, direction="left_to_right", speed="moderate"):
        """Sweep audio across stereo field."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop any existing panning for this clip
        self._stop_panning_thread(cid_int)

        # Set duration based on speed
        speed_durations = {"slow": 10.0, "moderate": 5.0, "fast": 2.0}
        if isinstance(speed, str) and speed in speed_durations:
            duration = speed_durations[speed]
        elif isinstance(speed, (int, float)):
            duration = float(speed)
        else:
            duration = 5.0  # Default to moderate

        # Set start/end positions based on direction
        if direction == "left_to_right":
            start_pan, end_pan = -1.0, 1.0
        elif direction == "right_to_left":
            start_pan, end_pan = 1.0, -1.0
        elif direction == "center_out":
            # First move to center, then sweep out
            self.pan_audio(None, 0.0, cid_int)
            start_pan, end_pan = 0.0, 1.0
        else:
            start_pan, end_pan = -1.0, 1.0

        # Create and start panning thread
        thread_info = {"stop": False}
        thread = threading.Thread(
            target=self._smooth_pan_transition,
            args=(cid_int, start_pan, end_pan, duration),
            daemon=True,
        )
        thread_info["thread"] = thread
        self._panning_threads[cid_int] = thread_info
        thread.start()

        return f"Started {direction} sweep for clip {cid_int} over {duration}s"

    def pan_pattern_pendulum(self, clip_id, cycles=3, duration_per_cycle=3.0):
        """Create pendulum back-and-forth panning motion."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop any existing panning
        self._stop_panning_thread(cid_int)

        def pendulum_motion():
            clip = self.clips.get(cid_int)
            if not clip:
                return

            thread_info = self._panning_threads.get(cid_int, {})
            steps_per_cycle = 40
            sleep_time = duration_per_cycle / steps_per_cycle

            for cycle in range(cycles):
                if thread_info.get("stop", False):
                    break

                # Swing left to right
                for step in range(steps_per_cycle // 2):
                    if thread_info.get("stop", False):
                        break
                    pan = -1.0 + (2.0 * step / (steps_per_cycle // 2))
                    pan = max(-1.0, min(1.0, pan))
                    self.mixer.set_pan(clip["channel"], pan)
                    clip["pan"] = pan
                    time.sleep(sleep_time)

                # Swing right to left
                for step in range(steps_per_cycle // 2):
                    if thread_info.get("stop", False):
                        break
                    pan = 1.0 - (2.0 * step / (steps_per_cycle // 2))
                    pan = max(-1.0, min(1.0, pan))
                    self.mixer.set_pan(clip["channel"], pan)
                    clip["pan"] = pan
                    time.sleep(sleep_time)

        # Create and start thread
        thread_info = {"stop": False}
        thread = threading.Thread(target=pendulum_motion, daemon=True)
        thread_info["thread"] = thread
        self._panning_threads[cid_int] = thread_info
        thread.start()

        return f"Started pendulum motion for clip {cid_int} - {cycles} cycles"

    def pan_pattern_alternating(self, clip_id, interval=2.0, cycles=5):
        """Alternate between left and right positions."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop any existing panning
        self._stop_panning_thread(cid_int)

        def alternating_motion():
            clip = self.clips.get(cid_int)
            if not clip:
                return

            thread_info = self._panning_threads.get(cid_int, {})
            positions = [-0.8, 0.8]  # Slightly inward from extreme positions

            for cycle in range(cycles):
                if thread_info.get("stop", False):
                    break

                pan = positions[cycle % 2]
                self.mixer.set_pan(clip["channel"], pan)
                clip["pan"] = pan

                time.sleep(interval)

        # Create and start thread
        thread_info = {"stop": False}
        thread = threading.Thread(target=alternating_motion, daemon=True)
        thread_info["thread"] = thread
        self._panning_threads[cid_int] = thread_info
        thread.start()

        return f"Started alternating pattern for clip {cid_int} - {cycles} cycles at {interval}s intervals"

    def pan_to_side(self, clip_id, side):
        """Quickly pan audio to specified side."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop any existing panning animation
        self._stop_panning_thread(cid_int)

        # Map side to pan value
        side_map = {
            "left": -0.8,
            "right": 0.8,
            "center": 0.0,
            "hard_left": -1.0,
            "hard_right": 1.0,
            "slight_left": -0.3,
            "slight_right": 0.3,
        }

        pan = side_map.get(side.lower(), 0.0)

        return self.pan_audio(None, pan, cid_int)

    def stop_panning_patterns(self, clip_id=None):
        """Stop panning patterns for specific clip or all clips."""
        if clip_id is not None:
            try:
                cid_int = int(clip_id)
                self._stop_panning_thread(cid_int)
                return f"Stopped panning pattern for clip {cid_int}"
            except (ValueError, TypeError):
                return f"Invalid clip_id {clip_id}"
        else:
            # Stop all panning patterns
            for cid in list(self._panning_threads.keys()):
                self._stop_panning_thread(cid)
            return "Stopped all panning patterns"
