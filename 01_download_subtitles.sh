#!/bin/bash
# Downloads Spanish auto-generated subtitles from the Wild Project playlist.
# Output: .vtt files in ./subtitles/

PLAYLIST_URL="https://www.youtube.com/playlist?list=PLzuFY9Ixj9Z6nf7z6t5YmPDTLBgksk8Ts"
OUT_DIR="./subtitles"

mkdir -p "$OUT_DIR"

yt-dlp \
  --write-auto-sub \
  --sub-lang es \
  --skip-download \
  --output "$OUT_DIR/%(upload_date)s_%(id)s_%(title)s.%(ext)s" \
  --sleep-interval 2 \
  --max-sleep-interval 5 \
  "$PLAYLIST_URL"

echo ""
echo "Done. VTT files saved to $OUT_DIR/"
echo "Count: $(ls $OUT_DIR/*.vtt 2>/dev/null | wc -l) files"
