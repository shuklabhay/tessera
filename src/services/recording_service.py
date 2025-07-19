import io
import threading
import time as time_module
import wave

import numpy as np
import sounddevice as sd


class RecordingService:
    """Handles audio recording with silence detection."""

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.01,
        silence_duration: float = 1.5,
    ):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start_time = None
        self.recording_complete = False
        self.kai_is_speaking = False

    def record_with_threshold(self) -> bytes:
        """Records audio when a voice is detected and stops after a period of silence.

        Returns:
            bytes: The recorded audio data in WAV format.
        """
        if self.kai_is_speaking:
            return b""

        print("Listening for voice...")
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start_time = None
        self.recording_complete = False

        def audio_callback(indata, frames, time, status):
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
        """Sets the speaking state of the assistant to prevent recording during TTS.

        Args:
            is_speaking (bool): Whether the assistant is currently speaking.
        """
        self.kai_is_speaking = is_speaking
