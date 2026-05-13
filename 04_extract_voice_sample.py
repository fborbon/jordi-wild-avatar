"""
Downloads audio from a Wild Project episode and extracts a clean voice sample
of Jordi speaking (skipping intros, music, etc.).
Output: data/jordi_voice_sample.wav  (30 seconds, 22050 Hz mono)

Usage:
  python3 04_extract_voice_sample.py
  python3 04_extract_voice_sample.py --url "https://www.youtube.com/watch?v=XYZ"
"""

import os
import subprocess
import argparse

# A recent episode where Jordi speaks clearly from the start
DEFAULT_URL = "https://www.youtube.com/watch?v=As1CSUuqq1k"

OUT_DIR = "data"
RAW_AUDIO = os.path.join(OUT_DIR, "jordi_raw.mp3")
SAMPLE_WAV = os.path.join(OUT_DIR, "jordi_voice_sample.wav")

# Skip first N seconds (intros/music), then take DURATION seconds
SKIP_SECONDS = 180     # skip first 3 min (sponsor/intro)
DURATION_SECONDS = 45  # 45s is more than enough for XTTS voice cloning


def run(cmd: list[str], desc: str):
    print(f"  {desc}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-300:]}")
        raise RuntimeError(f"Command failed: {' '.join(cmd[:3])}")


def main(url: str):
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Downloading audio from:\n  {url}\n")

    run([
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--output", RAW_AUDIO,
        "--force-overwrites",
        url,
    ], "Downloading audio")

    print(f"  Extracting {DURATION_SECONDS}s starting at {SKIP_SECONDS}s...")
    result = subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(SKIP_SECONDS),
        "-i", RAW_AUDIO,
        "-t", str(DURATION_SECONDS),
        "-ar", "22050",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        SAMPLE_WAV,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr[-300:]}")
        raise RuntimeError("ffmpeg failed")

    size_kb = os.path.getsize(SAMPLE_WAV) // 1024
    print(f"\nVoice sample saved: {SAMPLE_WAV}  ({size_kb} KB)")
    print("Ready for voice cloning.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL, help="YouTube URL of episode to sample")
    args = parser.parse_args()
    main(args.url)
