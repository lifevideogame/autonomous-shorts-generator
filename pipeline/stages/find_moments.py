import json
import logging
from pathlib import Path

from google import genai

from pipeline.config import DATA_DIR, GEMINI_API_KEY, GEMINI_MODEL, MOMENTS_PER_HOUR, PROMPTS_DIR
from pipeline.state import insert_moments, update_video_status

log = logging.getLogger(__name__)

client = None


def _get_client():
    global client
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def run(creator: str, video_id: str) -> Path:
    """Analyze transcript and find viral moments. Returns path to moments.json."""
    video_dir = DATA_DIR / creator / video_id
    transcript_path = video_dir / "transcript.json"
    moments_path = video_dir / "moments.json"

    if moments_path.exists():
        log.info("Moments already found: %s", moments_path)
        update_video_status(video_id, "moments_found")
        return moments_path

    with open(transcript_path) as f:
        transcript = json.load(f)

    full_text = transcript["text"]
    duration_sec = transcript["segments"][-1]["end"] if transcript["segments"] else 0
    duration_hours = max(duration_sec / 3600, 1)
    num_moments = int(MOMENTS_PER_HOUR * duration_hours)

    prompt_template = (PROMPTS_DIR / "find_moments.txt").read_text()
    prompt = prompt_template.format(
        num_moments=num_moments,
        transcript=full_text,
    )

    log.info("Asking Gemini to find %d moments in %.1f hours of content", num_moments, duration_hours)

    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    # Parse JSON from response
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    moments = json.loads(text)

    with open(moments_path, "w") as f:
        json.dump(moments, f, indent=2)

    insert_moments(video_id, moments)
    update_video_status(video_id, "moments_found")

    log.info("Found %d moments, saved to %s", len(moments), moments_path)
    return moments_path
