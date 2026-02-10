import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import boto3

from pipeline.config import AWS_REGION, DATA_DIR, MAX_UPLOADS_PER_VIDEO, OPUS_CLIP_INPUT_DIR, S3_BUCKET
from pipeline.state import update_moment_s3_url, update_video_status

log = logging.getLogger(__name__)


def _extract_hq_clip(source: Path, start: float, end: float, out_path: Path):
    """Extract a clip from the original HQ source."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-to", str(end),
        "-i", str(source),
        "-c:v", "libx264", "-crf", "18", "-preset", "slow",
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg HQ extract failed: {result.stderr[-300:]}")


def _sanitize_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "" for c in s).strip().replace(" ", "_")[:50]


def run(creator: str, video_id: str) -> list[str]:
    """Extract HQ clips and upload to S3. Returns list of S3 URLs."""
    video_dir = DATA_DIR / creator / video_id
    source = video_dir / "source.mp4"
    approved_path = video_dir / "approved.json"
    final_dir = video_dir / "final"
    final_dir.mkdir(exist_ok=True)

    with open(approved_path) as f:
        approved = json.load(f)

    if not approved:
        log.info("No approved moments for %s — skipping upload", video_id)
        update_video_status(video_id, "uploaded")
        return []

    # Rank by viral score (highest first), then cap
    approved.sort(key=lambda m: m.get("score", 5), reverse=True)
    to_upload = approved[:MAX_UPLOADS_PER_VIDEO]
    log.info("Uploading top %d/%d approved moments by score (cap=%d)", len(to_upload), len(approved), MAX_UPLOADS_PER_VIDEO)

    s3 = boto3.client("s3", region_name=AWS_REGION)
    date_str = datetime.now().strftime("%Y-%m-%d")
    urls = []

    for m in to_upload:
        safe_title = _sanitize_filename(m["title"])
        local_path = final_dir / f"moment_{m['moment_index']}.mp4"

        # Extract HQ clip from original source
        log.info("Extracting HQ clip: moment %d (%.1f → %.1f)", m["moment_index"], m["refined_start"], m["refined_end"])
        _extract_hq_clip(source, m["refined_start"], m["refined_end"], local_path)

        # Copy to local OpusClip input folder
        opus_filename = f"{creator}_{video_id}_{safe_title}.mp4"
        opus_path = OPUS_CLIP_INPUT_DIR / opus_filename
        shutil.copy2(str(local_path), str(opus_path))
        log.info("Saved to OpusClip input: %s", opus_path)

        # Upload to S3
        s3_key = f"{creator}/{date_str}/{video_id}_{safe_title}.mp4"
        log.info("Uploading to s3://%s/%s", S3_BUCKET, s3_key)
        s3.upload_file(str(local_path), S3_BUCKET, s3_key)

        s3_url = f"s3://{S3_BUCKET}/{s3_key}"
        urls.append(s3_url)

        if m.get("db_id"):
            update_moment_s3_url(m["db_id"], s3_url)

    update_video_status(video_id, "uploaded")
    log.info("Upload complete: %d clips to S3 + local OpusClip folder", len(urls))
    return urls
