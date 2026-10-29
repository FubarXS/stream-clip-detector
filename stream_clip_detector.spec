# PyInstaller recipe for the Windows app (a folder with StreamClipDetector.exe).
# Build:  py -m pip install pyinstaller   then   py -m PyInstaller stream_clip_detector.spec --noconfirm
# Set the environment variable INCLUDE_CUDA=1 (and pip install nvidia-cublas-cu12 nvidia-cudnn-cu12) for the GPU variant.
import os
from PyInstaller.utils.hooks import collect_all

datas, binaries = [("icons", "icons")], []
hidden = ["clip_detector", "analyze_finished", "calibrate", "llm_judge", "platforms", "transcript_cache",
          "keywords", "exports", "gui_player", "gui_gallery", "llm_parse", "llm_scan"]  # started by name in "--worker" mode, so not found by import scanning
packages = ["faster_whisper", "ctranslate2", "customtkinter", "onnxruntime", "av", "tokenizers", "yt_dlp"]
if os.environ.get("INCLUDE_CUDA") == "1":
    packages += ["nvidia.cublas", "nvidia.cudnn"]  # clip_detector._add_cuda_dlls() finds nvidia/*/bin next to the program
for pkg in packages:  # data files and libraries these packages load at run time
    d, b, h = collect_all(pkg)
    datas, binaries, hidden = datas + d, binaries + b, hidden + h

a = Analysis(["app_main.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hidden,
             excludes=["matplotlib", "scipy", "pandas", "torch", "IPython", "pytest"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="StreamClipDetector", console=False, icon="icons/app.ico")
coll = COLLECT(exe, a.binaries, a.datas, name="StreamClipDetector")
