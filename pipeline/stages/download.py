import json
import logging
import re
import subprocess
from pathlib import Path

from pipeline.config import CREATORS_JSON, DATA_DIR, MAX_VIDEOS_TO_SCAN, MIN_VIDEO_DURATION
from pipeline.state import is_video_processed, upsert_video

log = logging.getLogger(__name__)


def load_creators() -> list[dict]:
    with open(CREATORS_JSON) as f:
        data = json.load(f)
    creators = []
    for cat in data["categories"]:
        for c in cat["creators"]:
            if c.get("channel_url"):
                creators.append(c)
    return creators


def _get_channel_videos(channel_url: str, max_results: int = MAX_VIDEOS_TO_SCAN) -> list[dict]:
    """Fetch video listings from a channel with duration info."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--playlist-end", str(max_results),
        "--print", "%(id)s\t%(url)s\t%(title)s\t%(duration)s",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        log.error("yt-dlp listing failed for %s: %s", channel_url, result.stderr)
        return []

    videos = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 3)
        if len(parts) < 4:
            continue
        try:
            duration = float(parts[3])
        except (ValueError, TypeError):
            continue
        videos.append({
            "id": parts[0],
            "url": parts[1],
            "title": parts[2],
            "duration": duration,
        })
    return videos


def _needs_cookies(url: str) -> bool:
    return "kick.com" in url


def download_video(creator_name: str, video_id: str, url: str) -> Path:
    """Download a single video. Returns the path to source.mp4."""
    out_dir = DATA_DIR / creator_name / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "source.mp4"

    if out_path.exists():
        log.info("Already downloaded: %s", out_path)
        return out_path

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio",
        "--merge-output-format", "mp4",
        "--write-auto-sub", "--sub-lang", "en", "--convert-subs", "srt",
        "-o", str(out_path),
        url,
    ]

    if _needs_cookies(url):
        cmd.insert(1, "--cookies-from-browser")
        cmd.insert(2, "chrome")

    log.info("Downloading %s → %s", url, out_path)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed: {result.stderr[-500:]}")

    if not out_path.exists():
        candidates = list(out_dir.glob("source.*"))
        if candidates:
            out_path = candidates[0]
        else:
            raise RuntimeError(f"Download completed but no file found in {out_dir}")

    return out_path


def run(creator_name: str | None = None, url: str | None = None) -> list[dict]:
    """Download unprocessed long-form videos. Returns list of {creator, video_id, path}."""
    results = []

    if url:
        video_id = _extract_video_id(url)
        cname = creator_name or "unknown"
        if not is_video_processed(video_id):
            path = download_video(cname, video_id, url)
            upsert_video(video_id, cname, url, "downloaded")
            results.append({"creator": cname, "video_id": video_id, "path": str(path)})
        return results

    creators = load_creators()
    if creator_name:
        creators = [c for c in creators if c["name"] == creator_name]
        if not creators:
            raise ValueError(f"Creator '{creator_name}' not found or has no channel_url")

    for creator in creators:
        cname = creator["name"]
        channel_url = creator["channel_url"]
        log.info("Checking %s (%s)", cname, channel_url)

        try:
            videos = _get_channel_videos(channel_url)
        except Exception as e:
            log.error("Failed to list videos for %s: %s", cname, e)
            continue

        for vid in videos:
            if vid["duration"] < MIN_VIDEO_DURATION:
                log.info("Skipping %s (%.0fmin, too short): %s", vid["id"], vid["duration"] / 60, vid["title"])
                continue

            if is_video_processed(vid["id"]):
                log.info("Already processed: %s", vid["id"])
                continue

            try:
                log.info("Queueing %s (%.0fmin): %s", vid["id"], vid["duration"] / 60, vid["title"])
                path = download_video(cname, vid["id"], vid["url"])
                upsert_video(vid["id"], cname, vid["url"], "downloaded")
                results.append({"creator": cname, "video_id": vid["id"], "path": str(path)})
                break  # Only the latest long VOD per creator
            except Exception as e:
                log.error("Download failed for %s: %s", vid["id"], e)
                continue

    return results


def _extract_video_id(url: str) -> str:
    """Extract video ID from a YouTube/Twitch/Kick URL."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})", url)
    if m:
        return m.group(1)
    m = re.search(r"twitch\.tv/videos/(\d+)", url)
    if m:
        return f"twitch_{m.group(1)}"
    m = re.search(r"kick\.com/(?:video/)?([a-zA-Z0-9_-]+)", url)
    if m:
        return f"kick_{m.group(1)}"
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:12]
