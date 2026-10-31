# Tools

## analyze_hashtags.py
Finds which hashtags and which hashtag sets go with better-performing YouTube Shorts.
Standalone - it does not change the main program, it only prints a report.

1. Export your videos from YouTube Studio to CSV (see `yt-studio-export.user.js`, a Tampermonkey script).
2. Run: `python tools/analyze_hashtags.py youtube-shorts-export-*.csv`
3. Read `analyza_vystup/report.md` and tune the numbers in `platforms.py` yourself.

Needs Python 3.9+, no extra packages. With fewer than ~15 videos the report is only a description of the sample, not proof.

Volitelně: `--labels stitky.csv` (sloupce `video_id;typ_obsahu;sada`) pro porovnání uvnitř jednoho typu obsahu.
