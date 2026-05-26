"""
Scan extracted frames for the OLD product name (or any caller-supplied term).

Use case: when a VSL switches from product A to product B, the new render
sometimes leaks a B-roll, packshot, or label still showing product A. This
script runs OCR over every PNG in a directory and flags frames whose detected
text contains the supplied term(s) — so the auditor doesn't depend on visual
sampling to catch leftover packshots.

Usage:
    python scan_old_label.py --frames-dir <dir> --term LIPOTRINE [--term OTHER] \
        [--lang en] [--threshold 0.30] [--output <json>]

Output:
    Stdout JSON: { "hits": [{"timestamp": 2790.0, "frame": "...", "matches": [...]}, ...],
                   "scanned": N, "term_matches": {"LIPOTRINE": k, ...} }
    Stderr: progress.

Notes:
- Uses easyocr (Reader). GPU if available, otherwise CPU.
- Match is case-insensitive substring match against the detected text.
  Useful for catching label artifacts like "LIPO TRINE" or partial reads.
- `--threshold` filters out OCR detections with low confidence.
- Frame timestamp is parsed from filename "frame_<centi>.png" (matches the
  extract_frames.py output).
"""

import argparse
import json
import os
import sys
from pathlib import Path


def ts_from_name(path: Path) -> float:
    stem = path.stem  # frame_00279000
    try:
        centi = int(stem.split("_", 1)[1])
        return centi / 100.0
    except (IndexError, ValueError):
        return -1.0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--frames-dir", required=True)
    p.add_argument("--term", action="append", required=True,
                   help="Term to search for in OCR output (case-insensitive). "
                        "Pass multiple --term flags for multiple variants.")
    p.add_argument("--lang", default="en",
                   help="OCR language code (default: en). For pt+en use 'en' "
                        "since product labels are usually English-language.")
    p.add_argument("--threshold", type=float, default=0.30,
                   help="Min confidence to keep an OCR detection (default 0.30)")
    p.add_argument("--output",
                   help="Optional path to write the JSON report. "
                        "Stdout always also gets the JSON.")
    p.add_argument("--gpu", action="store_true", default=True,
                   help="Use GPU if available (default true).")
    p.add_argument("--no-gpu", action="store_false", dest="gpu")
    args = p.parse_args()

    frames_dir = Path(args.frames_dir)
    if not frames_dir.exists():
        print(f"ERROR: frames dir not found: {frames_dir}", file=sys.stderr)
        return 1

    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        print(f"ERROR: no frame_*.png found in {frames_dir}", file=sys.stderr)
        return 1

    print(f"[sentinela-ocr] loading easyocr (lang={args.lang}, gpu={args.gpu})...",
          file=sys.stderr)
    import easyocr  # type: ignore
    reader = easyocr.Reader([args.lang], gpu=args.gpu, verbose=False)

    terms_lc = [t.lower() for t in args.term]
    term_counts = {t: 0 for t in args.term}
    hits = []

    print(f"[sentinela-ocr] scanning {len(frames)} frames for terms: {args.term}",
          file=sys.stderr)
    for i, frame in enumerate(frames, 1):
        if i % 50 == 0 or i == len(frames):
            print(f"[sentinela-ocr]   {i}/{len(frames)}...", file=sys.stderr)
        try:
            detections = reader.readtext(str(frame))
        except Exception as e:
            print(f"[sentinela-ocr] WARN: {frame.name}: {e}", file=sys.stderr)
            continue

        frame_matches = []
        for det in detections:
            # easyocr returns: [bbox, text, confidence]
            text = det[1] if len(det) > 1 else ""
            conf = float(det[2]) if len(det) > 2 else 0.0
            if conf < args.threshold:
                continue
            text_lc = text.lower()
            # normalize: collapse non-alnum to detect "LIPO TRINE", "LIPO-TRINE", etc.
            text_norm = "".join(c if c.isalnum() else "" for c in text_lc)
            for orig, lc in zip(args.term, terms_lc):
                lc_norm = "".join(c if c.isalnum() else "" for c in lc)
                if lc in text_lc or (lc_norm and lc_norm in text_norm):
                    frame_matches.append({
                        "term": orig,
                        "text": text,
                        "confidence": round(conf, 3),
                    })
                    term_counts[orig] += 1
                    break

        if frame_matches:
            hits.append({
                "timestamp": ts_from_name(frame),
                "frame": str(frame),
                "matches": frame_matches,
            })

    report = {
        "scanned": len(frames),
        "term_matches": term_counts,
        "hits": hits,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[sentinela-ocr] wrote report to {args.output}", file=sys.stderr)

    print(json.dumps(report, indent=2))
    print(f"[sentinela-ocr] DONE. {len(hits)} frame(s) with hits across "
          f"{sum(term_counts.values())} matches.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
