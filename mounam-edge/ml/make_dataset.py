"""Create reproducible noisy/clean/reference pairs; synthetic demo is explicitly tagged."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.signal import lfilter
from tools.audio import read_wav

RATE = 16000


def rms(x):
    return float(np.sqrt(np.mean(np.square(x), dtype=np.float64) + 1e-12))


def synthetic_speech(rng, frames):
    # Harmonic/formant-like test signal, never claimed to be a real speech corpus.
    t = np.arange(frames)/RATE
    f0 = rng.uniform(90, 260)
    phase = 2*np.pi*(f0*t + 2*np.sin(2*np.pi*2*t))
    voice = sum(np.sin(k*phase + rng.uniform(-0.1, 0.1))/k for k in range(1, 12))
    voice += 0.15*rng.normal(size=frames)
    envelope = np.maximum(0, np.sin(2*np.pi*rng.uniform(2, 5)*t))**0.5
    envelope *= (np.sin(2*np.pi*0.8*t + rng.uniform(0, 4)) > -0.2)
    return voice*envelope


def synthetic_noise(rng, frames, kind):
    t = np.arange(frames)/RATE
    white = rng.normal(size=frames)
    if kind == "stationary":
        return lfilter([0.2], [1, -0.8], white) + 0.8*np.sin(2*np.pi*rng.uniform(80, 240)*t)
    if kind == "nonstationary":
        return (0.1 + 0.8*np.sin(2*np.pi*6*t)**2) * (np.sin(2*np.pi*140*t) + 0.4*white)
    noise = 0.08*white
    for position in rng.integers(0, frames-1000, size=4):
        burst = rng.normal(size=800)*np.exp(-np.arange(800)/100)
        noise[position:position+800] += 3*burst
    return noise


def mix_pair(clean, noise, snr_db, rng, speech=True):
    clean = np.asarray(clean, dtype=np.float64)
    noise = np.asarray(noise, dtype=np.float64)
    clean = clean/(rms(clean)+1e-10)*0.04 if speech else np.zeros_like(clean)
    noise = noise/(rms(noise)+1e-10) * 0.04 * 10**(-snr_db/20)
    # Reference hears noise first; primary noise includes a different causal path.
    lag = int(rng.integers(2, 20))
    path = np.zeros(lag+8); path[lag] = 0.8; path[-1] = 0.15
    primary_noise = lfilter(path, [1], noise)
    reference = noise + rng.uniform(0, 0.08)*clean + rng.normal(0, 0.001, len(clean))
    primary = clean + primary_noise + rng.normal(0, 0.001, len(clean))
    scale = min(1, 0.85/(max(np.max(np.abs(primary)), np.max(np.abs(reference)), np.max(np.abs(clean)))+1e-9))
    return dict(primary=(primary*scale).astype(np.float32), reference=(reference*scale).astype(np.float32),
                clean=(clean*scale).astype(np.float32))


def chunk(audio, frames, rng):
    if len(audio) < frames:
        return np.tile(audio, int(np.ceil(frames/len(audio))))[:frames]
    start = int(rng.integers(0, len(audio)-frames+1))
    return audio[start:start+frames]


def source_split(items):
    # Input order is seeded before this call; preserve at least one source per split.
    n = len(items)
    if n < 3:
        raise ValueError("Need at least three independent speakers and three noise files.")
    train_end = max(1, int(n*0.6))
    val_end = min(n-1, max(train_end+1, int(n*0.8)))
    return {"train": items[:train_end], "validation": items[train_end:val_end], "test": items[val_end:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--speech-dir", type=Path)
    parser.add_argument("--noise-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=90, help="Total across three source-disjoint splits.")
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=26052)
    args = parser.parse_args()
    if args.examples < 15 or args.seconds < 0.25 or args.seconds > 30:
        parser.error("Use >=15 examples, 0.25..30 seconds per example.")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output folder must be empty; datasets are never silently replaced.")
    if not args.demo and (not args.speech_dir or not args.noise_dir):
        parser.error("Supply --speech-dir and --noise-dir, or explicitly use --demo.")
    rng = np.random.default_rng(args.seed)
    frames = int(args.seconds*RATE)//32*32
    groups = noise_groups = None
    if not args.demo:
        speakers = sorted(p for p in args.speech_dir.iterdir() if p.is_dir() and list(p.rglob("*.wav")))
        noises = sorted(args.noise_dir.rglob("*.wav"))
        rng.shuffle(speakers); rng.shuffle(noises)
        groups = source_split(speakers); noise_groups = source_split(noises)
        # Duplicate audio under different filenames must not cross evaluation splits.
        for category, splits in (("speech", groups), ("noise", noise_groups)):
            seen = {}
            for split, paths in splits.items():
                for path in paths:
                    for file in (sorted(path.rglob("*.wav")) if path.is_dir() else [path]):
                        digest = hashlib.sha256(file.read_bytes()).hexdigest()
                        if digest in seen and seen[digest] != split:
                            raise ValueError(f"Duplicate {category} audio spans splits: {file}")
                        seen[digest] = split
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    counts = [args.examples*3//5, args.examples//5]
    counts.append(args.examples-sum(counts))
    for split, count in zip(("train", "validation", "test"), counts):
        for index in range(count):
            kind = ("stationary", "nonstationary", "impulsive")[index % 3]
            if args.demo:
                clean = synthetic_speech(rng, frames)
                noise = synthetic_noise(rng, frames, kind)
                speaker = f"demo-{split}-voice-{index}"
                noise_source = f"demo-{split}-{kind}-{index}"
            else:
                speaker_path = groups[split][index % len(groups[split])]
                speech_files = sorted(speaker_path.rglob("*.wav"))
                speech_path = speech_files[int(rng.integers(len(speech_files)))]
                noise_path = noise_groups[split][index % len(noise_groups[split])]
                clean = chunk(read_wav(speech_path, 0), frames, rng)
                noise = chunk(read_wav(noise_path, 0), frames, rng)
                speaker = str(speaker_path.relative_to(args.speech_dir))
                noise_source = str(noise_path.relative_to(args.noise_dir))
                kind = "recorded_unlabelled"
            speech = index % 4 != 0
            snr_db = float(rng.choice([-10, -5, 0, 5, 10, 15]))
            pair = mix_pair(clean, noise, snr_db, rng, speech)
            filename = f"{split}-{index:04d}.npz"
            target = args.output / filename
            np.savez_compressed(target, **pair)
            records.append(dict(path=filename, split=split, noise_type=kind, snr_db=snr_db,
                speech=speech, speaker_id=speaker, noise_id=noise_source,
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                provenance="synthetic_demo" if args.demo else "recorded_sources_synthetic_mixtures"))
    manifest = args.output/"manifest.jsonl"
    manifest.write_text("".join(json.dumps(row, sort_keys=True)+"\n" for row in records))
    print(json.dumps({"manifest": str(manifest), "examples": len(records), "seed": args.seed,
                      "provenance": records[0]["provenance"]}, indent=2))


if __name__ == "__main__":
    main()
