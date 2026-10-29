# Project notes (for contributors and for AI assistants starting a new chat)

## What it is
Desktop app (Python 3, CustomTkinter) that finds clip-worthy moments in stream recordings and writes posts for them.
The window never does heavy work itself: it starts helper programs as separate processes and reads their output.

## File map (rule: every file stays under ~400 lines)
| File | Role |
|---|---|
| `clip_gui.py` | Main window: settings, language, clips list loading/saving |
| `gui_layout.py` | Window layout (Analysis tab, Clips tab switch, header, bar, footer) |
| `gui_gallery.py` | Gallery view of the Clips tab (compact cards, "Edit" opens the full card in a window) |
| `gui_player.py` | In-app clip player: ffmpeg pictures + ffplay sound, no extra Python packages |
| `app_main.py`, `stream_clip_detector.spec` | Entry point and PyInstaller recipe of the Windows app (`--worker <module>` = helper mode) |
| `install.bat`, `start.bat`, `create_shortcut.ps1` | Install packages + desktop shortcut with the icon, start the program |
| `.github/workflows/build-windows.yml` | Builds the Windows zip files when a `v*` tag is pushed |
| `gui_clips.py` | Clips tab: cards, platform tabs, favorites, delete, copy buttons |
| `gui_runner.py` | Starts/stops the helper processes, shows progress and status |
| `gui_widgets.py` | Tooltip, `FitButton` (never clips its text) and form helpers (cards, sliders, translated dropdowns) |
| `gui_icons.py` | Icons drawn with Pillow at run time (trash, edit, copy, list, gallery), `icon_button`, the list/gallery `ViewToggle` |
| `gui_source.py` | One-source rule (file OR Twitch link) and "save clips next to the recording" |
| `gui_dialogs.py` | Small dialogs (game question) |
| `gui_config.py` | Defaults, option lists, reasons for defaults |
| `gui_strings.py` | Czech texts (English text is the key) |
| `brand.py` | ALL colors/styles (FubarXS brand: magma orange on black, no purple/blue) |
| `clip_detector.py` | The detection engine (loudness, speech, secret word, picking, cutting) |
| `keywords.py` | Default trigger words (kept tiny so the window does not import numpy) |
| `calibrate.py` | Loudness check ("Measure my loudness") |
| `llm_judge.py` | Optional AI step via Ollama (rating, texts, hashtags, platform adaptation) |
| `llm_scan.py` | Optional: the AI reads the transcript in ~5 min pieces and names clip candidates that loudness and trigger words missed (`--ai-scan`) |
| `llm_parse.py` | Tolerant reading of the AI reply (JSON in a fence, "8/10", hashtags as one string, cut-off answers) |
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
- Helper processes are started with `gui_config.worker_cmd(module, ...)` (works from source and inside the packaged .exe).
- Clips tab: the list can come from `results.json`, `finished.json` and from scanning the folder for `clip_*` / `marker_*` files
  (`exports.scan_folder`, texts from `*_info.txt`; favorites are stored in the info file as `Favorite: yes`).
- Clip container is chosen with `--format mp4|mov|mkv`; `exports.cut` falls back to AAC audio when the container refuses the codec.
- Deleting a clip in the Clips window also deletes its `_info.txt` (and the `.srt` of a finished clip).
- A second analysis of the same recording reuses the saved transcript (`--no-transcript-cache` forces a new one).
- Clips are cut with `-map 0:v:0 -map 0:a?` so every audio track of the recording (OBS multitrack) stays in the clip.
- Each clip gets `<clip name>_info.txt` (time, why, AI notes, title, description, hashtags, transcript). Finished clips: `<out>/finished/`.
  Edits in the Clips window are written back to it on close. Switches: `--no-info-files`, `--no-transcript-files` (speech is still analyzed).
- UI text is English in the code; Czech lives in `gui_strings.py` (lookup by the English text).
- Static widget texts are translated by walking the widget tree; texts built at runtime use `self.tr(...)`.
- Pillow is optional (nicer visuals); the app must work without it (icon buttons then show a short translated word).
- Use `FitButton` instead of `ctk.CTkButton` for buttons with text: its `width` is only a minimum, so longer Czech words never get cut off.
  Small fixed-size buttons (the corner cross, the star) stay `ctk.CTkButton`.
- Dropdowns (`Blocks.option`) keep the ENGLISH key in their variable (the program looks it up) and show it translated; new option
  texts need a Czech entry in `gui_strings.py`.
- Source rules: only one of "Recording" / "Twitch link" can be filled (the other field is locked). "Save clips next to the recording"
  writes into `<video folder>/<video name>_clips`; `settings.json` keeps the user's own folder (`out`) plus `out_beside`.
- Never write a file before the new content is computed (a failed read once emptied a file).
- Settings (`gui_settings.json`), `run_config.json` and `crash_log.txt` live in `DATA` (`gui_config.py`): `%APPDATA%\StreamClipDetector`
  in the packaged app, next to the code when run from source. Every release unpacks into a NEW folder, so settings next to the
  .exe started from the defaults each time (the AI switch is off by default -> clips without titles and hashtags). Versions up to
  0.5.1 kept them next to the .exe; the first start copies that file over once.
- AI scan (`--ai-scan`, off by default): finds candidates only. They join the normal ones and get the same detailed rating, so
  the AI never decides alone what is kept. It adds at most `--top` candidates, none closer than one clip length to another,
  and drops times that are not in the piece it was shown (invented). The reason is added to a clip's `why` only AFTER judging,
  so the judge is not told "the AI picked this". Costs about one model call per 5 minutes of speech (3 h stream = ~40 calls).
  Not cached yet: running the analysis again repeats the scan.
- The AI texts are optional: with the switch off the log says so and gallery cards say "AI was off or failed" instead of an empty title.
- Icons: `make_icon.py` makes two glyphs - the detailed clapperboard (>= 64 px) and a fat one with 4 stripes for 16-48 px - and writes
  `app.ico` with one hand-made picture per size (16, 20, 24, 32, 40, 48, 64, 128, 256; Windows asks for 20/24/40 at 125/150/250 %).
  Small sizes are shrunk with HAMMING, not LANCZOS (LANCZOS puts a bright ring next to hard edges). `brand.window_icon` passes
  all PNG sizes to Tk. The list/gallery icons in `gui_icons.py` are laid out in 4/3 units = 1 px at 18 px, so they are crisp at 100 %.

## Testing without a screen
Use `xvfb-run` on Linux for the window; a small fake Ollama HTTP server for the AI step; replace `clip_detector.transcribe`
with a function returning fake segments (Whisper models are not needed to test the flow).

## Known limits
- The packaged Windows app is built by GitHub Actions and was only tested on Linux (build, helper mode, window start); the sound
  of the in-app player needs ffplay (bundled in the Windows zip; for a source install it comes with the ffmpeg download).
- Each stream analysis rewrites `results.json` in its output folder (use a folder per stream).
- Hashtag recommendations are an AI estimate shaped by third-party guides; no live trend data.
- Not tested on macOS/Linux; the window is developed for Windows.
