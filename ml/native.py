"""Call the actual firmware DSP and feature code, rather than a Python imitation."""
import ctypes as ct
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
F32 = np.ctypeslib.ndpointer(dtype=np.float32, flags="C_CONTIGUOUS")


def library():
    path = ROOT / "build/libmounam.so"
    if not path.is_file():
        raise RuntimeError("Run 'make' from mounam-edge first (Linux/WSL, g++ required).")
    lib = ct.CDLL(str(path))
    lib.mounam_create.restype = ct.c_void_p
    lib.mounam_destroy.argtypes = [ct.c_void_p]
    lib.mounam_configure.argtypes = [ct.c_void_p, ct.c_uint, ct.c_uint, ct.c_float, ct.c_uint, ct.c_uint]
    lib.mounam_process.argtypes = [ct.c_void_p, F32, F32, ct.c_size_t]
    lib.mounam_features_create.restype = ct.c_void_p
    lib.mounam_features_destroy.argtypes = [ct.c_void_p]
    lib.mounam_extract.argtypes = [ct.c_void_p, F32, F32, ct.c_size_t]
    lib.mounam_predict.argtypes = [F32]
    lib.mounam_predict.restype = ct.c_float
    lib.mounam_model_provenance.restype = ct.c_char_p
    lib.mounam_model_id.restype = ct.c_char_p
    return lib


def stereo_array(stereo):
    audio = np.asarray(stereo, dtype=np.float32)
    if audio.ndim != 2 or audio.shape[1] != 2 or len(audio) == 0:
        raise ValueError("Expected non-empty [frames, 2] primary/reference audio.")
    if not np.isfinite(audio).all():
        raise ValueError("Audio contains NaN or infinity.")
    if np.max(np.abs(audio)) > 1:
        raise ValueError("Audio exceeds normalized full scale.")
    padding = (-len(audio)) % 32
    return np.ascontiguousarray(np.pad(audio, ((0, padding), (0, 0)))), len(audio)


def extract(stereo):
    audio, _ = stereo_array(stereo)
    result = np.empty((len(audio)//32, 8), dtype=np.float32)
    lib = library()
    handle = lib.mounam_features_create()
    if not handle:
        raise MemoryError("Unable to allocate features.")
    try:
        lib.mounam_extract(handle, audio, result, len(audio))
    finally:
        lib.mounam_features_destroy(handle)
    return result


def enhance(stereo, mode="hybrid", gain=0.05, hold=False, delay=0):
    if mode not in ("primary", "reference", "dsp", "hybrid"):
        raise ValueError("Unknown processing mode.")
    if not np.isfinite(gain) or not 0 <= gain <= 1 or not 0 <= delay <= 64:
        raise ValueError("Gain must be 0..1, delay must be 0..64 samples.")
    audio, original = stereo_array(stereo)
    result = np.empty(len(audio), dtype=np.float32)
    lib = library()
    handle = lib.mounam_create()
    if not handle:
        raise MemoryError("Unable to allocate DSP.")
    try:
        lib.mounam_configure(handle, ("primary", "reference", "dsp", "hybrid").index(mode), 0, gain, int(hold), delay)
        lib.mounam_process(handle, audio, result, len(audio))
    finally:
        lib.mounam_destroy(handle)
    return result[:original]
