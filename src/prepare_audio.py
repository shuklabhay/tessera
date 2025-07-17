import os
import pathlib
import shutil
import subprocess
from typing import Iterator

from google import genai
from google.genai import types

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg"}
SRC_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = SRC_DIR.parent
AUDIO_DIR = ROOT_DIR / "audio"
PROMPT_PATH = SRC_DIR / "prompts" / "audio_labeling_prompt.md"
TMP_SUFFIX = ".tmp_normalised.wav"
PROMPT_TEXT = (SRC_DIR / "prompts" / "audio_labeling_prompt.md").read_text()

_CLIENT = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
_MODEL_NAME = "gemini-2.5-flash"
_CONTENT_CONFIG = types.GenerateContentConfig(
    response_mime_type="text/plain",
    system_instruction=PROMPT_TEXT,
)


def _find_audio_files() -> Iterator[pathlib.Path]:
    """Yields absolute file paths for supported audio files found within the project's audio directory.

    Returns:
        An iterator of pathlib.Path objects for each found audio file.
    """
    for path in AUDIO_DIR.rglob("*"):
        if path.suffix.lower() in AUDIO_EXTENSIONS and path.is_file():
            yield path


def _ffmpeg_normalise(source: pathlib.Path, target: pathlib.Path) -> None:
    """Resamples the source audio file to 24 kHz and normalises its loudness to -12 LUFS, saving it to the target path.

    Args:
        source: The path to the input audio file.
        target: The path where the normalised output audio file will be saved.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ar",
        "24000",
        "-af",
        "loudnorm=I=-12:LRA=7:TP=-2",
        str(target),
    ]
    subprocess.run(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )


def _replace_file(original: pathlib.Path, tmp: pathlib.Path) -> None:
    """Atomically replaces the original file with the temporary file by moving it.

    Args:
        original: The path to the original file that will be replaced.
        tmp: The path to the temporary file that will replace the original.
    """
    shutil.move(str(tmp), str(original))


def _prepare_audio_file(path: pathlib.Path) -> None:
    """Normalises a given audio file and generates a new text description file for it.

    Args:
        path: The path to the audio file to be prepared.
    """
    tmp_path = path.with_suffix(TMP_SUFFIX)
    _ffmpeg_normalise(path, tmp_path)

    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()

    _replace_file(path, tmp_path)

    desc_path = path.with_suffix(".txt")
    description = _generate_description(audio_bytes)
    desc_path.write_text(description.strip() + "\n")


def _generate_description(audio_bytes: bytes) -> str:
    """Generates a single-paragraph text description for the given audio bytes using the Gemini API.

    Args:
        audio_bytes: The raw bytes of the audio file to be described.

    Returns:
        A string containing the generated description.
    """
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")],
        )
    ]

    response_chunks = _CLIENT.models.generate_content_stream(
        model=_MODEL_NAME,
        contents=contents,
        config=_CONTENT_CONFIG,
    )
    return "".join(chunk.text for chunk in response_chunks)


def main() -> None:
    """Processes all audio files in the audio directory by normalising them and generating descriptions."""
    for audio_path in _find_audio_files():
        _prepare_audio_file(audio_path)
        print(f"✔ Processed {audio_path.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
