"""
Parses VTT subtitle files into clean plain-text transcripts.

YouTube auto-captions accumulate text word-by-word within each utterance,
producing many overlapping entries that look like duplicates. This parser
collapses those into clean, non-repeated sentences.

Output: one .txt file per episode in ./transcripts/
"""

import re
import os
import glob
import webvtt

SUBTITLES_DIR = "./subtitles"
OUT_DIR = "./transcripts"

os.makedirs(OUT_DIR, exist_ok=True)


def clean_line(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)   # remove HTML/timing tags
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def deduplicate(raw: list[str]) -> list[str]:
    """
    Collapse YouTube's word-accumulation captions.
    YouTube emits lines like:
      "Oye tío"  →  "Oye tío, esto"  →  "Oye tío, esto es bestial"
    We keep the longest version and skip extensions.
    """
    result: list[str] = []
    for text in raw:
        if not text:
            continue
        if not result:
            result.append(text)
            continue
        prev = result[-1]
        if text == prev:
            continue
        # New line extends previous (keep longer)
        if text.startswith(prev):
            result[-1] = text
            continue
        # Previous already contains this line (skip shorter)
        if prev.startswith(text):
            continue
        # Overlap at the seam: end of prev == start of new
        prev_words = prev.split()
        new_words  = text.split()
        overlap = 0
        for n in range(1, min(len(prev_words), len(new_words)) + 1):
            if prev_words[-n:] == new_words[:n]:
                overlap = n
        if overlap > 0:
            extension = new_words[overlap:]
            if extension:
                result[-1] = prev + " " + " ".join(extension)
            continue
        result.append(text)
    return result


def merge_fragments(lines: list[str]) -> list[str]:
    """Join short caption fragments into full sentences."""
    out: list[str] = []
    for line in lines:
        if (out
                and not out[-1].endswith((".", "?", "!", "…", "—", ":"))
                and len(line) < 80):
            out[-1] = out[-1] + " " + line
        else:
            out.append(line)
    return out


def vtt_to_text(vtt_path: str) -> str:
    raw = []
    for caption in webvtt.read(vtt_path):
        for part in caption.text.split("\n"):
            line = clean_line(part)
            if line:
                raw.append(line)

    deduped   = deduplicate(raw)
    sentences = merge_fragments(deduped)
    return "\n".join(sentences)


def process_all():
    # Find all VTTs, preserving subfolder structure (Podcast/Tertulias/Interviews)
    vtt_files = sorted(
        glob.glob(os.path.join(SUBTITLES_DIR, "*.vtt")) +
        glob.glob(os.path.join(SUBTITLES_DIR, "**", "*.vtt"))
    )
    if not vtt_files:
        print(f"No .vtt files found in {SUBTITLES_DIR}/")
        return

    print(f"Processing {len(vtt_files)} files...")
    for vtt_path in vtt_files:
        # Mirror the subfolder from subtitles/ into transcripts/
        rel      = os.path.relpath(vtt_path, SUBTITLES_DIR)        # e.g. Podcast/date_id_title.es.vtt
        subfolder = os.path.dirname(rel)                            # e.g. Podcast  (or "" for root)
        basename  = os.path.splitext(os.path.basename(vtt_path))[0]
        basename  = re.sub(r"\.es$", "", basename)

        out_dir  = os.path.join(OUT_DIR, subfolder) if subfolder else OUT_DIR
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, basename + ".txt")

        # Skip if already up to date
        if os.path.exists(out_path) and os.path.getmtime(out_path) >= os.path.getmtime(vtt_path):
            continue

        try:
            text = vtt_to_text(vtt_path)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            words = len(text.split())
            print(f"  OK  {rel[:70]}  ({words} words)")
        except Exception as e:
            print(f"  ERR {rel}: {e}")

    print(f"\nDone. Transcripts saved to {OUT_DIR}/")


if __name__ == "__main__":
    process_all()
