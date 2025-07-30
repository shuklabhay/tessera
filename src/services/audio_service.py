import io
import threading
import time as time_module
import wave
from typing import Callable, List, Optional

import numpy as np
import pygame
import sounddevice as sd
from faster_whisper import WhisperModel
from piper import PiperVoice, SynthesisConfig


class AudioService:
    def __init__(
        self,
        tts_model_path: str,
        tts_config_path: str,
        whisper_model_size: str = "tiny",
        whisper_device: str = "cpu",
        whisper_compute_type: str = "int8",
        sample_rate: int = 16000,
        threshold: float = 0.01,
        silence_duration: float = 1.5,
    ) -> None:
        self.tts_voice = PiperVoice.load(tts_model_path, tts_config_path)

        self.syn_config = SynthesisConfig(length_scale=1.5, noise_scale=0.333)
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)

        self.whisper_model = WhisperModel(
            whisper_model_size, device=whisper_device, compute_type=whisper_compute_type
        )

        self.sample_rate: int = sample_rate
        self.threshold: float = threshold
        self.silence_duration: float = silence_duration
        self.is_recording: bool = False
        self.audio_buffer: List[float] = []
        self.silence_start_time: Optional[float] = None
        self.recording_complete: bool = False
        self.kai_is_speaking: bool = False

    def text_to_speech(
        self, text: str, callback: Optional[Callable[[], None]] = None
    ) -> None:
        if not text.strip():
            if callback:
                callback()
            return

        print(f"Kai: {text}")

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            self.tts_voice.synthesize_wav(text, wav_file, syn_config=self.syn_config)

        wav_buffer.seek(0)

        with wave.open(wav_buffer, "rb") as wav_file:
            audio_bytes = wav_file.readframes(wav_file.getnframes())

        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        if audio_data.ndim == 1:
            audio_data = np.column_stack((audio_data, audio_data))

        sound = pygame.sndarray.make_sound(audio_data)
        channel = sound.play()

        if callback and channel:

            def monitor_completion():
                while channel.get_busy():
                    pygame.time.wait(10)
                callback()

            threading.Thread(target=monitor_completion, daemon=True).start()

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""

        audio_buffer = io.BytesIO(audio_bytes)

        segments, _ = self.whisper_model.transcribe(audio_buffer)
        transcription = " ".join([segment.text for segment in segments])
        return transcription.strip()

    def record_with_threshold(self) -> bytes:
        if self.kai_is_speaking:
            return b""

        print("Listening for voice...")
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start_time = None
        self.recording_complete = False

        def audio_callback(indata, outdata=None, frames=None, time=None, status=None):
            if status:
                print(f"Audio status: {status}")

            if self.kai_is_speaking:
                self.recording_complete = True
                return

            rms = np.sqrt(np.mean(indata**2))
            if rms > self.threshold:
                if not self.is_recording:
                    print("Voice detected, starting recording...")
                    self.is_recording = True
                    self.audio_buffer = []

                self.audio_buffer.extend(indata.flatten())
                self.silence_start_time = None
            elif self.is_recording:
                self.audio_buffer.extend(indata.flatten())
                if self.silence_start_time is None:
                    self.silence_start_time = time_module.time()
                elif (
                    time_module.time() - self.silence_start_time > self.silence_duration
                ):
                    print("Silence detected, stopping recording...")
                    self.recording_complete = True

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=audio_callback,
            dtype=np.float32,
            blocksize=1024,
        ):
            recording_event = threading.Event()

            def check_completion():
                while not self.recording_complete:
                    recording_event.wait(0.01)
                recording_event.set()

            completion_thread = threading.Thread(target=check_completion, daemon=True)
            completion_thread.start()
            recording_event.wait()

        if self.audio_buffer:
            audio_data = np.array(self.audio_buffer, dtype=np.float32)
            audio_data = (audio_data * 32767).astype(np.int16)
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            return wav_buffer.getvalue()

        return b""

    def set_kai_is_speaking(self, is_speaking: bool) -> None:
        self.kai_is_speaking = is_speaking
