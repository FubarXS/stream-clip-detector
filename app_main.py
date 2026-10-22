"""Entry point of the packaged .exe (PyInstaller). A normal start opens the window; "--worker <module> ..."
runs a helper module (clip_detector, analyze_finished, yt_dlp) instead - the window starts these as separate processes."""
import sys

if sys.platform == "win32":
    # The packaged app has no console window, so every program it starts (ffmpeg, ffprobe, ...) would open and
    # close a console window of its own. This keeps them all hidden.
    import subprocess
    _popen_init = subprocess.Popen.__init__

    def _hidden(self, *args, **kwargs):
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | 0x08000000  # CREATE_NO_WINDOW
        _popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _hidden

if len(sys.argv) > 2 and sys.argv[1] == "--worker":
    import runpy
    import traceback
    for stream in (sys.stdout, sys.stderr):  # PyInstaller ignores PYTHONIOENCODING, but the window reads UTF-8
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    module = sys.argv[2]
    sys.argv = [module + ".py"] + sys.argv[3:]
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit:
        raise
    except BaseException:  # the error goes to the log in the window instead of an "Unhandled exception" box
        traceback.print_exc()
        sys.exit(1)
else:
    import clip_gui
    clip_gui.main()
