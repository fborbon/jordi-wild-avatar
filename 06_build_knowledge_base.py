"""
Builds the Jordi Wild knowledge base for RAG (Retrieval-Augmented Generation).

Sources ingested:
  - All Jordi lines extracted by 03_extract_style.py
  - All transcript files (for re-extraction with more episodes)
  - Wikipedia article about his book
  - data/extra_context.txt  (manual additions, optional)

Output:
  data/jordi_lines.txt          — all extracted Jordi lines (appended)
  data/knowledge_base.pkl       — TF-IDF index for fast retrieval
  data/jordi_style_profile.json — refreshed style profile

Usage:
  python3 06_build_knowledge_base.py
  python3 06_build_knowledge_base.py --skip-extract   # skip LLM extraction, just index
"""

import os, re, json, random, pickle, argparse, urllib.request
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

TRANSCRIPTS_DIR  = "./transcripts"
DATA_DIR         = "./data"
LINES_FILE       = os.path.join(DATA_DIR, "jordi_lines.txt")
KB_FILE          = os.path.join(DATA_DIR, "knowledge_base.pkl")
PROFILE_FILE     = os.path.join(DATA_DIR, "jordi_style_profile.json")
WIKI_FILE        = os.path.join(DATA_DIR, "book_summary.txt")
SAMPLE_SIZE      = 9999  # process all episodes (heuristic is free/instant)
CHUNK_CHARS      = 6000

os.makedirs(DATA_DIR, exist_ok=True)

WIKI_URL = "https://es.wikipedia.org/wiki/As%C3%AD_es_la_puta_vida"

# Heuristic diarization — no API calls needed
# Jordi's lines are identifiable by: questions, short reactions, known phrases
JORDI_REACTIONS = {
    "ajá", "guau", "claro", "exacto", "sí sí", "ya", "vale", "ostia", "tío",
    "my god", "la madre", "me cago", "jolín", "coño", "hostia", "buff",
    "qué bestia", "qué fuerte", "no me digas", "en serio", "es que",
    "o sea", "es decir", "básicamente", "literalmente", "exactamente",
    "flipante", "increíble", "alucinante", "barbaridad",
}
JORDI_QUESTION_STARTS = (
    "¿", "y tú", "y qué", "cómo", "cuándo", "cuánto", "cuál", "quién",
    "por qué", "para qué", "qué crees", "qué opinas", "qué piensas",
    "qué te parece", "qué pasó", "qué fue", "háblame", "cuéntame",
    "pero ", "entonces ", "o sea ",
)

def fetch_wikipedia():
    if os.path.exists(WIKI_FILE):
        print("  Wikipedia already cached.")
        return
    print("  Fetching Wikipedia article...")
    req = urllib.request.Request(
        WIKI_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JordiAvatarBot/1.0)"}
    )
    with urllib.request.urlopen(req) as r:
        html = r.read().decode("utf-8")
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Keep only the meaty part (first 8000 chars after cleaning)
    text = text[:8000]
    with open(WIKI_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Saved Wikipedia summary ({len(text)} chars)")


def chunk_text(text, size):
    return [text[i:i+size] for i in range(0, len(text), size)]


def is_jordi_line(line: str) -> bool:
    """
    Heuristic: a line is likely Jordi's if it:
    - Is a question (ends in ? or starts with ¿)
    - Is a short reaction / interjection
    - Starts with a known interviewer opener
    - Is short enough to be a reaction (< 15 words) and contains a reaction word
    """
    low = line.lower().strip()
    words = low.split()

    # Questions are almost always the interviewer
    if line.strip().endswith("?") or line.strip().startswith("¿"):
        return True

    # Known reaction words in short lines
    if len(words) <= 10:
        for r in JORDI_REACTIONS:
            if r in low:
                return True

    # Typical interviewer openers
    if low.startswith(JORDI_QUESTION_STARTS):
        return True

    # Very short lines (1-4 words) are usually host reactions
    if len(words) <= 4:
        return True

    return False


def extract_jordi_lines(transcript: str) -> list[str]:
    """Extract likely Jordi lines using heuristics — no API calls."""
    sentences = [s.strip() for s in transcript.split("\n") if s.strip()]
    return [s for s in sentences if is_jordi_line(s)]


def build_kb(lines, extra_sources=None):
    """Build TF-IDF knowledge base from lines."""
    entries = [{"text": l, "source": "podcast"} for l in lines if l.strip()]
    if extra_sources:
        entries.extend(extra_sources)

    texts = [e["text"] for e in entries]
    print(f"  Indexing {len(texts)} entries...")
    vec = TfidfVectorizer(
        max_features=20000,
        ngram_range=(1, 2),
        min_df=1,
        strip_accents="unicode",
    )
    matrix = vec.fit_transform(texts)
    kb = {"vectorizer": vec, "matrix": matrix, "entries": entries}
    with open(KB_FILE, "wb") as f:
        pickle.dump(kb, f)
    print(f"  Knowledge base saved to {KB_FILE}")
    return kb


def main(skip_extract=False):
    import glob

    # 1. Fetch Wikipedia
    print("1/4  Fetching Wikipedia book summary...")
    fetch_wikipedia()

    # 2. Extract Jordi lines from new transcripts
    txt_files = sorted(
        glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.txt")) +
        glob.glob(os.path.join(TRANSCRIPTS_DIR, "**", "*.txt"))
    )
    print(f"\n2/4  Found {len(txt_files)} transcript files.")

    existing_lines = []
    if os.path.exists(LINES_FILE):
        with open(LINES_FILE, encoding="utf-8") as f:
            existing_lines = [l.strip() for l in f if l.strip()]
        print(f"     {len(existing_lines)} existing Jordi lines loaded.")

    if not skip_extract:
        sample = random.sample(txt_files, min(SAMPLE_SIZE, len(txt_files)))
        print(f"     Extracting from {len(sample)} new episodes (Claude API)...")
        new_lines = []
        for path in sample:
            name = os.path.basename(path)[:70]
            print(f"     → {name}")
            with open(path, encoding="utf-8") as f:
                text = f.read()
            ep_lines = extract_jordi_lines(text)
            new_lines.extend(ep_lines)
            print(f"       {len(ep_lines)} turns")
            # Save incrementally after each episode
            combined = list(dict.fromkeys(existing_lines + new_lines))
            with open(LINES_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(combined))

        all_lines = list(dict.fromkeys(existing_lines + new_lines))
        print(f"     Total Jordi lines: {len(all_lines)}")
    else:
        all_lines = existing_lines
        print("     Skipping extraction (--skip-extract).")

    # 3. Style profile is built separately by 03_extract_style.py (requires Claude API)
    print(f"\n3/4  Style profile: run 03_extract_style.py separately if needed.")

    # 4. Build knowledge base
    print("\n4/4  Building knowledge base...")
    extra = []
    if os.path.exists(WIKI_FILE):
        with open(WIKI_FILE, encoding="utf-8") as f:
            wiki_text = f.read()
        # Split into chunks for indexing
        for i in range(0, len(wiki_text), 500):
            chunk = wiki_text[i:i+500].strip()
            if chunk:
                extra.append({"text": chunk, "source": "libro_asi_es_la_puta_vida"})
    build_kb(all_lines, extra_sources=extra)
    print("\nKnowledge base ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-extract", action="store_true")
    args = parser.parse_args()
    main(skip_extract=args.skip_extract)
