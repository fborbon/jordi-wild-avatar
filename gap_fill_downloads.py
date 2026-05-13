"""
Downloads subtitle files that are missing from our local collection.
Compares playlist IDs against what we already have and fetches only the gaps.

Usage:
  python3 gap_fill_downloads.py                  # fills all gaps
  python3 gap_fill_downloads.py --dry-run        # shows what would be downloaded
  python3 gap_fill_downloads.py --playlist URL   # check against a specific playlist
"""

import os, subprocess, argparse, re

PLAYLISTS = {
    "Podcast":   "https://www.youtube.com/playlist?list=PLzuFY9Ixj9Z6nf7z6t5YmPDTLBgksk8Ts",
    "Tertulias": "https://www.youtube.com/playlist?list=PLzuFY9Ixj9Z6DGzF9p26nCbENb13-1Kg5",
}
SUBTITLES_DIR = "./subtitles"


def get_playlist_ids(url: str) -> set[str]:
    r = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "id", "--no-warnings", url],
        capture_output=True, text=True
    )
    return {l.strip() for l in r.stdout.splitlines() if l.strip()}


def get_local_ids() -> set[str]:
    ids = set()
    for root, _, files in os.walk(SUBTITLES_DIR):
        for f in files:
            if f.endswith(".vtt"):
                parts = f.split("_", 2)
                if len(parts) >= 2:
                    ids.add(parts[1])
    return ids


def download_missing(missing_ids: set[str], category: str, dry_run: bool):
    out_dir = os.path.join(SUBTITLES_DIR, category)
    os.makedirs(out_dir, exist_ok=True)

    ids = sorted(missing_ids)
    print(f"\n{category}: {len(ids)} missing episodes to download")

    for i, vid_id in enumerate(ids, 1):
        url = f"https://www.youtube.com/watch?v={vid_id}"
        print(f"  [{i:3d}/{len(ids)}] {vid_id}", end="", flush=True)
        if dry_run:
            print(" (dry-run)")
            continue

        result = subprocess.run([
            "yt-dlp",
            "--write-auto-sub", "--sub-lang", "es",
            "--skip-download",
            "--output", os.path.join(out_dir, "%(upload_date)s_%(id)s_%(title)s.%(ext)s"),
            "--no-warnings", "--ignore-errors",
            "--sleep-interval", "2",
            url,
        ], capture_output=True, text=True)

        if "Writing video subtitles" in result.stderr or "Writing video subtitles" in result.stdout:
            print(" ✓")
        elif "no subtitles" in result.stderr.lower() or result.returncode != 0:
            print(" — no subtitles")
        else:
            print(" ✓")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--playlist", default=None, help="Check single playlist URL")
    args = parser.parse_args()

    local_ids = get_local_ids()
    print(f"Local subtitle files: {len(local_ids)}")

    targets = {}
    if args.playlist:
        targets["Custom"] = args.playlist
    else:
        targets = PLAYLISTS

    total_missing = 0
    for category, url in targets.items():
        print(f"\nFetching {category} playlist IDs...")
        playlist_ids = get_playlist_ids(url)
        missing = playlist_ids - local_ids
        total_missing += len(missing)
        print(f"  Playlist: {len(playlist_ids)}  Local: {len(playlist_ids) - len(missing)}  Missing: {len(missing)}")
        if missing:
            download_missing(missing, category, dry_run=args.dry_run)

    print(f"\nTotal missing: {total_missing}")
    if args.dry_run:
        print("(dry-run — nothing downloaded)")


if __name__ == "__main__":
    main()
