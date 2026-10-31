import argparse
import json
from pathlib import Path
from ml.native import enhance, library
from tools.audio import read_wav, write_wav


def main():
    parser = argparse.ArgumentParser(description="Process a dual-mic WAV with the actual firmware DSP core.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["primary", "reference", "dsp", "hybrid"], default="hybrid")
    parser.add_argument("--gain", type=float, default=0.05)
    parser.add_argument("--hold", action="store_true")
    parser.add_argument("--delay", type=int, default=0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new filename.")
    stereo = read_wav(args.input)
    output = enhance(stereo, args.mode, args.gain, args.hold, args.delay)
    write_wav(args.output, output)
    print(json.dumps({"output": str(args.output), "mode": args.mode, "gain": args.gain,
        "model": library().mounam_model_provenance().decode(), "source": "shared firmware C++ core",
        "hardware_latency_measured": False}, indent=2))


if __name__ == "__main__":
    main()
