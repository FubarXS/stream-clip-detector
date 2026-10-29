# Contributing

Thanks for helping! This is a small free tool.

1. Fork the repository and create a branch.
2. Keep every file under about 400 lines; if a file grows, split it by responsibility (see `PROJECT_NOTES.md`).
3. Colors and widget styles live only in `brand.py`.
4. Test your change (a short recording and `--no-whisper` is a quick way to try the detection).
5. Open a pull request that explains what changed and why.
6. Maintainers write the release commit message in the changelog style described in `PROJECT_NOTES.md` (section "Changelog / commit messages").

Ideas: chat activity as another signal (there is a plug-in point, `EXTRA_SIGNALS`), facecam emotion detection, game events (OCR),
automatic upload helpers, more interface languages, Linux/macOS testing.
