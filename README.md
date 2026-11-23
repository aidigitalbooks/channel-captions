# Channel captions

**This is the only caption repo.** It handles Gus Kessler, Nora Valeen, Sasha M and Fat Fortune.
The old `gus-captions` repo is retired: don't add it back to the Cloudflare relay.

One caption pipeline for every AI channel. Burns captions into finished HeyGen videos and
publishes each one as a GitHub Release with a public MP4 link for Metricool.

**How a video is matched to its channel:** by the start of its HeyGen title, using `channels.json`.
"Nora Valeen — Sleep tip" → Nora. A title that matches no channel is skipped; nothing is guessed.
Output files are named after the channel (`nora-<id>.mp4`) and every release lists the channel and
its Metricool brand ID, so it's checked again before scheduling.

Caption look ("gus" style): white rounded box, bold black serif (Lora), 2–5 words at a time.
Words are black by default. "Never say X." puts X in red; "Say Y." puts Y in green.
For scripts that don't use that wording, add `highlights/<slug>-<video id>.json` with
`{"red": [phrases], "green": [phrases]}` and re-run: a separate `-color` release is made.

**Captions never cover the face.** The video is scanned for the presenter's face (human first,
then a cat face for Fat Fortune) and captions go just below it, or above it if there's no room.
If no face is found at all, captions go low in the frame (70% down) instead of at chest height.

## Add a new channel
Edit `channels.json` on GitHub (pencil icon), copy a block, change the values, commit. That's all:
no new repo, secrets, token or Worker change.

| Field | Meaning |
|---|---|
| `name` | Channel name |
| `title_starts_with` | HeyGen titles for this channel must start with this (use the full persona name) |
| `slug` | Short lowercase name used in file names (must be unique) |
| `caption_style` | Caption look (currently `gus`) |
| `caption_y` | Caption height: 0 = top, 1 = bottom |
| `metricool_brand_id` | The Metricool brand this channel posts to |
| `heygen_avatar_group_id` | The HeyGen avatar this channel uses (checked when videos are made) |

## One-time setup
1. Repo is **Public** (free Actions minutes; video links work in Metricool). Keys stay private in Secrets.
2. **Settings → Secrets and variables → Actions → New repository secret**: `HEYGEN_API_KEY`.
3. **Settings → Actions → General → Workflow permissions → Read and write permissions → Save.**
4. Cloudflare Worker (`relay/worker.js`): set `GITHUB_REPO` to exactly `aidigitalbooks/channel-captions` (nothing else).

## Run by hand
**Actions → Caption channel videos → Run workflow**, paste a HeyGen video ID.

Font: Lora (SIL Open Font License).
