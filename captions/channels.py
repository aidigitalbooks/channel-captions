#!/usr/bin/env python3
"""
Look up which channel a HeyGen video belongs to, from its title.

  python channels.py match "Nora Valeen — The Sandbag Trick"   -> prints slug,caption_y,brand_id,name  (exit 3 if no match)
  python channels.py prefixes                                   -> prints every title prefix, one per line
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "..", "channels.json")


def load():
    with open(CONFIG, encoding="utf-8") as f:
        chans = json.load(f)["channels"]
    slugs = [c["slug"] for c in chans]
    if len(slugs) != len(set(slugs)):
        sys.exit("channels.json: two channels share the same slug")
    return chans


def match(title):
    t = (title or "").strip().lower()
    best, best_len = None, -1
    for c in load():
        for p in prefixes_of(c):
            p = p.strip().lower()
            # longest prefix wins, so "Nora Valeen Kids" never falls into "Nora Valeen"
            if p and t.startswith(p) and len(p) > best_len:
                best, best_len = c, len(p)
    return best


def prefixes_of(c):
    """title_starts_with, plus any extra title prefixes in also_title_starts_with."""
    return [c["title_starts_with"]] + list(c.get("also_title_starts_with") or [])


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "prefixes":
        for c in load():
            for p in prefixes_of(c):
                print(p)
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "match":
        c = match(sys.argv[2])
        if not c:
            sys.exit(3)
        print(f'{c["slug"]},{c.get("caption_y", 0.44)},{c.get("metricool_brand_id", "")},{c["name"]}')
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
