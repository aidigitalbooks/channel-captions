#!/usr/bin/env python3
"""
Small HeyGen helper (stdlib only).

  python heygen.py list-new --prefix "Nora Valeen" --prefix "Gus Kessler" --hours 48   -> completed video IDs, one per line
  python heygen.py fetch VIDEO_ID --out work/             -> downloads video.mp4 (+ captions.srt if available)

Needs env var HEYGEN_API_KEY.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.heygen.com"


RETRY_CODES = {408, 410, 425, 429, 500, 502, 503, 504}


def call(path, attempts=4):
    """GET a HeyGen API path. Retries brief HeyGen hiccups (e.g. the 410s seen on 2026-11-18)."""
    key = os.environ.get("HEYGEN_API_KEY")
    if not key:
        sys.exit("HEYGEN_API_KEY is not set")
    req = urllib.request.Request(API + path, headers={"X-Api-Key": key, "Accept": "application/json"})
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_CODES or i == attempts - 1:
                raise
            wait = 15 * (i + 1)
        except urllib.error.URLError:
            if i == attempts - 1:
                raise
            wait = 15 * (i + 1)
        print(f"HeyGen API busy ({path}); retrying in {wait}s", file=sys.stderr)
        time.sleep(wait)


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "channel-captions/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)


def to_epoch(v):
    if v is None:
        return None
    if isinstance(v, str) and not v.replace(".", "", 1).isdigit():
        from datetime import datetime
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    try:
        v = float(v)
        return v / 1000.0 if v > 1e12 else v
    except (TypeError, ValueError):
        return None


LIST_PATHS = [
    # v1/video.list may answer 410 GONE like v1/video_status.get did (2026-11-23); fall back to newer ones.
    "/v1/video.list",
    "/v3/videos",
    "/v2/videos",
]


def unpack_list(raw):
    """Return (videos, next_token) from any of HeyGen's list response shapes."""
    data = raw.get("data", raw)
    if isinstance(data, list):
        return data, raw.get("token") or raw.get("next_token")
    videos = data.get("videos") or data.get("list") or data.get("items") or []
    return videos, data.get("token") or data.get("next_token") or raw.get("next_token")


def list_videos(token=None):
    """One page of recent videos from the first list endpoint that answers."""
    errors = []
    for path in LIST_PATHS:
        sep = "&" if "?" in path else "?"
        try:
            raw = call(path + (f"{sep}token={token}" if token else ""), attempts=2)
        except urllib.error.HTTPError as e:
            errors.append(f"{path} -> HTTP {e.code}")
            continue
        except urllib.error.URLError as e:
            errors.append(f"{path} -> {e.reason}")
            continue
        videos, nxt = unpack_list(raw)
        print(f"list endpoint: {path} ({len(videos)} videos)", file=sys.stderr)
        return videos, nxt
    sys.exit("HeyGen video list failed on every endpoint: " + "; ".join(errors))


def vfields(v):
    vid = v.get("video_id") or v.get("id")
    title = v.get("video_title") or v.get("title") or v.get("name") or ""
    status = (v.get("status") or "").lower()
    return vid, title, status, to_epoch(v.get("created_at"))


def list_new(prefixes, hours):
    cutoff = time.time() - hours * 3600
    videos, _ = list_videos()
    for v in videos:
        vid, title, status, created = vfields(v)
        if not vid or status not in ("completed", "complete", "success", "succeeded", "done"):
            continue
        if not any(title.lower().startswith(p.lower()) for p in prefixes):
            continue
        if created is not None and created < cutoff:
            continue
        print(vid)


STATUS_PATHS = [
    # HeyGen began answering 410 GONE on the v1 status endpoint (2026-11-23), so try the newer
    # endpoints too and use the first that answers.
    "/v1/video_status.get?video_id={id}",
    "/v2/videos/{id}",
    "/v3/videos/{id}",
    "/v2/video/{id}",
]


def first(d, *keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return None


def get_status(video_id):
    errors = []
    for tmpl in STATUS_PATHS:
        path = tmpl.format(id=video_id)
        try:
            raw = call(path, attempts=2)
        except urllib.error.HTTPError as e:
            errors.append(f"{path} -> HTTP {e.code}")
            continue
        except urllib.error.URLError as e:
            errors.append(f"{path} -> {e.reason}")
            continue
        d = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        if isinstance(d.get("video"), dict):
            d = d["video"]
        print(f"status endpoint: {path} (fields: {', '.join(sorted(d.keys()))})")
        return d
    sys.exit("HeyGen status lookup failed on every endpoint: " + "; ".join(errors))


def fetch(video_id, out):
    os.makedirs(out, exist_ok=True)
    d = get_status(video_id)
    status = (first(d, "status", "video_status") or "").lower()
    if status not in ("completed", "complete", "success", "succeeded", "done"):
        sys.exit(f"video {video_id} is not completed (status={status})")
    video_url = first(d, "video_url", "url", "video_url_caption_free", "download_url")
    if not video_url:
        sys.exit("no video_url in HeyGen response")
    download(video_url, os.path.join(out, "video.mp4"))
    srt_url = first(d, "caption_url", "subtitle_url", "srt_url", "captions_url")
    if srt_url:
        download(srt_url, os.path.join(out, "captions.srt"))
        print("downloaded video + captions")
    else:
        print("downloaded video (no caption file from HeyGen)")
    title = first(d, "video_title", "title", "name") or lookup_title(video_id)
    with open(os.path.join(out, "meta.json"), "w") as f:
        # "untitled" never matches any channel, so videos that can't be identified are skipped
        json.dump({"video_id": video_id, "title": title or "untitled",
                   "duration": d.get("duration")}, f)


def lookup_title(video_id):
    """The status response doesn't always include the title; find it in the video list."""
    token = None
    for _ in range(10):  # up to ~10 pages of recent videos
        try:
            videos, token = list_videos(token)
        except SystemExit:
            return ""
        for v in videos:
            vid, title, _, _ = vfields(v)
            if vid == video_id:
                return title
        if not token:
            break
    return ""


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("list-new")
    a.add_argument("--prefix", action="append", required=True)
    a.add_argument("--hours", type=float, default=48)
    b = sub.add_parser("fetch")
    b.add_argument("video_id")
    b.add_argument("--out", default="work")
    args = ap.parse_args()
    if args.cmd == "list-new":
        list_new(args.prefix, args.hours)
    else:
        fetch(args.video_id, args.out)


if __name__ == "__main__":
    main()
