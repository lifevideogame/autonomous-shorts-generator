import logging
import shutil
from pathlib import Path

import boto3

from pipeline.config import AWS_REGION, DATA_DIR, S3_BUCKET
from pipeline.state import get_approved_moments, update_video_status

log = logging.getLogger(__name__)


def _verify_s3_upload(s3_url: str) -> bool:
    """Check that a file exists in S3 via HEAD object."""
    if not s3_url.startswith("s3://"):
        return False
    parts = s3_url.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]
    s3 = boto3.client("s3", region_name=AWS_REGION)
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def run(creator: str, video_id: str):
    """Delete large files after confirming S3 uploads succeeded."""
    video_dir = DATA_DIR / creator / video_id

    # Verify all uploads succeeded before deleting anything
    approved = get_approved_moments(video_id)
    for m in approved:
        if m["s3_url"] and not _verify_s3_upload(m["s3_url"]):
            log.error("S3 verification failed for %s — aborting cleanup", m["s3_url"])
            return

    # Delete large files
    source = video_dir / "source.mp4"
    slices_dir = video_dir / "slices"
    final_dir = video_dir / "final"

    deleted = []
    if source.exists():
        source.unlink()
        deleted.append("source.mp4")
    if slices_dir.exists():
        shutil.rmtree(slices_dir)
        deleted.append("slices/")
    if final_dir.exists():
        shutil.rmtree(final_dir)
        deleted.append("final/")

    update_video_status(video_id, "cleaned")
    log.info("Cleanup complete for %s: removed %s", video_id, ", ".join(deleted) or "nothing")
