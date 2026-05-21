"""
Shared GPU detection + DLL path setup for transcribe scripts.

On Windows, the NVIDIA CUDA libraries installed via pip (nvidia-cublas-cu12,
nvidia-cudnn-cu12, nvidia-cuda-nvrtc-cu12) live inside the venv site-packages
folder. CTranslate2 (used by faster-whisper) needs them on the DLL search
path. `os.add_dll_directory` isn't enough — we also need to prepend to PATH.

Call `pick_device()` to get back ('cuda'|'cpu', compute_type) with all setup
already done. Falls back to CPU on any failure.
"""

import os
import sys
from pathlib import Path


def _setup_nvidia_dll_path() -> bool:
    """Find NVIDIA pip-installed CUDA libs and add them to PATH. Returns True if any were found."""
    site = Path(sys.prefix) / "Lib" / "site-packages"
    if not site.exists():
        return False
    found = False
    for sub in ("nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin"):
        p = site / sub
        if p.exists():
            os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
            try:
                os.add_dll_directory(str(p))
            except (OSError, AttributeError):
                pass
            found = True
    return found


def pick_device():
    """
    Try GPU first, fall back to CPU silently. Returns (device, compute_type).

    - GPU available + libs OK → ('cuda', 'float16')
    - Otherwise → ('cpu', 'int8')
    """
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            _setup_nvidia_dll_path()
            # Probe: actually try to allocate on GPU. If it fails (missing
            # cuBLAS/cuDNN), fall back to CPU instead of crashing later.
            try:
                from faster_whisper import WhisperModel
                # Tiny probe with the smallest model
                probe = WhisperModel("tiny", device="cuda", compute_type="float16")
                del probe
                return "cuda", "float16"
            except Exception as e:
                print(f"[sentinela] GPU detected but failed to initialize ({e}); falling back to CPU.", file=sys.stderr)
                return "cpu", "int8"
    except ImportError:
        pass
    return "cpu", "int8"
