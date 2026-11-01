"""Build speaker-disjoint pairs from real Speech Commands audio and generated noises."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import chirp, lfilter
from ml.make_dataset import rms

URL = "https://storage.googleapis.com/download.tensorflow.org/data/mini_speech_commands.zip"
RATE = 16000


def noise_signal(rng, frames, kind):
    t = np.arange(frames)/RATE
    white = rng.normal(size=frames)
    if kind == "stationary":
        return lfilter([0.18], [1, -0.82], white)+0.6*np.sin(2*np.pi*rng.uniform(70, 220)*t)
    if kind == "rotor_modulated":
        f = rng.uniform(70, 180)
        mechanical = sum(np.sin(2*np.pi*f*k*t)/k for k in range(1, 6))
        return (0.2+0.8*np.sin(2*np.pi*rng.uniform(4, 12)*t)**2)*(mechanical+0.15*white)
    if kind == "siren_chirp":
        return chirp(t, rng.uniform(300, 700), t[-1], rng.uniform(1200, 2600))+0.2*white
    if kind == "wind_colored":
        return lfilter([0.06], [1, -0.94], white)*(0.2+0.8*np.sin(2*np.pi*1.3*t)**2)
    noise = 0.025*white
    for position in rng.integers(0, frames-1600, size=int(rng.integers(3, 8))):
        burst = rng.normal(size=1200)*np.exp(-np.arange(1200)/rng.uniform(35, 120))
        noise[position:position+1200] += 4*burst
    return noise


def prepare(output, examples, speakers, seed):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new empty corpus output directory.")
    output.mkdir(parents=True, exist_ok=True)
    archive = output/"source.zip"
    print("Downloading the official TensorFlow mini Speech Commands corpus...", flush=True)
    with urllib.request.urlopen(URL, timeout=90) as response, archive.open("wb") as file:
        while chunk := response.read(1024*1024):
            file.write(chunk)
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    # Once a release pins this archive, a changed upstream download is rejected.
    source_card = Path(__file__).resolve().parents[1]/"models/public_data_sources.json"
    if source_card.exists():
        pin = json.loads(source_card.read_text()).get("archive_sha256")
        if pin and pin != archive_sha:
            raise ValueError("Upstream corpus hash differs from the released source pin.")
    with zipfile.ZipFile(archive) as zipped:
        by_speaker = {}
        for name in sorted(zipped.namelist()):
            path = Path(name)
            if path.suffix.lower() != ".wav" or "__MACOSX" in path.parts or "_nohash_" not in path.name:
                continue
            speaker = path.stem.split("_nohash_")[0]
            by_speaker.setdefault(speaker, []).append(name)
        selected = sorted(by_speaker, key=lambda s: hashlib.sha256((str(seed)+s).encode()).hexdigest())[:speakers]
        split_sources = {"train":[], "validation":[], "test":[]}
        for speaker in selected:
            code = int(hashlib.sha256(speaker.encode()).hexdigest()[:8], 16)%10
            split_sources["train" if code < 6 else "validation" if code < 8 else "test"].append(speaker)
        if any(len(v) < 3 for v in split_sources.values()):
            raise ValueError("Need at least three independent speakers per split.")
        rng = np.random.default_rng(seed)
        counts = [examples*3//5, examples//5]; counts.append(examples-sum(counts))
        records = []
        types = ["stationary", "rotor_modulated", "siren_chirp", "wind_colored", "impulsive"]
        for split, count in zip(split_sources, counts):
            for index in range(count):
                speaker = split_sources[split][index % len(split_sources[split])]
                names = by_speaker[speaker]
                name = names[int(rng.integers(len(names)))]
                rate, pcm = wavfile.read(io.BytesIO(zipped.read(name)))
                if rate != RATE or pcm.dtype != np.int16 or pcm.ndim != 1:
                    raise ValueError("Unexpected source WAV encoding.")
                voice = pcm.astype(np.float64)/32768
                frames = 32000
                clean = np.zeros(frames)
                offset = int(rng.integers(4800, 7200))
                clean[offset:offset+len(voice)] = voice
                speech = index % 4 != 0
                if speech:
                    clean *= rng.uniform(0.025, 0.065)/(rms(clean)+1e-9)
                else:
                    clean.fill(0)
                kind = types[index % len(types)]
                noise = noise_signal(rng, frames, kind)
                snr = float([-10, -5, 0, 5, 10, 15][(index//5) % 6])
                amplitude = rms(clean) if speech else 0.04
                noise *= amplitude*10**(-snr/20)/(rms(noise)+1e-9)
                # Distinct causal mic paths, reference speech leakage and unshared noise.
                lag = int(rng.integers(2, 24))
                path = np.zeros(lag+10); path[lag] = rng.uniform(0.65, 0.95); path[-1] = rng.uniform(-0.15, 0.2)
                primary = clean+lfilter(path, [1], noise)
                primary += rng.normal(0, rms(noise)*rng.uniform(0.01, 0.08)+0.0002, frames)
                reference = noise+rng.uniform(0, 0.12)*clean+rng.normal(0, 0.0003, frames)
                scale = min(1, 0.9/(max(np.max(np.abs(primary)), np.max(np.abs(reference)), np.max(np.abs(clean)))+1e-9))
                filename = f"{split}-{index:04d}.npz"
                target = output/filename
                np.savez_compressed(target, primary=(primary*scale).astype(np.float32),
                    reference=(reference*scale).astype(np.float32), clean=(clean*scale).astype(np.float32))
                records.append(dict(path=filename, split=split, speaker_id=speaker, noise_id=f"generated-{split}-{index}",
                    source_wav=name, source_wav_sha256=hashlib.sha256(zipped.read(name)).hexdigest(),
                    speech=speech, snr_db=snr, noise_type=kind, provenance="public_human_speech_generated_noise",
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    (output/"manifest.jsonl").write_text("".join(json.dumps(r, sort_keys=True)+"\n" for r in records))
    metadata = dict(dataset="TensorFlow mini Speech Commands (human recordings)", url=URL,
        archive_sha256=archive_sha, license="CC BY 4.0", attribution="Speech Commands dataset, Pete Warden and contributors, Google/TensorFlow",
        reference="https://research.google/blog/launching-the-speech-commands-dataset/",
        seed=seed, examples=examples, speakers={k:len(v) for k,v in split_sources.items()},
        speaker_ids=split_sources, noises="Generated stationary, modulated, chirp, wind and impulse signals; not actual defence recordings.",
        limitations="Short English command recordings; simulated mic paths; no physical-hardware or continuous-speech validation.")
    (output/"source_card.json").write_text(json.dumps(metadata, indent=2)+"\n")
    archive.unlink()  # Pairs and their source identities suffice for this run.
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=600)
    parser.add_argument("--speakers", type=int, default=120)
    parser.add_argument("--seed", type=int, default=26052)
    args = parser.parse_args()
    if args.examples < 60 or args.speakers < 30:
        parser.error("Use at least 60 examples and 30 speakers.")
    print(json.dumps(prepare(args.output, args.examples, args.speakers, args.seed), indent=2))


if __name__ == "__main__":
    main()
