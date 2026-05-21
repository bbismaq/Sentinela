"""
Transcribe multiple videos with a single model load.

Usage:
    python transcribe_batch.py --dir <folder> --output-dir <json_dir> [--model medium] [--language en]

Walks <folder> for .mp4 files, transcribes each, and writes a JSON per video
named <stem>.json in <output-dir>.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def cut_audio(video_path: Path, out_wav: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000",
        "-acodec", "pcm_s16le",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--model", default="medium")
    p.add_argument("--language", default="en")
    args = p.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH.", file=sys.stderr)
        return 2

    from faster_whisper import WhisperModel

    in_dir = Path(args.dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(in_dir.glob("*.mp4"))
    if not videos:
        print(f"No .mp4 found in {in_dir}", file=sys.stderr)
        return 1

    print(f"[batch] loading model '{args.model}' (CPU/int8)...", file=sys.stderr)
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    for i, video in enumerate(videos, 1):
        out_path = out_dir / (video.stem + ".json")
        if out_path.exists():
            print(f"[batch] ({i}/{len(videos)}) SKIP {video.name} (already done)", file=sys.stderr)
            continue

        print(f"[batch] ({i}/{len(videos)}) {video.name}", file=sys.stderr)
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "slice.wav"
            cut_audio(video, wav)
            segments_iter, info = model.transcribe(
                str(wav),
                language=args.language,
                vad_filter=True,
                word_timestamps=False,
            )
            segments = [
                {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
                for s in segments_iter
            ]

        out_path.write_text(
            json.dumps({"video": str(video), "language": args.language, "segments": segments},
                       ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[batch]   -> {len(segments)} segments", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
