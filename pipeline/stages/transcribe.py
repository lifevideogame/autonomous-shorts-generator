import json
import logging
from pathlib import Path

from pipeline.config import DATA_DIR, WHISPER_MODEL
from pipeline.state import update_video_status

log = logging.getLogger(__name__)


def run(creator: str, video_id: str) -> Path:
    """Transcribe source.mp4 using Whisper. Returns path to transcript.json."""
    video_dir = DATA_DIR / creator / video_id
    source = video_dir / "source.mp4"
    transcript_path = video_dir / "transcript.json"

    if transcript_path.exists():
        log.info("Transcript already exists: %s", transcript_path)
        update_video_status(video_id, "transcribed")
        return transcript_path

    if not source.exists():
        raise FileNotFoundError(f"Source video not found: {source}")

    log.info("Transcribing %s with Whisper model=%s", source, WHISPER_MODEL)

    import whisper

    model = whisper.load_model(WHISPER_MODEL, device="cpu")
    result = model.transcribe(str(source), language="en", word_timestamps=True, fp16=False)

    # Build output format
    transcript = {
        "text": result["text"],
        "segments": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            }
            for seg in result["segments"]
        ],
    }

    with open(transcript_path, "w") as f:
        json.dump(transcript, f, indent=2)

    log.info("Transcript saved: %s (%d segments)", transcript_path, len(transcript["segments"]))
    update_video_status(video_id, "transcribed")
    return transcript_path
