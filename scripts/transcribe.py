"""
Transcribe a slice of a video using faster-whisper.

Usage:
    python transcribe.py --video <path> --start MM:SS --end MM:SS --output <json_path>
    python transcribe.py --video <path> --output <json_path>       # full video

Output JSON shape:
    {
      "video": "...",
      "language": "en",
      "window": {"start": 2520.0, "end": 3510.0},
      "segments": [
        {"start": 2521.4, "end": 2525.1, "text": "Buy now for just $57..."},
        ...
      ]
    }

Timestamps are restored to the ORIGINAL video timeline (we add the slice offset
back), so the caller can cite "47:23" and it matches the source file.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_timestamp(ts: str) -> float:
    """Convert 'MM:SS' or 'HH:MM:SS' or plain seconds to float seconds."""
    if ts is None:
        return None
    parts = ts.strip().split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Cannot parse timestamp: {ts}")


def cut_audio(video_path: Path, start: float, end: float, out_wav: Path) -> None:
    """Use ffmpeg to extract a mono 16kHz wav of the desired window."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
    ]
    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None:
        duration = end - (start or 0)
        cmd += ["-t", str(duration)]
    cmd += [
        "-vn", "-ac", "1", "-ar", "16000",
        "-acodec", "pcm_s16le",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--start", default=None, help="MM:SS or HH:MM:SS")
    p.add_argument("--end", default=None, help="MM:SS or HH:MM:SS")
    p.add_argument("--output", required=True)
    p.add_argument("--model", default="medium")
    p.add_argument("--language", default="en")
    args = p.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH. Run install.ps1 first.", file=sys.stderr)
        return 2

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("ERROR: faster-whisper not installed. Run install.ps1 first.", file=sys.stderr)
        return 2

    video = Path(args.video)
    if not video.exists():
        print(f"ERROR: video not found: {video}", file=sys.stderr)
        return 1

    start_sec = parse_timestamp(args.start) if args.start else None
    end_sec = parse_timestamp(args.end) if args.end else None
    offset = start_sec or 0.0

    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "slice.wav"
        print(f"[sentinela] cutting audio slice -> {wav}", file=sys.stderr)
        cut_audio(video, start_sec, end_sec, wav)

        print(f"[sentinela] loading model '{args.model}' (CPU/int8)...", file=sys.stderr)
        model = WhisperModel(args.model, device="cpu", compute_type="int8")

        print("[sentinela] transcribing...", file=sys.stderr)
        segments_iter, info = model.transcribe(
            str(wav),
            language=args.language,
            vad_filter=True,
            word_timestamps=False,
        )

        segments = []
        for seg in segments_iter:
            segments.append({
                "start": round(seg.start + offset, 2),
                "end": round(seg.end + offset, 2),
                "text": seg.text.strip(),
            })

    result = {
        "video": str(video),
        "language": args.language,
        "window": {"start": start_sec, "end": end_sec},
        "segments": segments,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[sentinela] wrote {len(segments)} segments to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
