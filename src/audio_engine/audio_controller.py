import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pygame

from audio_engine.audio_loader import AudioLoader
from audio_engine.mixer import AudioMixer

# Volume limits for different channel types
GEMINI_VOLUME = 1.2
BACKGROUND_VOLUME_MAX = 0.2
NORMAL_VOLUME_MAX = 0.5


class AudioController:
    def __init__(self) -> None:
        if pygame.mixer.get_init():
            pygame.mixer.quit()

        pygame.mixer.pre_init(
            frequency=24000, size=-16, channels=2, buffer=512, allowedchanges=0
        )
        pygame.mixer.init()

        self.loader = AudioLoader()
        self.mixer = AudioMixer()
        self.clips = {}
        self._next_clip_id = 1
        self.channel_map = {"gemini": 0}
        self._ducked = False
        self._panning_threads = {}
        self._fade_threads = {}

    def play_gemini_chunk(self, audio_chunk_bytes: bytes) -> None:
        """Play raw audio chunk from Gemini."""
        if not audio_chunk_bytes:
            return

        # Convert bytes to numpy array
        mono_array = np.frombuffer(audio_chunk_bytes, dtype=np.int16)

        # Convert mono to stereo
        stereo_array = np.ascontiguousarray(np.column_stack([mono_array, mono_array]))

        # Create and queue sound
        sound_chunk = pygame.sndarray.make_sound(stereo_array)
        self.mixer.set_volume(self.channel_map["gemini"], GEMINI_VOLUME)
        self.mixer.queue_sound(self.channel_map["gemini"], sound_chunk)

        # Duck background audio
        self._auto_duck_background(True)

    def _get_audio_description(self, filepath: str) -> str:
        """Get description from companion text file."""
        if not filepath:
            return "No description available."

        # Look for description file
        dir_name, file_name = os.path.split(filepath)
        base_name, _ = os.path.splitext(file_name)
        desc_path = os.path.join(dir_name, f"{base_name}.txt")

        # Read description
        if os.path.exists(desc_path):
            with open(desc_path, "r") as f:
                return f.read().strip()
        return "No description available."

    def _fade_volume(
        self,
        clip_id: int,
        start_volume: float,
        end_volume: float,
        duration: float = 0.5,
    ) -> None:
        """Smoothly fade volume over a duration."""
        if clip_id not in self.clips:
            return

        # Calculate fade parameters
        clip = self.clips[clip_id]
        steps = 20
        sleep_time = duration / steps
        step_size = (end_volume - start_volume) / steps

        # Apply fade
        for step in range(steps + 1):
            if clip_id in self._fade_threads and self._fade_threads[clip_id].get(
                "stop", False
            ):
                break

            current_volume = start_volume + (step_size * step)
            current_volume = max(0.0, min(1.0, current_volume))

            self.mixer.set_volume(clip["channel"], current_volume)
            clip["volume"] = current_volume

            if step < steps:
                time.sleep(sleep_time)

    def _start_fade_in(self, clip_id: int, target_volume: float) -> None:
        """Start a fade-in effect."""
        if clip_id in self._fade_threads:
            self._fade_threads[clip_id]["stop"] = True

        # Create and start fade thread
        thread_info = {"stop": False}
        thread = threading.Thread(
            target=self._fade_volume,
            args=(clip_id, 0.0, target_volume, 0.5),
            daemon=True,
        )
        thread_info["thread"] = thread
        self._fade_threads[clip_id] = thread_info
        thread.start()

    def _start_fade_out(self, clip_id: int, callback=None) -> None:
        """Start a fade-out effect."""
        if clip_id not in self.clips:
            return

        if clip_id in self._fade_threads:
            self._fade_threads[clip_id]["stop"] = True

        # Get current volume
        current_volume = self.clips[clip_id]["volume"]
        thread_info = {"stop": False}

        # Define fade and callback
        def fade_and_callback():
            self._fade_volume(clip_id, current_volume, 0.0, 0.5)
            if callback:
                callback()

        # Create and start fade thread
        thread = threading.Thread(target=fade_and_callback, daemon=True)
        thread_info["thread"] = thread
        self._fade_threads[clip_id] = thread_info
        thread.start()

    def _auto_duck_background(self, enable: bool) -> None:
        """Automatically duck background audio."""
        target_volume = BACKGROUND_VOLUME_MAX if enable else NORMAL_VOLUME_MAX

        # Duck all non-Gemini channels
        for clip_id, clip in self.clips.items():
            if clip["channel"] != self.channel_map["gemini"]:
                self._fade_volume(clip_id, clip["volume"], target_volume, 0.3)



    def play_environmental_sound(
        self, volume: float = 0.7
    ) -> Union[str, Dict[str, Any]]:
        """Play a random environmental sound."""
        # Set volume and get audio
        target_volume = max(0.0, min(NORMAL_VOLUME_MAX, volume))
        audio, filepath = self.loader.get_cached_audio("environmental")
        if audio is not None:
            # Convert for pygame
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            # Allocate channel
            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            # Start playing at zero volume
            self.mixer.play(sound, channel, loops=-1, volume=0.0)

            # Create clip metadata
            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "environmental",
                "channel": channel,
                "volume": 0.0,
                "pan": 0.0,
                "description": description,
            }

            # Start fade-in effect
            self._start_fade_in(clip_id, target_volume)

            return {
                "clip_id": clip_id,
                "description": description,
                "type": "environmental",
            }
        return "No environmental sounds available"

    def play_speaker_sound(self, volume: float = 0.7) -> Union[str, Dict[str, Any]]:
        """Play a random speaker sound."""
        # Set volume and get audio
        target_volume = max(0.0, min(NORMAL_VOLUME_MAX, volume))
        audio, filepath = self.loader.get_cached_audio("speakers")
        if audio is not None:
            # Convert for pygame
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            # Allocate channel
            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            # Start playing at zero volume
            self.mixer.play(sound, channel, loops=-1, volume=0.0)

            # Create clip metadata
            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "speakers",
                "channel": channel,
                "volume": 0.0,
                "pan": 0.0,
                "description": description,
            }

            # Start fade-in effect
            self._start_fade_in(clip_id, target_volume)

            return {"clip_id": clip_id, "description": description, "type": "speakers"}
        return "No speaker audio available"

    def play_noise_sound(self, volume: float = 0.7) -> Union[str, Dict[str, Any]]:
        """Play a random noise sound."""
        # Set volume and get audio
        target_volume = max(0.0, min(NORMAL_VOLUME_MAX, volume))
        audio, filepath = self.loader.get_cached_audio("noise")
        if audio is not None:
            # Convert for pygame
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            # Allocate channel
            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            # Start playing at zero volume
            self.mixer.play(sound, channel, loops=-1, volume=0.0)

            # Create clip metadata
            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "noise",
                "channel": channel,
                "volume": 0.0,
                "pan": 0.0,
                "description": description,
            }

            # Start fade-in effect
            self._start_fade_in(clip_id, target_volume)

            return {"clip_id": clip_id, "description": description, "type": "noise"}
        return "No noise audio available"

    def play_alert_sound(self, volume: float = 0.7) -> Union[str, Dict[str, Any]]:
        """Play a random alert sound."""
        # Set volume and get audio
        target_volume = max(0.0, min(NORMAL_VOLUME_MAX, volume))
        audio, filepath = self.loader.get_cached_audio("alerts")
        if audio is not None:
            # Convert for pygame
            audio_array = np.ascontiguousarray((audio * 32767).astype(np.int16))
            sound = pygame.sndarray.make_sound(audio_array)

            # Allocate channel
            channel = self._get_free_non_reserved_channel()
            if channel is None:
                return "No free audio channels available"

            # Start playing at zero volume
            self.mixer.play(sound, channel, loops=0, volume=0.0)

            # Create clip metadata
            description = self._get_audio_description(filepath)
            clip_id = self._next_clip_id
            self._next_clip_id += 1
            self.clips[clip_id] = {
                "type": "alerts",
                "channel": channel,
                "volume": 0.0,
                "pan": 0.0,
                "description": description,
            }

            # Start fade-in effect
            self._start_fade_in(clip_id, target_volume)

            return {"clip_id": clip_id, "description": description, "type": "alerts"}
        return "No alert sounds available"

    def pan_audio(
        self,
        audio_type: Optional[str],
        pan: float,
        clip_id: Optional[Union[str, int]] = None,
    ) -> str:
        """Pan an audio source left or right."""
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

    def adjust_volume(
        self,
        audio_type: Optional[str],
        volume: float,
        clip_id: Optional[Union[str, int]] = None,
    ) -> str:
        """Adjust volume for a specific clip."""
        volume = max(0.0, min(NORMAL_VOLUME_MAX, volume))

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

    def stop_audio(self, audio_type: Optional[str] = None) -> str:
        """Stop a specific audio type."""
        if audio_type and not audio_type == "clip":
            to_remove = [
                cid for cid, m in self.clips.items() if m["type"] == audio_type
            ]
            for cid in to_remove:
                # Fade out and stop
                def stop_callback(clip_id=cid):
                    if clip_id in self.clips:
                        self.mixer.stop(self.clips[clip_id]["channel"])
                        del self.clips[clip_id]

                self._start_fade_out(cid, stop_callback)
            return f"Stopping {len(to_remove)} {audio_type} clips with fade-out"
        elif audio_type == "clip":
            return "Use stop_audio with clip_id parameter."
        elif not audio_type:
            return self.stop_all_audio()
        return f"No active {audio_type} stream to stop"

    def get_status(self) -> List[Dict[str, Any]]:
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

    def stop_all_audio(self) -> str:
        """Stop all active audio streams."""
        # Stop all panning patterns
        for cid in list(self._panning_threads.keys()):
            self._stop_panning_thread(cid)

        # Fade out all non-Gemini clips
        clips_to_fade = []
        for cid, clip in self.clips.items():
            if clip["channel"] != self.channel_map.get("gemini"):
                clips_to_fade.append(cid)

        if clips_to_fade:
            for cid in clips_to_fade:

                def stop_callback(clip_id=cid):
                    if clip_id in self.clips:
                        self.mixer.stop(self.clips[clip_id]["channel"])
                        del self.clips[clip_id]

                self._start_fade_out(cid, stop_callback)
            return f"Stopping {len(clips_to_fade)} audio streams with fade-out"
        else:
            return "No audio streams to stop"

    def duck_background(self, enable: bool, factor: float = 0.3) -> None:
        """Duck or restore background volumes."""
        if (enable and self._ducked) or (not enable and not self._ducked):
            return

        # Exclude Gemini channel
        exclude = (
            [self.channel_map.get("gemini")] if "gemini" in self.channel_map else []
        )

        # Perform ducking
        updated = self.mixer.duck_channels(enable, factor, exclude=exclude)

        # Sync metadata
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

    def _get_free_non_reserved_channel(self) -> Optional[int]:
        """Return a free, non-reserved mixer channel."""
        reserved = set(self.channel_map.values())
        for idx in range(len(self.mixer.channels)):
            if idx in reserved:
                continue
            if not self.mixer.channels[idx].get_busy():
                return idx
        return None

    def _stop_panning_thread(self, clip_id: int) -> None:
        """Stop an active panning animation."""
        if clip_id in self._panning_threads:
            self._panning_threads[clip_id]["stop"] = True
            self._panning_threads[clip_id]["thread"].join(timeout=1.0)
            del self._panning_threads[clip_id]

    def _smooth_pan_transition(
        self,
        clip_id: int,
        start_pan: float,
        end_pan: float,
        duration_seconds: float,
        steps: int = 20,
    ) -> None:
        """Smoothly transition pan position."""
        clip = self.clips.get(clip_id)
        if not clip:
            return

        # Calculate transition parameters
        sleep_time = duration_seconds / steps
        step_size = (end_pan - start_pan) / steps

        thread_info = self._panning_threads.get(clip_id, {})

        # Apply transition
        for step in range(steps + 1):
            if thread_info.get("stop", False):
                break

            current_pan = start_pan + (step_size * step)
            current_pan = max(-1.0, min(1.0, current_pan))

            self.mixer.set_pan(clip["channel"], current_pan)
            clip["pan"] = current_pan

            if step < steps:
                time.sleep(sleep_time)

    def pan_pattern_sweep(
        self,
        clip_id: Union[str, int],
        direction: str = "left_to_right",
        speed: Union[str, float] = "moderate",
    ) -> str:
        """Sweep audio across the stereo field."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop existing panning
        self._stop_panning_thread(cid_int)

        # Set duration
        speed_durations = {"slow": 10.0, "moderate": 5.0, "fast": 2.0}
        if isinstance(speed, str) and speed in speed_durations:
            duration = speed_durations[speed]
        elif isinstance(speed, (int, float)):
            duration = float(speed)
        else:
            duration = 5.0

        # Get current pan
        current_pan = self.clips[cid_int]["pan"]

        # Set start and end positions
        if direction == "left_to_right":
            start_pan, end_pan = current_pan, 1.0
        elif direction == "right_to_left":
            start_pan, end_pan = current_pan, -1.0
        elif direction == "center_out":
            start_pan, end_pan = current_pan, 1.0 if current_pan >= 0 else -1.0
        else:
            start_pan, end_pan = current_pan, 1.0

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

    def pan_pattern_pendulum(
        self, clip_id: Union[str, int], cycles: int = 3, duration_per_cycle: float = 3.0
    ) -> str:
        """Create a pendulum panning motion."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop existing panning
        self._stop_panning_thread(cid_int)

        def pendulum_motion() -> None:
            clip = self.clips.get(cid_int)
            if not clip:
                return

            # Set parameters
            thread_info = self._panning_threads.get(cid_int, {})
            steps_per_cycle = 40
            sleep_time = duration_per_cycle / steps_per_cycle
            current_pan = clip["pan"]

            for cycle in range(cycles):
                if thread_info.get("stop", False):
                    break

                # Determine swing direction
                if current_pan <= 0:
                    # Swing right
                    for step in range(steps_per_cycle // 2):
                        if thread_info.get("stop", False):
                            break
                        pan = current_pan + (
                            (1.0 - current_pan) * step / (steps_per_cycle // 2)
                        )
                        pan = max(-1.0, min(1.0, pan))
                        self.mixer.set_pan(clip["channel"], pan)
                        clip["pan"] = pan
                        time.sleep(sleep_time)

                    # Swing left
                    for step in range(steps_per_cycle // 2):
                        if thread_info.get("stop", False):
                            break
                        pan = 1.0 - (2.0 * step / (steps_per_cycle // 2))
                        pan = max(-1.0, min(1.0, pan))
                        self.mixer.set_pan(clip["channel"], pan)
                        clip["pan"] = pan
                        time.sleep(sleep_time)
                else:
                    # Swing left
                    for step in range(steps_per_cycle // 2):
                        if thread_info.get("stop", False):
                            break
                        pan = current_pan - (
                            (current_pan + 1.0) * step / (steps_per_cycle // 2)
                        )
                        pan = max(-1.0, min(1.0, pan))
                        self.mixer.set_pan(clip["channel"], pan)
                        clip["pan"] = pan
                        time.sleep(sleep_time)

                    # Swing right
                    for step in range(steps_per_cycle // 2):
                        if thread_info.get("stop", False):
                            break
                        pan = -1.0 + (2.0 * step / (steps_per_cycle // 2))
                        pan = max(-1.0, min(1.0, pan))
                        self.mixer.set_pan(clip["channel"], pan)
                        clip["pan"] = pan
                        time.sleep(sleep_time)

                # Update pan for next cycle
                current_pan = clip["pan"]

        # Create and start thread
        thread_info = {"stop": False}
        thread = threading.Thread(target=pendulum_motion, daemon=True)
        thread_info["thread"] = thread
        self._panning_threads[cid_int] = thread_info
        thread.start()

        return f"Started pendulum motion for clip {cid_int} - {cycles} cycles"

    def pan_pattern_alternating(
        self, clip_id: Union[str, int], interval: float = 2.0, cycles: int = 5
    ) -> str:
        """Alternate audio between left and right."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop existing panning
        self._stop_panning_thread(cid_int)

        def alternating_motion() -> None:
            clip = self.clips.get(cid_int)
            if not clip:
                return

            # Set parameters
            thread_info = self._panning_threads.get(cid_int, {})
            current_pan = clip["pan"]

            # Choose start position
            if current_pan <= 0:
                positions = [0.8, -0.8]
            else:
                positions = [-0.8, 0.8]

            for cycle in range(cycles):
                if thread_info.get("stop", False):
                    break

                target_pan = positions[cycle % 2]

                # Smoothly transition to target
                steps = 10
                step_time = interval / steps
                start_pan = clip["pan"]

                for step in range(steps):
                    if thread_info.get("stop", False):
                        break
                    pan = start_pan + ((target_pan - start_pan) * step / steps)
                    self.mixer.set_pan(clip["channel"], pan)
                    clip["pan"] = pan
                    time.sleep(step_time)

                # Set final position
                self.mixer.set_pan(clip["channel"], target_pan)
                clip["pan"] = target_pan

        # Create and start thread
        thread_info = {"stop": False}
        thread = threading.Thread(target=alternating_motion, daemon=True)
        thread_info["thread"] = thread
        self._panning_threads[cid_int] = thread_info
        thread.start()

        return f"Started alternating pattern for clip {cid_int}"

    def pan_to_side(self, clip_id: Union[str, int], side: str) -> str:
        """Smoothly pan audio to a side."""
        try:
            cid_int = int(clip_id)
        except (ValueError, TypeError):
            return f"Invalid clip_id {clip_id}."

        if cid_int not in self.clips:
            return f"Unknown clip_id {clip_id}."

        # Stop existing panning
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

        # Set pan values
        target_pan = side_map.get(side.lower(), 0.0)
        current_pan = self.clips[cid_int]["pan"]

        # Create and start thread
        thread_info = {"stop": False}
        thread = threading.Thread(
            target=self._smooth_pan_transition,
            args=(cid_int, current_pan, target_pan, 0.5),
            daemon=True,
        )
        thread_info["thread"] = thread
        self._panning_threads[cid_int] = thread_info
        thread.start()

        return f"Panning clip {cid_int} to {side}"

    def stop_panning_patterns(self, clip_id: Optional[Union[str, int]] = None) -> str:
        """Stop panning patterns for a clip or all clips."""
        if clip_id is not None:
            try:
                cid_int = int(clip_id)
                self._stop_panning_thread(cid_int)
                return f"Stopped panning pattern for clip {cid_int}"
            except (ValueError, TypeError):
                return f"Invalid clip_id {clip_id}"
        else:
            # Stop all panning
            for cid in list(self._panning_threads.keys()):
                self._stop_panning_thread(cid)
            return "Stopped all panning patterns"
