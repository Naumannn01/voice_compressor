"""Core voice-compression logic: ffmpeg wrapper with speech-tuned presets."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
    pass


class CompressionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Preset:
    bitrate: str      # e.g. "24k"
    sample_rate: int  # Hz; Opus supports 8000/12000/16000/24000/48000


PRESETS = {
    "low": Preset("16k", 16000),     # smallest, still intelligible speech
    "medium": Preset("24k", 16000),  # good default for voice notes/meetings
    "high": Preset("32k", 24000),    # clearer, still far smaller than the source
}

# fmt -> (file extension, ffmpeg codec)
FORMATS = {
    "opus": (".opus", "libopus"),
    "mp3": (".mp3", "libmp3lame"),
}


def check_ffmpeg() -> str:
    """Return the ffmpeg path, or raise with install hints."""
    path = shutil.which("ffmpeg")
    if path is None:
        raise FFmpegNotFoundError(
            "ffmpeg not found on PATH. Install it:\n"
            "  Windows: winget install Gyan.FFmpeg\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   sudo apt install ffmpeg"
        )
    return path


def compress(
    src: Path,
    dst: Path | None = None,
    preset: str = "medium",
    fmt: str = "opus",
    overwrite: bool = False,
) -> tuple[Path, int, int]:
    """Compress one audio file. The original is never modified.

    Returns (output_path, original_size_bytes, compressed_size_bytes).
    """
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(f"Input file not found: {src}")
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Choose from {list(PRESETS)}")
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format '{fmt}'. Choose from {list(FORMATS)}")

    ffmpeg = check_ffmpeg()
    p = PRESETS[preset]
    ext, codec = FORMATS[fmt]

    if dst is None:
        dst = src.with_name(f"{src.stem}_compressed{ext}")
    dst = Path(dst)
    if dst.resolve() == src.resolve():
        raise ValueError("Output path must differ from the input path.")
    if dst.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {dst} (use overwrite=True)")

    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-y" if overwrite else "-n",
        "-i", str(src),
        "-vn",                      # drop any video/cover art stream
        "-ac", "1",                 # mono
        "-ar", str(p.sample_rate),
        "-c:a", codec,
        "-b:a", p.bitrate,
    ]
    if fmt == "opus":
        cmd += ["-application", "voip"]  # tuned for speech
    cmd.append(str(dst))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        dst.unlink(missing_ok=True)  # don't leave a partial file behind
        raise CompressionError(f"ffmpeg failed on {src.name}: {result.stderr.strip()}")

    return dst, src.stat().st_size, dst.stat().st_size
