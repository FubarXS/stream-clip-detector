# Project notes (for contributors and for AI assistants starting a new chat)

## What it is
Desktop app (Python 3, CustomTkinter) that finds clip-worthy moments in stream recordings and writes posts for them.
The window never does heavy work itself: it starts helper programs as separate processes and reads their output.

## File map (rule: every file stays under ~400 lines)
| File | Role |
|---|---|
| `clip_gui.py` | Main window: settings, language, clips list loading/saving |
| `gui_layout.py` | Window layout (Analysis tab, Clips tab switch, header, bar, footer) |
| `gui_clips.py` | Clips tab: cards, platform tabs, favorites, delete, copy buttons |
| `gui_runner.py` | Starts/stops the helper processes, shows progress and status |
| `gui_widgets.py` | Tooltip and form helpers (cards, sliders, options) |
| `gui_dialogs.py` | Small dialogs (game question) |
| `gui_config.py` | Defaults, option lists, reasons for defaults |
| `gui_strings.py` | Czech texts (English text is the key) |
| `brand.py` | ALL colors/styles (FubarXS brand: magma orange on black, no purple/blue) |
| `clip_detector.py` | The detection engine (loudness, speech, secret word, picking, cutting) |
| `keywords.py` | Default trigger words (kept tiny so the window does not import numpy) |
| `calibrate.py` | Loudness check ("Measure my loudness") |
| `llm_judge.py` | Optional AI step via Ollama (rating, texts, hashtags, platform adaptation) |
| `platforms.py` | Per-platform rules (hashtag counts, title length) and text building |
| `analyze_finished.py` | Analysis of already finished clips |
| `transcript_cache.py` | Saves/reuses the Whisper transcript per recording in `<out>/cache/` |
| `exports.py` | Thumbnails, `.srt`, `posts.txt`, `*_info.txt` per clip |
| `ollama_models.py` | Lists installed Ollama models and GPU memory |
| `make_icon.py`, `make_assets.py` | Generate `icons/` |

## Data flow
GUI -> subprocess `clip_detector.py` (or `analyze_finished.py`) -> prints progress lines (`@@...` = status line,
`@@MEASURE {json}` = loudness check result) -> writes `results.json` / `finished.json`, clips, `thumbs/`, `posts.txt`.
The Clips tab reads the JSON files; favorites and typed edits are written back into them.

## Conventions
- Deleting a clip in the Clips window also deletes its `_info.txt` (and the `.srt` of a finished clip).
- A second analysis of the same recording reuses the saved transcript (`--no-transcript-cache` forces a new one).
- Clips are cut with `-map 0:v:0 -map 0:a?` so every audio track of the recording (OBS multitrack) stays in the clip.
- Each clip gets `<clip name>_info.txt` (time, why, AI notes, title, description, hashtags, transcript). Finished clips: `<out>/finished/`.
  Edits in the Clips window are written back to it on close. Switches: `--no-info-files`, `--no-transcript-files` (speech is still analyzed).
- UI text is English in the code; Czech lives in `gui_strings.py` (lookup by the English text).
- Static widget texts are translated by walking the widget tree; texts built at runtime use `self.tr(...)`.
- Pillow is optional (nicer visuals); the app must work without it.
- Never write a file before the new content is computed (a failed read once emptied a file).

## Testing without a screen
Use `xvfb-run` on Linux for the window; a small fake Ollama HTTP server for the AI step; replace `clip_detector.transcribe`
with a function returning fake segments (Whisper models are not needed to test the flow).

## Known limits
- Each stream analysis rewrites `results.json` in its output folder (use a folder per stream).
- Hashtag recommendations are an AI estimate shaped by third-party guides; no live trend data.
- Not tested on macOS/Linux; the window is developed for Windows.
