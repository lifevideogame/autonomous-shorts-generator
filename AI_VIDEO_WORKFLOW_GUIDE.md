# AI Agent Replication Report: Autonomous Viral Shorts Generation

## 1. Objective
To autonomously download a long-form YouTube video, identify a viral moment using multimodal analysis (audio/visual), and edit it into a high-quality (1080p), vertical (9:16) Short with facecam tracking and viral-style captions.

## 2. Environment Setup
**System Requirements:**
*   **OS:** Linux (Ubuntu 22.04+ recommended) or WSL2.
*   **Runtime:** Node.js v18+, Python 3.10+.
*   **Tools:** `ffmpeg` (with libx264), `yt-dlp`.

**Dependencies:**
```bash
# System Tools
sudo apt update && sudo apt install ffmpeg python3-venv

# Python Dependencies
python3 -m venv venv
source venv/bin/activate
pip install opencv-python-headless numpy yt-dlp

# Node.js / Remotion
npx create-remotion@latest remotion-short --template blank-typescript
cd remotion-short
npm install @remotion/google-fonts @remotion/captions
```

## 3. Workflow & Logic

### Phase 1: Acquisition & Proxy Generation
**Goal:** Obtain the source material efficiently.
1.  **Download 360p Proxy:** Download a low-resolution version for fast analysis.
    ```bash
    yt-dlp -f "bestvideo[height<=360]+bestaudio/best" "URL" -o "input_proxy.mp4"
    ```
2.  **Download Subtitles:** Fetch English captions for context analysis.
    ```bash
    yt-dlp --write-auto-subs --sub-langs en-orig --skip-download "URL" -o "subs"
    ffmpeg -i subs.en-orig.vtt subtitles.srt
    ```

### Phase 2: Multimodal Analysis
**Goal:** Identify the "Viral Moment" without human input.

1.  **Audio Peak Detection (The "Ears"):**
    *   **Logic:** Viral moments in gaming are often loud (screams, laughs).
    *   **Method:** Calculate RMS amplitude over sliding 30s windows.
    *   **Script:** `scripts/analyze_audio.py`
    *   **Result:** Found peak at **18:30**.

2.  **Visual Feature Extraction (The "Eyes"):**
    *   **Goal:** Locate the streamer's facecam for cropping.
    *   **Method:** Extract a frame from the peak moment and use OpenCV Haar Cascades.
    *   **Script:** `scripts/detect_facecam.py`
    *   **Command:** `python3 scripts/detect_facecam.py frame.jpg`
    *   **Result:** Face found at `x:1544, y:787` (in 1080p coordinates).

3.  **Semantic Verification (The "Brain"):**
    *   **Method:** Search `subtitles.srt` at the timestamp.
    *   **Found:** "Strut bro look at that!" (Context: NieR Automata 2B animations).
    *   **Verdict:** High viral potential.

### Phase 3: High-Quality Asset Prep
**Goal:** Prepare assets for the final render. **Do not use the proxy.**
1.  **Download HQ Clip:** Use `yt-dlp` to download *only* the 35s segment in 1080p.
    ```bash
    yt-dlp -f "bestvideo[height>=1080]+bestaudio" --external-downloader ffmpeg --external-downloader-args "ffmpeg_i:-ss 00:18:30 -t 35" "URL" -o "public/moment_1080p.mp4"
    ```
2.  **Transcode to Master:** Ensure accurate seeking for Remotion.
    ```bash
    ffmpeg -i public/moment_1080p.mp4 -c:v libx264 -crf 18 -c:a aac public/moment_final.mp4
    ```

### Phase 4: Procedural Editing (Remotion)
**Goal:** Programmatically edit the video.
*   **Resolution:** 1080x1920 (9:16 Vertical).
*   **Composition (`src/GamingShort.tsx`):**
    *   **Layer 1 (Gameplay):** Main video scaled `1.8x` and centered.
    *   **Layer 2 (Facecam):** Duplicate video layer, masked to a circle.
        *   *Math:* Calculated offsets to move `x:1544, y:787` to the center of a 650px container.
    *   **Layer 3 (Captions):** Parsed `subtitles.srt`, synced to frame time, styled with `Kanit` font and yellow/black high-contrast colors.
    *   **Layer 4 (Overlay):** "LIVE" and "REC" elements.

## 4. Execution
To replicate this video generation:

1.  **Clone the Repository:**
    ```bash
    git clone <YOUR_REPO_URL>
    cd remotion-short
    npm install
    ```
2.  **Place Assets:**
    *   Put your source clip in `public/moment_final.mp4`.
    *   Put your subtitles in `public/subtitles.srt`.
3.  **Configure (Optional):**
    *   Update `FACE_X`, `FACE_Y` in `src/GamingShort.tsx` if the facecam moves.
4.  **Render:**
    ```bash
    npx remotion render GamingShort out/viral_short.mp4
    ```

## 5. Code Structure
*   `src/GamingShort.tsx`: The core logic for layout, zoom, and animations.
*   `src/Root.tsx`: Composition registration.
*   `scripts/`: Python tools for analysis.
