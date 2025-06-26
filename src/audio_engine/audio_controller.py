import os

import numpy as np
import pygame

from audio_engine.audio_loader import AudioLoader
from audio_engine.mixer import AudioMixer
from audio_engine.noise_generator import NoiseGenerator


class AudioController:
    def __init__(self):
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
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
        }

    def _get_audio_description(self, filepath):
        if not filepath:
            return "No description available."

        dir_name, file_name = os.path.split(filepath)
        base_name, _ = os.path.splitext(file_name)
        desc_path = os.path.join(dir_name, f"{base_name}.txt")

        if os.path.exists(desc_path):
            try:
                with open(desc_path, "r") as f:
                    return f.read().strip()
            except Exception as e:
                return "Error reading description."
        return "No description available."

    def play_environmental_sound(self):
        volume = 0.7  # Hardcoded volume
        audio, filepath = self.loader.get_cached_audio("environmental")
        if audio:
            audio_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                audio_array = audio_array.reshape((-1, 2))
            else:
                audio_array = audio_array.reshape((-1, 1))
            sound = pygame.sndarray.make_sound(audio_array)
            channel = self.channel_map["environmental"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["environmental"] = channel
            description = self._get_audio_description(filepath)
            return f"Playing environmental sound. Description: {description}"
        return "No environmental sounds available"

    def play_speaker_sound(self):
        volume = 0.7  # Hardcoded volume
        audio, filepath = self.loader.get_cached_audio("speakers")
        if audio:
            audio_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                audio_array = audio_array.reshape((-1, 2))
            else:
                audio_array = audio_array.reshape((-1, 1))
            sound = pygame.sndarray.make_sound(audio_array)
            channel = self.channel_map["speakers"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["speakers"] = channel
            description = self._get_audio_description(filepath)
            return f"Playing speaker audio. Description: {description}"
        return "No speaker audio available"

    def play_noise_sound(self):
        volume = 0.7  # Hardcoded volume
        audio, filepath = self.loader.get_cached_audio("noise")
        if audio:
            audio_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                audio_array = audio_array.reshape((-1, 2))
            else:
                audio_array = audio_array.reshape((-1, 1))
            sound = pygame.sndarray.make_sound(audio_array)
            channel = self.channel_map["noise"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["noise"] = channel
            description = self._get_audio_description(filepath)
            return f"Playing noise audio. Description: {description}"
        return "No noise audio available"

    def generate_white_noise(self, duration=10):
        volume = 0.7  # Hardcoded volume
        noise_data = self.noise_gen.white(duration, amplitude=volume)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=1.0)
        self.active_streams["white_noise"] = channel
        return f"Generating white noise at {int(volume*100)}% volume"

    def generate_pink_noise(self, duration=10):
        volume = 0.7  # Hardcoded volume
        noise_data = self.noise_gen.pink(duration, amplitude=volume)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=1.0)
        self.active_streams["pink_noise"] = channel
        return f"Generating pink noise at {int(volume*100)}% volume"

    def generate_noise(self, noise_type, duration=10, volume=0.5):
        """Generate different types of noise based on the noise_type parameter."""
        if noise_type == "brown":
            return self.generate_brown_noise(duration, volume)
        elif noise_type == "white":
            return self.generate_white_noise(duration)
        elif noise_type == "pink":
            return self.generate_pink_noise(duration)
        else:
            return f"Unknown noise type: {noise_type}"

    def generate_brown_noise(self, duration=10, volume=0.5):
        noise_data = self.noise_gen.brown(duration, amplitude=volume)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=1.0)
        self.active_streams["brown_noise"] = channel
        return f"Generating brown noise at {int(volume*100)}% volume"

    def pan_audio(self, audio_type, pan):
        pan = max(-1.0, min(1.0, pan))  # Clamp pan value between -1.0 and 1.0
        if audio_type in self.active_streams:
            channel_idx = self.active_streams[audio_type]
            self.mixer.set_pan(channel_idx, pan)
            return f"Panned {audio_type} to {pan}"
        return f"No active {audio_type} stream to pan."

    def adjust_volume(self, audio_type, volume):
        volume = max(0.0, min(1.0, volume))
        if audio_type in self.active_streams:
            channel = self.active_streams[audio_type]
            self.mixer.set_volume(channel, volume)
            return f"Adjusted {audio_type} volume to {int(volume*100)}%"
        return f"No active {audio_type} stream to adjust"

    def stop_audio(self, audio_type=None):
        if audio_type and audio_type in self.active_streams:
            channel = self.active_streams[audio_type]
            self.mixer.stop(channel)
            del self.active_streams[audio_type]
            return f"Stopped {audio_type} audio"
        elif not audio_type:
            self.mixer.stop_all()
            self.active_streams.clear()
            return "Stopped all background audio"
        return f"No active {audio_type} stream to stop"

    def get_status(self):
        active = list(self.active_streams.keys())
        if active:
            return f"Currently playing: {', '.join(active)}"
        return "No background audio currently playing"

    def stop_all_audio(self):
        stopped_streams = []
        for stream_name, channel in self.active_streams.items():
            self.mixer.stop(channel)
            stopped_streams.append(stream_name)
        self.active_streams.clear()
        return f"Stopped all audio streams: {', '.join(stopped_streams) if stopped_streams else 'No active streams'}"
