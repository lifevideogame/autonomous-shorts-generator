import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# API keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Whisper
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# Moment detection
MOMENTS_PER_HOUR = 5
MOMENT_MIN_DURATION = 120  # seconds
MOMENT_MAX_DURATION = 180  # seconds
SLICE_PADDING = 30  # seconds of padding on each side for Gemini context

# Download filters
MIN_VIDEO_DURATION = 3600  # 60 min — skip edited videos, only raw VODs/streams
MAX_VIDEOS_TO_SCAN = 50    # How far back to scan a channel

# Upload cap
MAX_UPLOADS_PER_VIDEO = 3

# Gemini
GEMINI_MODEL = "gemini-3-flash-preview"

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path("/mnt/e/pipeline-data")
OPUS_CLIP_INPUT_DIR = Path("/mnt/c/opus-clip-input")
DB_PATH = PROJECT_ROOT / "pipeline_state.db"
CREATORS_JSON = PROJECT_ROOT / "creators.json"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
