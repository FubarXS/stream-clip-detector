"""Entry point of the packaged .exe (PyInstaller). A normal start opens the window; "--worker <module> ..."
runs a helper module (clip_detector, analyze_finished, yt_dlp) instead - the window starts these as separate processes."""
import sys

if len(sys.argv) > 2 and sys.argv[1] == "--worker":
    import runpy
    module = sys.argv[2]
    sys.argv = [module + ".py"] + sys.argv[3:]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
else:
    import clip_gui
    clip_gui.main()
