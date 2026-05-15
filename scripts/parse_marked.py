"""
Parse a marked script with [old text] <new text> annotations.

Convention:
    [texto antigo]   = what was in the previous version and should be removed
    <texto novo>     = what should be in the new version

Usage:
    python parse_marked.py --file script.txt
    python parse_marked.py --text "Buy for [\$67] <\$57>..."

Output: JSON with the list of replacement pairs and their context.

    {
      "pairs": [
        {
          "index": 0,
          "old": "$67",
          "new": "$57",
          "context_before": "Buy now for just ",
          "context_after": " and get..."
        },
        ...
      ]
    }
"""

import argparse
import json
import re
import sys
from pathlib import Path

PAIR_RE = re.compile(r"\[(?P<old>[^\[\]]+?)\]\s*<(?P<new>[^<>]+?)>")
CONTEXT_CHARS = 40


def extract_pairs(text: str):
    pairs = []
    for i, m in enumerate(PAIR_RE.finditer(text)):
        start, end = m.span()
        before = text[max(0, start - CONTEXT_CHARS):start].replace("\n", " ").strip()
        after = text[end:end + CONTEXT_CHARS].replace("\n", " ").strip()
        pairs.append({
            "index": i,
            "old": m.group("old").strip(),
            "new": m.group("new").strip(),
            "context_before": before,
            "context_after": after,
        })
    return pairs


def main() -> int:
    p = argparse.ArgumentParser()
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="Path to .txt file with the marked script")
    src.add_argument("--text", help="Inline marked text")
    args = p.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")
    else:
        text = args.text

    pairs = extract_pairs(text)
    print(json.dumps({"pairs": pairs}, ensure_ascii=False, indent=2))

    if not pairs:
        print("[sentinela] WARNING: no [old] <new> pairs found.", file=sys.stderr)
    else:
        print(f"[sentinela] extracted {len(pairs)} replacement pair(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
