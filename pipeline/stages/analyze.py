import json
import logging
import time
from pathlib import Path

from google import genai

from pipeline.config import DATA_DIR, GEMINI_API_KEY, GEMINI_MODEL, PROMPTS_DIR, SLICE_PADDING
from pipeline.state import get_moments, update_moment_approval, update_video_status

log = logging.getLogger(__name__)

client = None


def _get_client():
    global client
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def _upload_and_wait(file_path: Path):
    """Upload a file to Gemini Files API and wait for it to be ready."""
    c = _get_client()
    uploaded = c.files.upload(file=str(file_path))
    log.info("Uploaded %s → %s (state: %s)", file_path.name, uploaded.name, uploaded.state)

    while uploaded.state.name == "PROCESSING":
        time.sleep(5)
        uploaded = c.files.get(name=uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"File upload failed: {uploaded.state.name}")

    return uploaded


def run(creator: str, video_id: str) -> Path:
    """Analyze slices with Gemini video understanding. Returns path to approved.json."""
    video_dir = DATA_DIR / creator / video_id
    slices_dir = video_dir / "slices"
    approved_path = video_dir / "approved.json"

    if approved_path.exists():
        log.info("Already analyzed: %s", approved_path)
        update_video_status(video_id, "analyzed")
        return approved_path

    moments = get_moments(video_id)
    prompt_template = (PROMPTS_DIR / "analyze_slice.txt").read_text()
    approved = []

    for m in moments:
        slice_path = slices_dir / f"moment_{m['moment_index']}_360p.mp4"
        if not slice_path.exists():
            log.warning("Slice not found: %s", slice_path)
            continue

        log.info("Analyzing moment %d: %s", m["moment_index"], m["title"])

        try:
            uploaded_file = _upload_and_wait(slice_path)

            prompt = prompt_template.format(
                title=m["title"],
                reason=m["reason"],
                start=m["start_sec"],
                end=m["end_sec"],
            )

            response = _get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=[uploaded_file, prompt],
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            result = json.loads(text)

            keep = result.get("keep", False)
            refined_start = result.get("refined_start")
            refined_end = result.get("refined_end")

            # Fix slice-relative timestamps: if Gemini returned timestamps
            # relative to the slice instead of absolute, convert them.
            # The slice starts at (start_sec - SLICE_PADDING).
            slice_start = max(0, m["start_sec"] - SLICE_PADDING)
            if refined_start is not None and refined_start < slice_start:
                log.info("  Converting slice-relative timestamps: %.1f,%.1f → %.1f,%.1f",
                         refined_start, refined_end,
                         refined_start + slice_start, refined_end + slice_start)
                refined_start += slice_start
                refined_end += slice_start

            update_moment_approval(
                m["id"],
                approved=keep,
                refined_start=refined_start,
                refined_end=refined_end,
            )

            if keep:
                score = result.get("score", 5)
                approved.append({
                    "moment_index": m["moment_index"],
                    "title": m["title"],
                    "original_start": m["start_sec"],
                    "original_end": m["end_sec"],
                    "refined_start": refined_start,
                    "refined_end": refined_end,
                    "score": score,
                    "reason": result.get("reason", ""),
                    "db_id": m["id"],
                })
                log.info("  ✓ Approved (%.1f → %.1f, score=%d)", refined_start, refined_end, score)
            else:
                log.info("  ✗ Rejected: %s", result.get("reason", "no reason"))

        except Exception as e:
            log.error("Failed to analyze moment %d: %s", m["moment_index"], e)
            continue

    with open(approved_path, "w") as f:
        json.dump(approved, f, indent=2)

    update_video_status(video_id, "analyzed")
    log.info("Analysis complete: %d/%d moments approved", len(approved), len(moments))
    return approved_path
