"""
Scan extracted frames for the OLD product name (or any caller-supplied term).

Use case: when a VSL switches from product A to product B, the new render
sometimes leaks a B-roll, packshot, or label still showing product A. This
script runs OCR over every PNG in a directory and flags frames whose detected
text contains the supplied term(s) — so the auditor doesn't depend on visual
sampling to catch leftover packshots.

Engine selection (automatic, no user knob):
- If CUDA GPU is available: use EasyOCR + GPU (fastest, ~1-2min for 1500 frames).
- Otherwise: use RapidOCR + CPU (ONNX-based, ~5-8min for 1500 frames on a
  modest laptop — 5-10x faster than EasyOCR + CPU).

Both engines return matches with [bbox, text, confidence]; the matching logic
is shared.

Usage:
    python scan_old_label.py --frames-dir <dir> --term LIPOTRINE [--term OTHER] \
        [--threshold 0.30] [--output <json>]

Output:
    Stdout JSON: { "hits": [{"timestamp": 2790.0, "frame": "...", "matches": [...]}, ...],
                   "scanned": N, "term_matches": {"LIPOTRINE": k, ...},
                   "engine": "easyocr-gpu" | "rapidocr-cpu" }
    Stderr: progress.
"""

import argparse
import json
import sys
from pathlib import Path


def ts_from_name(path: Path) -> float:
    stem = path.stem  # frame_00279000
    try:
        centi = int(stem.split("_", 1)[1])
        return centi / 100.0
    except (IndexError, ValueError):
        return -1.0


def has_cuda() -> bool:
    """Return True if a CUDA-capable GPU is available via torch."""
    try:
        import torch  # type: ignore
        return bool(torch.cuda.is_available())
    except Exception:
        return False


class OCREngine:
    """Unified interface around EasyOCR (GPU) or RapidOCR (CPU).

    Both engines expose `read(path) -> list[(text, confidence)]`.
    """

    def __init__(self, name: str):
        self.name = name
        self._reader = None

    @classmethod
    def autoselect(cls, lang: str = "en") -> "OCREngine":
        if has_cuda():
            return EasyOCRGPU(lang)
        return RapidOCRCPU()


class EasyOCRGPU(OCREngine):
    def __init__(self, lang: str = "en"):
        super().__init__("easyocr-gpu")
        import easyocr  # type: ignore
        self._reader = easyocr.Reader([lang], gpu=True, verbose=False)

    def read(self, path: str):
        out = []
        for det in self._reader.readtext(path):
            text = det[1] if len(det) > 1 else ""
            conf = float(det[2]) if len(det) > 2 else 0.0
            out.append((text, conf))
        return out


class RapidOCRCPU(OCREngine):
    def __init__(self):
        super().__init__("rapidocr-cpu")
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
        self._reader = RapidOCR()

    def read(self, path: str):
        result, _elapse = self._reader(path)
        out = []
        if not result:
            return out
        for det in result:
            # rapidocr: [bbox, text, confidence]
            text = det[1] if len(det) > 1 else ""
            try:
                conf = float(det[2]) if len(det) > 2 else 0.0
            except (TypeError, ValueError):
                conf = 0.0
            out.append((text, conf))
        return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--frames-dir", required=True)
    p.add_argument("--term", action="append", required=True,
                   help="Term to search for in OCR output (case-insensitive). "
                        "Pass multiple --term flags for multiple variants.")
    p.add_argument("--lang", default="en",
                   help="OCR language code (default: en). Used only by EasyOCR engine.")
    p.add_argument("--threshold", type=float, default=0.30,
                   help="Min confidence to keep an OCR detection (default 0.30)")
    p.add_argument("--output",
                   help="Optional path to write the JSON report. "
                        "Stdout always also gets the JSON.")
    p.add_argument("--engine", choices=["auto", "easyocr-gpu", "rapidocr-cpu"],
                   default="auto",
                   help="Force a specific engine. Default 'auto' picks easyocr-gpu "
                        "when CUDA is available, otherwise rapidocr-cpu.")
    args = p.parse_args()

    frames_dir = Path(args.frames_dir)
    if not frames_dir.exists():
        print(f"ERROR: frames dir not found: {frames_dir}", file=sys.stderr)
        return 1

    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        print(f"ERROR: no frame_*.png found in {frames_dir}", file=sys.stderr)
        return 1

    # Engine selection
    if args.engine == "auto":
        engine = OCREngine.autoselect(args.lang)
    elif args.engine == "easyocr-gpu":
        engine = EasyOCRGPU(args.lang)
    elif args.engine == "rapidocr-cpu":
        engine = RapidOCRCPU()
    else:
        print(f"ERROR: unknown engine {args.engine}", file=sys.stderr)
        return 1

    print(f"[sentinela-ocr] engine={engine.name} ({len(frames)} frames)",
          file=sys.stderr)

    terms_lc = [t.lower() for t in args.term]
    term_counts = {t: 0 for t in args.term}
    hits = []

    print(f"[sentinela-ocr] scanning for terms: {args.term}", file=sys.stderr)
    for i, frame in enumerate(frames, 1):
        if i % 50 == 0 or i == len(frames):
            print(f"[sentinela-ocr]   {i}/{len(frames)}...", file=sys.stderr)
        try:
            detections = engine.read(str(frame))
        except Exception as e:
            print(f"[sentinela-ocr] WARN: {frame.name}: {e}", file=sys.stderr)
            continue

        frame_matches = []
        for text, conf in detections:
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
        "engine": engine.name,
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
