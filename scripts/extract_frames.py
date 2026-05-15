"""
Extract frames from a video window using ffmpeg.

Usage:
    python extract_frames.py --video <path> --start MM:SS --end MM:SS \
        --fps 0.5 --output-dir <dir>

Output:
    - PNG files named like 'frame_002820.png' where the number is the timestamp
      in centiseconds of the ORIGINAL video (so 002820 = 00:28.20).
    - Stdout: JSON manifest { "frames": [{"path": ..., "timestamp": 47.5}, ...] }
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def parse_timestamp(ts: str) -> float:
    parts = ts.strip().split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Cannot parse timestamp: {ts}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--fps", type=float, default=0.5,
                   help="Frames per second to extract (default 0.5 = one every 2s)")
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH.", file=sys.stderr)
        return 2

    video = Path(args.video)
    if not video.exists():
        print(f"ERROR: video not found: {video}", file=sys.stderr)
        return 1

    start_sec = parse_timestamp(args.start)
    end_sec = parse_timestamp(args.end)
    duration = end_sec - start_sec
    if duration <= 0:
        print("ERROR: end must be greater than start", file=sys.stderr)
        return 1

    out_dir = Path(args.output_dir)
    if out_dir.exists():
        for f in out_dir.glob("frame_*.png"):
            f.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = out_dir / "raw_%05d.png"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", str(start_sec),
        "-t", str(duration),
        "-i", str(video),
        "-vf", f"fps={args.fps},scale=960:-2",
        str(pattern),
    ]
    print(f"[sentinela] extracting frames at {args.fps} fps...", file=sys.stderr)
    subprocess.run(cmd, check=True)

    interval = 1.0 / args.fps
    manifest = []
    raw_frames = sorted(out_dir.glob("raw_*.png"))
    for i, raw in enumerate(raw_frames):
        ts = start_sec + i * interval
        centi = int(round(ts * 100))
        renamed = out_dir / f"frame_{centi:08d}.png"
        raw.rename(renamed)
        manifest.append({"path": str(renamed), "timestamp": round(ts, 2)})

    print(json.dumps({"frames": manifest}, indent=2))
    print(f"[sentinela] wrote {len(manifest)} frames to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
