import os

import numpy as np
import pygame

from audio_engine.audio_loader import AudioLoader
from audio_engine.mixer import AudioMixer
from audio_engine.noise_generator import NoiseGenerator


class AudioController:
    def __init__(self):
        # CHANGE 1: Set frequency to 24000 Hz to match Gemini's output
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
        """
        Receives a raw audio chunk from Gemini, converts it to a stereo
        """
        if not audio_chunk_bytes:
            return

        try:
            # Convert the mono 16-bit PCM bytes to a NumPy array
            mono_array = np.frombuffer(audio_chunk_bytes, dtype=np.int16)

            # Pygame mixer is stereo, so duplicate the mono channel to create a stereo array
            stereo_array = np.column_stack([mono_array, mono_array])

            # Create a Pygame Sound object from the NumPy array
            sound_chunk = pygame.sndarray.make_sound(stereo_array)

            # Queue the sound on the dedicated Gemini channel
            self.mixer.queue_sound(self.channel_map["gemini"], sound_chunk)
        except Exception as e:
            print(f"Error playing Gemini chunk: {e}")

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

    def play_environmental_sound(self, volume=0.7):
        audio, filepath = self.loader.get_cached_audio("environmental")
        if audio:
            audio_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                audio_array = audio_array.reshape((-1, 2))
            else:
                audio_array = np.repeat(audio_array.reshape((-1, 1)), 2, axis=1)
            sound = pygame.sndarray.make_sound(audio_array)
            channel = self.channel_map["environmental"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["environmental"] = channel
            description = self._get_audio_description(filepath)
            return f"Playing environmental sound. Description: {description}"
        return "No environmental sounds available"

    def play_speaker_sound(self, volume=0.7):
        audio, filepath = self.loader.get_cached_audio("speakers")
        if audio:
            audio_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                audio_array = audio_array.reshape((-1, 2))
            else:
                audio_array = np.repeat(audio_array.reshape((-1, 1)), 2, axis=1)
            sound = pygame.sndarray.make_sound(audio_array)
            channel = self.channel_map["speakers"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["speakers"] = channel
            description = self._get_audio_description(filepath)
            return f"Playing speaker audio. Description: {description}"
        return "No speaker audio available"

    def play_noise_sound(self, volume=0.7):
        audio, filepath = self.loader.get_cached_audio("noise")
        if audio:
            audio_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                audio_array = audio_array.reshape((-1, 2))
            else:
                audio_array = np.repeat(audio_array.reshape((-1, 1)), 2, axis=1)
            sound = pygame.sndarray.make_sound(audio_array)
            channel = self.channel_map["noise"]
            self.mixer.play(sound, channel, loops=-1, volume=volume)
            self.active_streams["noise"] = channel
            description = self._get_audio_description(filepath)
            return f"Playing noise audio. Description: {description}"
        return "No noise audio available"

    def generate_white_noise(self, volume=0.5, duration=10):
        noise_data = self.noise_gen.white(duration, amplitude=0.5)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=volume)
        self.active_streams["white_noise"] = channel
        return f"Generating white noise at {int(volume*100)}% volume"

    def generate_pink_noise(self, volume=0.5, duration=10):
        noise_data = self.noise_gen.pink(duration, amplitude=0.5)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=volume)
        self.active_streams["pink_noise"] = channel
        return f"Generating pink noise at {int(volume*100)}% volume"

    def generate_brown_noise(self, volume=0.5, duration=10):
        noise_data = self.noise_gen.brown(duration, amplitude=0.5)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=volume)
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
            channel_idx = self.active_streams[audio_type]
            self.mixer.set_volume(channel_idx, volume)
            return f"Adjusted {audio_type} volume to {int(volume*100)}%"
        return f"No active {audio_type} stream to adjust"

    def stop_audio(self, audio_type=None):
        if audio_type and audio_type in self.active_streams:
            channel_idx = self.active_streams[audio_type]
            self.mixer.stop(channel_idx)
            del self.active_streams[audio_type]
            return f"Stopped {audio_type} audio"
        elif not audio_type:
            # This case is less likely with the strict tool definition but good to have
            return self.stop_all_audio()
        return f"No active {audio_type} stream to stop"

    def get_status(self):
        active = list(self.active_streams.keys())
        if active:
            return f"Currently playing: {', '.join(active)}"
        return "No background audio currently playing"

    def stop_all_audio(self):
        stopped_streams = list(self.active_streams.keys())
        self.mixer.stop_all()
        self.active_streams.clear()
        return f"Stopped all audio streams: {', '.join(stopped_streams) if stopped_streams else 'No active streams'}"
