"""
Pull exact `start` timestamps from a transcribe.py JSON output for given snippets.

Use this BEFORE writing any "## Alterações" bullet. The skill prohibits mental
approximation of timestamps — every audio-substitution item in the report must
cite the `start` of the matching transcript segment, no exceptions.

Usage:
    python pull_timestamps.py --transcript path/to/transcript.json \
        --snippet "Its name is Memopezil" \
        --snippet "address printed on Memopezil" \
        [--case-insensitive] [--threshold 0.6]

Output (stdout, JSON):
    {
        "matches": [
            {
                "snippet": "Its name is Memopezil",
                "matched_text": "Its name is memo puzzle",
                "start": 1827.14,
                "timestamp": "00:30:27",
                "score": 0.71
            },
            ...
        ],
        "misses": ["...snippets with no match..."]
    }

Match strategy:
- Normalizes both snippet and segment text (lowercase + collapse non-alnum).
- Finds the best-overlap segment by token overlap ratio.
- Default threshold 0.6 — drops to "misses" if no segment scores above.

This is deliberately blunt: it's a guard rail, not a precise NLP tool. If the
script can't match a snippet, that means the audit text doesn't actually
appear in the transcript verbatim, which is itself worth knowing before the
report goes out.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def normalize(text: str) -> list[str]:
    """Lowercase + collapse non-alnum, return token list."""
    return re.findall(r"[a-z0-9]+", text.lower())


def overlap_score(query_tokens: list[str], segment_tokens: list[str]) -> float:
    """Fraction of query tokens present in the segment, weighted by order."""
    if not query_tokens:
        return 0.0
    seg_set = set(segment_tokens)
    hits = sum(1 for t in query_tokens if t in seg_set)
    return hits / len(query_tokens)


def hhmmss(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def best_match(snippet: str, segments: list[dict], threshold: float):
    q_tokens = normalize(snippet)
    best = None
    for seg in segments:
        seg_tokens = normalize(seg["text"])
        score = overlap_score(q_tokens, seg_tokens)
        if best is None or score > best["score"]:
            best = {"seg": seg, "score": score}
    if best and best["score"] >= threshold:
        return best
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--transcript", required=True,
                   help="Path to transcribe.py JSON output.")
    p.add_argument("--snippet", action="append", required=True,
                   help="Text snippet to find. Pass multiple --snippet flags.")
    p.add_argument("--threshold", type=float, default=0.6,
                   help="Min token overlap to consider a match (default 0.6).")
    args = p.parse_args()

    transcript = Path(args.transcript)
    if not transcript.exists():
        print(f"ERROR: transcript not found: {transcript}", file=sys.stderr)
        return 1

    data = json.loads(transcript.read_text(encoding="utf-8"))
    segments = data.get("segments") or []
    if not segments:
        print("ERROR: no segments in transcript", file=sys.stderr)
        return 1

    matches = []
    misses = []
    for snippet in args.snippet:
        result = best_match(snippet, segments, args.threshold)
        if result:
            seg = result["seg"]
            matches.append({
                "snippet": snippet,
                "matched_text": seg["text"],
                "start": seg["start"],
                "timestamp": hhmmss(seg["start"]),
                "score": round(result["score"], 3),
            })
        else:
            misses.append(snippet)

    out = {"matches": matches, "misses": misses}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
