import os

import numpy as np
import pygame

from audio_engine.audio_loader import AudioLoader
from audio_engine.mixer import AudioMixer
from audio_engine.noise_generator import NoiseGenerator


class AudioController:
    def __init__(self):
        pygame.mixer.pre_init(frequency=24000, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        self.loader = AudioLoader()
        self.mixer = AudioMixer()
        self.noise_gen = NoiseGenerator()
        self.active_streams = {}
        self.channel_map = {
            "environmental": 0,
            "noise": 1,
            "speakers": 2,
            "procedural_noise": 3,
            "gemini": 7,
        }

    def play_gemini_chunk(self, audio_chunk_bytes):
        """Play raw audio chunk from Gemini as stereo sound."""
        if not audio_chunk_bytes:
            return

        try:
            # Convert bytes to numpy array
            mono_array = np.frombuffer(audio_chunk_bytes, dtype=np.int16)

            # Convert mono to stereo
            stereo_array = np.column_stack([mono_array, mono_array])

            # Create and queue sound
            sound_chunk = pygame.sndarray.make_sound(stereo_array)
            self.mixer.queue_sound(self.channel_map["gemini"], sound_chunk)
        except Exception as e:
            print(f"Error playing Gemini chunk: {e}")

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
            try:
                with open(desc_path, "r") as f:
                    return f.read().strip()
            except Exception as e:
                return "Error reading description."
        return "No description available."

    def play_environmental_sound(self, volume=0.7):
        """Play a random environmental soundscape on loop."""
        audio, filepath = self.loader.get_cached_audio("environmental")
        if audio is not None:
            # Convert to int16 for pygame
            audio_array = (audio * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(audio_array)

            # Play on environmental channel
            channel = self.channel_map["environmental"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["environmental"] = channel

            # Get description
            description = self._get_audio_description(filepath)
            return f"Playing environmental sound. Description: {description}"
        return "No environmental sounds available"

    def play_speaker_sound(self, volume=0.7):
        """Play a random person speaking audio on loop."""
        audio, filepath = self.loader.get_cached_audio("speakers")
        if audio is not None:
            # Convert to int16 for pygame
            audio_array = (audio * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(audio_array)

            # Play on speakers channel
            channel = self.channel_map["speakers"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["speakers"] = channel

            # Get description
            description = self._get_audio_description(filepath)
            return f"Playing speaker audio. Description: {description}"
        return "No speaker audio available"

    def play_noise_sound(self, volume=0.7):
        """Play a random noise sound on loop."""
        audio, filepath = self.loader.get_cached_audio("noise")
        if audio is not None:
            # Convert to int16 for pygame
            audio_array = (audio * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(audio_array)

            # Play on noise channel
            channel = self.channel_map["noise"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["noise"] = channel

            # Get description
            description = self._get_audio_description(filepath)
            return f"Playing noise audio. Description: {description}"
        return "No noise audio available"

    def generate_white_noise(self, volume=0.5, duration=10):
        """Generate continuous white noise."""
        # Generate noise data
        noise_data = self.noise_gen.white(duration, amplitude=0.5)
        noise_data = (noise_data * 32767).astype(np.int16)

        # Convert to stereo
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)

        # Play on procedural noise channel
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=volume)
        self.active_streams["white_noise"] = channel
        return f"Generating white noise at {int(volume*100)}% volume"

    def generate_pink_noise(self, volume=0.5, duration=10):
        """Generate continuous pink noise."""
        # Generate noise data
        noise_data = self.noise_gen.pink(duration, amplitude=0.5)
        noise_data = (noise_data * 32767).astype(np.int16)

        # Convert to stereo
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)

        # Play on procedural noise channel
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=volume)
        self.active_streams["pink_noise"] = channel
        return f"Generating pink noise at {int(volume*100)}% volume"

    def generate_brown_noise(self, volume=0.5, duration=10):
        """Generate continuous brown noise."""
        # Generate noise data
        noise_data = self.noise_gen.brown(duration, amplitude=0.5)
        noise_data = (noise_data * 32767).astype(np.int16)

        # Convert to stereo
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)

        # Play on procedural noise channel
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=volume)
        self.active_streams["brown_noise"] = channel
        return f"Generating brown noise at {int(volume*100)}% volume"

    def pan_audio(self, audio_type, pan):
        """Pan an audio source left or right."""
        # Clamp pan value
        pan = max(-1.0, min(1.0, pan))

        if audio_type in self.active_streams:
            channel_idx = self.active_streams[audio_type]
            self.mixer.set_pan(channel_idx, pan)
            return f"Panned {audio_type} to {pan}"
        return f"No active {audio_type} stream to pan."

    def adjust_volume(self, audio_type, volume):
        """Adjust the volume of a specific audio type."""
        # Clamp volume value
        volume = max(0.0, min(1.0, volume))

        if audio_type in self.active_streams:
            channel_idx = self.active_streams[audio_type]
            self.mixer.set_volume(channel_idx, volume)
            return f"Adjusted {audio_type} volume to {int(volume*100)}%"
        return f"No active {audio_type} stream to adjust"

    def stop_audio(self, audio_type=None):
        """Stop a specific audio type or all audio if none specified."""
        if audio_type and audio_type in self.active_streams:
            # Stop specific audio type
            channel_idx = self.active_streams[audio_type]
            self.mixer.stop(channel_idx)
            del self.active_streams[audio_type]
            return f"Stopped {audio_type} audio"
        elif not audio_type:
            # Stop all audio
            return self.stop_all_audio()
        return f"No active {audio_type} stream to stop"

    def get_status(self):
        """Get current audio playback status."""
        active = list(self.active_streams.keys())
        if active:
            return f"Currently playing: {', '.join(active)}"
        return "No background audio currently playing"

    def stop_all_audio(self):
        """Stop all active audio streams."""
        stopped_streams = list(self.active_streams.keys())
        self.mixer.stop_all()
        self.active_streams.clear()
        return f"Stopped all audio streams: {', '.join(stopped_streams) if stopped_streams else 'No active streams'}"
