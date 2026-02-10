"""
Autonomous Shorts Pipeline — CLI orchestrator.

Usage:
    python3 -m pipeline.main                          # Process all creators
    python3 -m pipeline.main --creator "T3.gg"        # Single creator
    python3 -m pipeline.main --url "https://..."      # Specific video URL
    python3 -m pipeline.main --creator "T3.gg" --stage transcribe  # Resume from stage
    python3 -m pipeline.main --status                 # Show all tracked videos
"""

import argparse
import logging
import sys

from pipeline import state
from pipeline.stages import download

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")

STAGES = ["download", "transcribe", "find_moments", "slice", "analyze", "upload", "cleanup"]
STAGE_STATUS = {
    "download": "downloaded",
    "transcribe": "transcribed",
    "find_moments": "moments_found",
    "slice": "sliced",
    "analyze": "analyzed",
    "upload": "uploaded",
    "cleanup": "cleaned",
}


def _get_stage_runner(stage_name: str):
    """Lazy-import stage modules to avoid import errors when deps aren't installed."""
    from pipeline.stages import download
    if stage_name == "download":
        return download.run
    elif stage_name == "transcribe":
        from pipeline.stages import transcribe
        return transcribe.run
    elif stage_name == "find_moments":
        from pipeline.stages import find_moments
        return find_moments.run
    elif stage_name == "slice":
        from pipeline.stages import slice
        return slice.run
    elif stage_name == "analyze":
        from pipeline.stages import analyze
        return analyze.run
    elif stage_name == "upload":
        from pipeline.stages import upload
        return upload.run
    elif stage_name == "cleanup":
        from pipeline.stages import cleanup
        return cleanup.run
    raise ValueError(f"Unknown stage: {stage_name}")


def process_video(creator: str, video_id: str, start_stage: str = "transcribe"):
    """Run the pipeline for a single video, starting from the given stage."""
    start_idx = STAGES.index(start_stage)

    for stage_name in STAGES[start_idx:]:
        log.info("=== Stage: %s (video: %s) ===", stage_name, video_id)
        try:
            runner = _get_stage_runner(stage_name)
            runner(creator, video_id)

            log.info("=== Stage %s complete ===", stage_name)

        except Exception as e:
            log.error("Stage %s failed for %s: %s", stage_name, video_id, e)
            state.update_video_status(video_id, STAGE_STATUS.get(stage_name, "error"), error=str(e))
            raise


def show_status():
    """Print a summary of all tracked videos."""
    videos = state.get_all_videos()
    if not videos:
        print("No videos tracked yet.")
        return

    print(f"\n{'Video ID':<20} {'Creator':<20} {'Status':<15} {'Error'}")
    print("-" * 75)
    for v in videos:
        error = (v["error"] or "")[:30]
        print(f"{v['video_id']:<20} {v['creator_name']:<20} {v['status']:<15} {error}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Autonomous Shorts Pipeline")
    parser.add_argument("--creator", type=str, help="Process a specific creator")
    parser.add_argument("--url", type=str, help="Process a specific video URL")
    parser.add_argument("--stage", type=str, choices=STAGES, help="Resume from a specific stage")
    parser.add_argument("--status", action="store_true", help="Show status of all tracked videos")
    args = parser.parse_args()

    state.init_db()

    if args.status:
        show_status()
        return

    # Determine starting stage
    start_stage = args.stage or "download"

    if start_stage == "download":
        # Download stage
        log.info("=== Stage: download ===")
        downloaded = download.run(creator_name=args.creator, url=args.url)

        if not downloaded:
            log.info("No new videos to process.")
            return

        log.info("Downloaded %d video(s)", len(downloaded))

        # Process each downloaded video through remaining stages
        for d in downloaded:
            process_video(d["creator"], d["video_id"], start_stage="transcribe")
    else:
        # Resuming from a later stage — need creator + video_id
        if not args.creator:
            print("Error: --creator is required when using --stage", file=sys.stderr)
            sys.exit(1)

        if args.url:
            video_id = download._extract_video_id(args.url)
        else:
            # Find the latest video for this creator that needs processing
            videos = state.get_all_videos()
            creator_videos = [v for v in videos if v["creator_name"] == args.creator]
            if not creator_videos:
                print(f"No tracked videos for creator '{args.creator}'", file=sys.stderr)
                sys.exit(1)
            video_id = creator_videos[0]["video_id"]

        process_video(args.creator, video_id, start_stage=start_stage)

    log.info("Pipeline complete.")


if __name__ == "__main__":
    main()
