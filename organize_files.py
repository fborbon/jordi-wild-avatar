"""
Organizes subtitle and transcript files into subfolders:
  Podcast/     — main interview episodes (TWP #1–#373)
  Tertulias/   — discussion/roundtable episodes
  Interviews/  — external interviews where Jordi is the guest

Strategy:
  1. Fetch video IDs from the Tertulias playlist (yt-dlp, no download)
  2. Hardcode the two external interview IDs
  3. Everything else → Podcast
  4. Move .vtt and .txt files into matching subfolders
  5. Update paths in 06_build_knowledge_base.py

Usage:
  python3 organize_files.py
"""

import os, re, subprocess, shutil, json

SUBTITLES_DIR  = "./subtitles"
TRANSCRIPTS_DIR = "./transcripts"

TERTULIAS_PLAYLIST = "https://www.youtube.com/playlist?list=PLzuFY9Ixj9Z6DGzF9p26nCbENb13-1Kg5"

# External interviews where Jordi is the interviewee
INTERVIEW_IDS = {"x200msN-QT8", "2wY9bJOW9n8"}


def get_playlist_ids(url: str) -> set[str]:
    """Get all video IDs from a playlist without downloading anything."""
    print(f"  Fetching playlist IDs from:\n  {url}")
    result = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "id", "--no-warnings", url],
        capture_output=True, text=True
    )
    ids = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    print(f"  → {len(ids)} IDs retrieved")
    return ids


def extract_video_id(filename: str) -> str | None:
    """
    Extract YouTube video ID from filenames like:
      20220222_HRuY_3ZbJ7k_Title.es.vtt   → HRuY_3ZbJ7k  (but we only need first segment)
      20211019__SBGvOCAtwU_Title.es.vtt    → _SBGvOCAtwU  (ID starts with _)
    YouTube IDs are 11 chars: [A-Za-z0-9_-]
    """
    # Strip date prefix (8 digits + underscore)
    rest = re.sub(r"^\d{8}_", "", filename)
    # Extract up to the next underscore-separated boundary that forms a valid ID
    # IDs are 11 alphanumeric + _- chars
    m = re.match(r"^([A-Za-z0-9_\-]{10,12})_", rest)
    if m:
        return m.group(1)
    return None


def categorize(video_id: str, tertulia_ids: set[str]) -> str:
    if video_id in INTERVIEW_IDS:
        return "Interviews"
    if video_id in tertulia_ids:
        return "Tertulias"
    return "Podcast"


def organize_dir(base_dir: str, tertulia_ids: set[str], ext: str):
    for cat in ("Podcast", "Tertulias", "Interviews"):
        os.makedirs(os.path.join(base_dir, cat), exist_ok=True)

    files = [f for f in os.listdir(base_dir) if f.endswith(ext)]
    counts = {"Podcast": 0, "Tertulias": 0, "Interviews": 0, "skipped": 0}

    for fname in files:
        vid_id = extract_video_id(fname)
        if not vid_id:
            counts["skipped"] += 1
            continue
        cat = categorize(vid_id, tertulia_ids)
        src = os.path.join(base_dir, fname)
        dst = os.path.join(base_dir, cat, fname)
        shutil.move(src, dst)
        counts[cat] += 1

    return counts


def main():
    print("Step 1/3  Fetching Tertulias playlist IDs...")
    tertulia_ids = get_playlist_ids(TERTULIAS_PLAYLIST)

    print("\nStep 2/3  Organizing subtitles/")
    s_counts = organize_dir(SUBTITLES_DIR, tertulia_ids, ".vtt")
    print(f"  Podcast: {s_counts['Podcast']}  "
          f"Tertulias: {s_counts['Tertulias']}  "
          f"Interviews: {s_counts['Interviews']}  "
          f"Skipped: {s_counts['skipped']}")

    print("\nStep 3/3  Organizing transcripts/")
    t_counts = organize_dir(TRANSCRIPTS_DIR, tertulia_ids, ".txt")
    print(f"  Podcast: {t_counts['Podcast']}  "
          f"Tertulias: {t_counts['Tertulias']}  "
          f"Interviews: {t_counts['Interviews']}  "
          f"Skipped: {t_counts['skipped']}")

    print("\nDone. Updated structure:")
    for base in (SUBTITLES_DIR, TRANSCRIPTS_DIR):
        for cat in ("Podcast", "Tertulias", "Interviews"):
            n = len(os.listdir(os.path.join(base, cat)))
            if n:
                print(f"  {base}/{cat}/  ({n} files)")


if __name__ == "__main__":
    main()
