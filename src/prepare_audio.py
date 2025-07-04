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
    """Yield absolute file paths for supported audio under AUDIO_DIR."""
    for path in AUDIO_DIR.rglob("*"):
        if path.suffix.lower() in AUDIO_EXTENSIONS and path.is_file():
            yield path


def _ffmpeg_normalise(source: pathlib.Path, target: pathlib.Path) -> None:
    """Resample to 24 kHz and normalise loudness to −12 LUFS."""
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
    """Atomically replace original with tmp."""
    shutil.move(str(tmp), str(original))


def _prepare_audio_file(path: pathlib.Path) -> None:
    """Normalise audio and regenerate description file."""
    tmp_path = path.with_suffix(TMP_SUFFIX)
    _ffmpeg_normalise(path, tmp_path)

    # Read bytes from temp wav before replacing original file
    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()

    _replace_file(path, tmp_path)

    desc_path = path.with_suffix(".txt")
    description = _generate_description(audio_bytes)
    desc_path.write_text(description.strip() + "\n")


def _generate_description(audio_bytes: bytes) -> str:
    """Send audio bytes to Gemini and return a single-paragraph description."""
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
    """Entry point when running from command line."""
    for audio_path in _find_audio_files():
        _prepare_audio_file(audio_path)
        print(f"✔ Processed {audio_path.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
