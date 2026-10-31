import math
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

RATE = 16000


def read_wav(path, channel=None):
    rate, data = wavfile.read(path)
    if data.dtype == np.int16:
        audio = data.astype(np.float64) / 32768
    elif data.dtype == np.int32:
        audio = data.astype(np.float64) / 2147483648
    elif data.dtype == np.uint8:
        audio = (data.astype(np.float64) - 128) / 128
    elif np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float64)
    else:
        raise ValueError(f"Unsupported WAV format: {data.dtype}")
    if channel is not None:
        if audio.ndim == 1 and channel != 0:
            raise ValueError("Mono input has only channel 0.")
        if audio.ndim > 1:
            if channel < 0 or channel >= audio.shape[1]:
                raise ValueError("Requested channel does not exist.")
            audio = audio[:, channel]
    if not len(audio) or not np.isfinite(audio).all() or np.max(np.abs(audio)) > 1.0001:
        raise ValueError("Empty, non-finite or out-of-range audio.")
    if rate != RATE:
        divisor = math.gcd(rate, RATE)
        audio = resample_poly(audio, RATE//divisor, rate//divisor, axis=0)
    # Resampling can overshoot. Reject rather than quietly clipping training inputs.
    if np.max(np.abs(audio)) > 1:
        raise ValueError("Resampling exceeded full scale; reduce source level before conversion.")
    return audio.astype(np.float32)


def write_wav(path, audio):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.asarray(audio)
    if not np.isfinite(audio).all() or np.max(np.abs(audio), initial=0) > 1.0001:
        raise ValueError("Output is not normalized finite PCM.")
    wavfile.write(path, RATE, np.rint(np.clip(audio, -1, 1)*32767).astype(np.int16))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract a channel and resample a WAV to 16 kHz.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--channel", type=int, default=0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new path.")
    write_wav(args.output, read_wav(args.input, args.channel))


if __name__ == "__main__":
    main()
