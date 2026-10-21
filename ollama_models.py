"""Models installed in Ollama (names and sizes) and the GPU memory, to help picking the AI model."""
import json
import subprocess
import urllib.request


def installed(url="http://localhost:11434/api/tags", timeout=2):
    """[(name, size in GB)] of the installed models, or None when Ollama is not running."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return sorted((m["name"], m.get("size", 0) / 1e9) for m in json.load(r).get("models", []))
    except Exception:
        return None


def gpu_gb():
    """Total memory of the biggest NVIDIA GPU in GB, or None."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return max(float(x) for x in out.split()) / 1024
    except Exception:
        return None
