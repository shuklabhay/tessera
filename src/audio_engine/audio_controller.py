import numpy as np
import pygame

from .audio_loader import AudioLoader
from .mixer import AudioMixer
from .noise_generator import NoiseGenerator


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

    def play_environmental_sound(self, volume=0.7):
        print("--- TOOL CALL: play_environmental_sound ---")
        audio = self.loader.get_cached_audio("environmental")
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
            return f"Playing environmental sound at {int(volume*100)}% volume"
        return "No environmental sounds available"

    def play_speaker_sound(self, volume=0.7):
        print("--- TOOL CALL: play_speaker_sound ---")
        audio = self.loader.get_cached_audio("speakers")
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
            return f"Playing speaker audio at {int(volume*100)}% volume"
        return "No speaker audio available"

    def play_noise_sound(self, volume=0.5):
        print("--- TOOL CALL: play_noise_sound ---")
        audio = self.loader.get_cached_audio("noise")
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
            return f"Playing noise audio at {int(volume*100)}% volume"
        return "No noise audio available"

    def generate_white_noise(self, volume=0.3, duration=10):
        print("--- TOOL CALL: generate_white_noise ---")
        noise_data = self.noise_gen.white(duration, amplitude=volume)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=1.0)
        self.active_streams["white_noise"] = channel
        return f"Generating white noise at {int(volume*100)}% volume"

    def generate_pink_noise(self, volume=0.3, duration=10):
        print("--- TOOL CALL: generate_pink_noise ---")
        noise_data = self.noise_gen.pink(duration, amplitude=volume)
        noise_data = (noise_data * 32767).astype(np.int16)
        noise_stereo = np.column_stack((noise_data, noise_data))
        sound = pygame.sndarray.make_sound(noise_stereo)
        channel = self.channel_map["procedural_noise"]
        self.mixer.play(sound, channel, loops=-1, volume=1.0)
        self.active_streams["pink_noise"] = channel
        return f"Generating pink noise at {int(volume*100)}% volume"

    def adjust_volume(self, audio_type, volume):
        print(
            f"--- TOOL CALL: adjust_volume (type: {audio_type}, volume: {volume}) ---"
        )
        volume = max(0.0, min(1.0, volume))
        if audio_type in self.active_streams:
            channel = self.active_streams[audio_type]
            self.mixer.set_volume(channel, volume)
            return f"Adjusted {audio_type} volume to {int(volume*100)}%"
        return f"No active {audio_type} stream to adjust"

    def stop_audio(self, audio_type=None):
        print(f"--- TOOL CALL: stop_audio (type: {audio_type}) ---")
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
        print("--- TOOL CALL: get_status ---")
        active = list(self.active_streams.keys())
        if active:
            return f"Currently playing: {', '.join(active)}"
        return "No background audio currently playing"

    def stop_all_audio(self):
        print("--- TOOL CALL: stop_all_audio ---")
        stopped_streams = []
        for stream_name, channel in self.active_streams.items():
            self.mixer.stop(channel)
            stopped_streams.append(stream_name)
        self.active_streams.clear()
        return f"Stopped all audio streams: {', '.join(stopped_streams) if stopped_streams else 'No active streams'}"
