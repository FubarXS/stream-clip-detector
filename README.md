# Stream Clip Detector

A free tool for Windows that finds the best moments in your stream recordings and helps you post them.
It does **not** depend on chat: it listens to loudness and to what you say. Everything runs on your own PC.

## What it does
- **Finds moments** from loudness spikes, trigger words you choose, and an optional secret phrase you say after a great moment.
- **Cuts clips** (ffmpeg) with a preview image, and explains why each clip was picked.
- **Speech to text** with [faster-whisper](https://github.com/SYSTRAN/faster-whisper): full transcript with timestamps and `.srt` subtitles.
- **Optional AI helper** (free, local, via [Ollama](https://ollama.com)): rates how funny a clip is, writes a title and caption, and suggests hashtags and meme ideas for TikTok, YouTube Shorts and Instagram Reels. Optionally it also reads the whole transcript to find funny moments that were not loud and had no trigger words.
- **Finished clips**: add a clip you already edited (for example exported from DaVinci Resolve) and get the same texts for it.
- Saves an `_info.txt` next to every clip (title, hashtags, transcript); transcript files can be switched off. All audio tracks of an OBS recording are kept in the clips.
- **Clips tab**: list or gallery view, play a clip right in the app (small player, no extra install), mark favorites, edit the texts
  and copy them, load the clips of any folder (they come back with their `_info.txt` texts). Czech and English interface.
- Clip format: MP4, MOV (DaVinci Resolve with several audio tracks) or MKV.

## Install (Windows)
1. Install [Python 3.10 or newer](https://www.python.org/downloads/) - tick **Add python.exe to PATH**.
2. Install ffmpeg: open PowerShell and run `winget install Gyan.FFmpeg`, then open a new PowerShell window.
3. Double-click `install.bat` (installs the Python packages).
4. Start the program with the **Stream Clip Detector** icon that `install.bat` puts on your desktop (or double-click `start.bat`).

**No Python?** Download the zip for Windows from the [Releases](../../releases) page (`...-cpu.zip`, or `...-gpu.zip` for NVIDIA
graphics cards - much larger), unzip it and start `StreamClipDetector.exe`. ffmpeg is included.

Optional: install [Ollama](https://ollama.com) and run `ollama pull <model>` for the AI helper. NVIDIA graphics cards make the
speech recognition much faster (see `requirements.txt`); without one, choose **CPU** in the program.

### Windows says "Windows protected your PC" (SmartScreen)

The downloaded `StreamClipDetector.exe` is not digitally signed (a code-signing certificate costs thousands per year, and this
tool is meant to stay free), so Windows SmartScreen warns about an unknown publisher. The program does nothing hidden - the
whole source code is in this repository and nothing is uploaded anywhere. To start it:

1. Click **More info**, then **Run anyway**.
2. To avoid the question for good: right-click the downloaded `.zip` -> **Properties** -> tick **Unblock** -> OK, and only
   then extract it. (Already extracted? In PowerShell: `Get-ChildItem -Recurse "C:\path\to\StreamClipDetector" | Unblock-File`.)
   Do this again for every new version, because each download is a new file for Windows.

Prefer not to run an exe at all? Use the Python install above - it has no warning, and you can read every line you run.

## Tips
- Analyze your **local OBS recording** if you can: better quality than a Twitch VOD, and if your microphone is on its own audio track
  you can pick that track (**Audio track for analysis**) so the game sound does not count as your reaction.
- Run the analysis when you are not streaming or gaming - it uses the GPU.
- Hashtag counts per platform: the YouTube limit (60) and the Instagram limit (5) are from the official platform pages; the TikTok count is from third-party guides and not verified. You can change them in `platforms.py`.

## Good to know
- Only analyze and download content you have the rights to. Respect the Terms of Service of the platforms.
- Not affiliated with Twitch, TikTok, YouTube, Instagram, DaVinci Resolve or Ollama.
- No analytics, no accounts. Nothing is uploaded anywhere by this program.

## Support
Free to use. If it saves you money compared with paid tools, you can support the author on [Ko-fi](https://ko-fi.com/fubarxs).
Code contributions are just as welcome - see [CONTRIBUTING.md](CONTRIBUTING.md).

## License
MIT - see [LICENSE](LICENSE).
