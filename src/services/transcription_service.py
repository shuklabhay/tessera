import io
import wave

from faster_whisper import WhisperModel


class TranscriptionService:
    """
    Handles audio transcription using the Whisper model.
    """

    def __init__(
        self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8"
    ) -> None:
        self.whisper_model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribes the given audio bytes to text.

        Args:
            audio_bytes (bytes): The audio data to transcribe.

        Returns:
            str: The transcribed text.
        """
        if not audio_bytes:
            return ""

        audio_buffer = io.BytesIO(audio_bytes)

        segments, _ = self.whisper_model.transcribe(audio_buffer)
        transcription = " ".join([segment.text for segment in segments])
        return transcription.strip()
