"""Command-line interface for voicecompress."""

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .core import (
    FORMATS,
    PRESETS,
    CompressionError,
    FFmpegNotFoundError,
    check_ffmpeg,
    compress,
)

try:
    from tqdm import tqdm  # optional: pip install tqdm
except ImportError:
    tqdm = None

AUDIO_EXTS = {
    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus",
    ".flac", ".wma", ".amr", ".aiff", ".aif", ".caf", ".mpeg", ".mpg", ".mp4", ".mkv", ".webm",
}


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="voicecompress",
        description="Compress voice recordings (mono, speech-tuned) using ffmpeg.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("input", type=Path, help="Audio file or folder of audio files")
    p.add_argument(
        "-o", "--output", type=Path,
        help="Output file (single input) or output folder (folder input). "
             "Defaults: <name>_compressed.<ext> or <folder>/compressed/",
    )
    p.add_argument("-p", "--preset", choices=PRESETS, default="medium",
                   help="Quality preset (default: medium)")
    p.add_argument("-f", "--format", choices=FORMATS, default="opus",
                   help="Output format (default: opus)")
    p.add_argument("--overwrite", action="store_true",
                   help="Overwrite existing output files")
    return p


def collect_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(f for f in path.iterdir()
                      if f.is_file() and f.suffix.lower() in AUDIO_EXTS)
    sys.exit(f"Error: '{path}' does not exist.")


def main() -> int:
    args = build_parser().parse_args()

    try:
        check_ffmpeg()
    except FFmpegNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    files = collect_inputs(args.input)
    if not files:
        print("No audio files found.", file=sys.stderr)
        return 1

    single = args.input.is_file()
    ext = FORMATS[args.format][0]
    if not single:
        out_dir = args.output or (args.input / "compressed")
        out_dir.mkdir(parents=True, exist_ok=True)

    # Progress: tqdm bar if installed, otherwise a plain "[i/n]" counter.
    if tqdm:
        bar = tqdm(files, unit="file", disable=single)
        log = tqdm.write
    else:
        bar = files
        log = print

    done = failed = total_before = total_after = 0
    start = time.perf_counter()

    for i, f in enumerate(bar, 1):
        if not tqdm and not single:
            print(f"[{i}/{len(files)}] {f.name}")
        dst = args.output if single else out_dir / f"{f.stem}{ext}"

        try:
            out, before, after = compress(
                f, dst, preset=args.preset, fmt=args.format, overwrite=args.overwrite
            )
            done += 1
            total_before += before
            total_after += after
            saved = (1 - after / before) * 100 if before else 0
            log(f"{f.name} -> {out.name}  {human(before)} -> {human(after)}  ({saved:.0f}% smaller)")
        except (FileExistsError, CompressionError, ValueError) as e:
            failed += 1
            log(f"FAILED {f.name}: {e}")

    elapsed = time.perf_counter() - start

    # Summary (only worth showing for batches)
    if not single:
        print("\n--- Summary ---")
        print(f"Compressed: {done}   Failed: {failed}   Time: {elapsed:.1f}s")
        if total_before:
            saved = (1 - total_after / total_before) * 100
            print(f"Total: {human(total_before)} -> {human(total_after)}  "
                  f"(saved {human(total_before - total_after)}, {saved:.0f}%)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
