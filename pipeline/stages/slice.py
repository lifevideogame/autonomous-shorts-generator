import logging
import subprocess
from pathlib import Path

from pipeline.config import DATA_DIR, SLICE_PADDING
from pipeline.state import get_moments, update_video_status

log = logging.getLogger(__name__)


def run(creator: str, video_id: str) -> Path:
    """Slice 360p clips for each moment. Returns path to slices/ directory."""
    video_dir = DATA_DIR / creator / video_id
    source = video_dir / "source.mp4"
    slices_dir = video_dir / "slices"
    slices_dir.mkdir(exist_ok=True)

    moments = get_moments(video_id)
    if not moments:
        raise ValueError(f"No moments found for {video_id}")

    for m in moments:
        out_path = slices_dir / f"moment_{m['moment_index']}_360p.mp4"
        if out_path.exists():
            log.info("Slice already exists: %s", out_path)
            continue

        start = max(0, m["start_sec"] - SLICE_PADDING)
        end = m["end_sec"] + SLICE_PADDING

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", str(source),
            "-vf", "scale=-2:360",
            "-c:v", "libx264", "-crf", "28", "-preset", "fast",
            "-c:a", "aac", "-b:a", "64k",
            str(out_path),
        ]

        log.info("Slicing moment %d: %.1fs → %.1fs", m["moment_index"], start, end)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            log.error("ffmpeg failed for moment %d: %s", m["moment_index"], result.stderr[-300:])
            continue

    update_video_status(video_id, "sliced")
    return slices_dir
