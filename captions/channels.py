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
    hits = [c for c in load() if t.startswith(c["title_starts_with"].strip().lower())]
    if not hits:
        return None
    # longest prefix wins, so "Nora Valeen Kids" never falls into "Nora Valeen"
    return max(hits, key=lambda c: len(c["title_starts_with"]))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "prefixes":
        for c in load():
            print(c["title_starts_with"])
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
