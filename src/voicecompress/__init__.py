"""voicecompress: shrink voice recordings with ffmpeg."""

__version__ = "0.1.0"

from .core import (  # noqa: E402
    FORMATS,
    PRESETS,
    CompressionError,
    FFmpegNotFoundError,
    check_ffmpeg,
    compress,
)

__all__ = [
    "FORMATS", "PRESETS", "CompressionError", "FFmpegNotFoundError",
    "check_ffmpeg", "compress", "__version__",
]
