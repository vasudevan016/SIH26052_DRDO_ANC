"""Measure paired clean/noisy enhancement; output level changes are never called SNR."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from ml.native import enhance, library
from ml.train import read_manifest


def snr(clean, estimate):
    return float(10*np.log10((np.sum(clean*clean)+1e-12)/(np.sum((estimate-clean)**2)+1e-12)))


def si_sdr(clean, estimate):
    clean, estimate = clean-clean.mean(), estimate-estimate.mean()
    projected = clean*(np.dot(clean, estimate)/(np.dot(clean, clean)+1e-12))
    return float(10*np.log10((np.sum(projected**2)+1e-12)/(np.sum((estimate-projected)**2)+1e-12)))


def perceptual(clean, estimate, enabled):
    result = {"stoi": None, "pesq_wb": None}
    reasons = {}
    if not enabled:
        return {**result, "perceptual_status": "not_requested"}
    for name in ("stoi", "pesq_wb"):
        try:
            if name == "stoi":
                from pystoi import stoi
                result[name] = float(stoi(clean, estimate, 16000, extended=False))
            else:
                from pesq import pesq
                result[name] = float(pesq(16000, clean, estimate, "wb"))
        except Exception as exc:
            reasons[name] = type(exc).__name__+": "+str(exc)
        if result[name] is not None and not np.isfinite(result[name]):
            result[name] = None; reasons[name] = "metric returned a non-finite result"
    return {**result, "perceptual_status": reasons or "computed"}


def evaluate_pair(clean, primary, output, gain, warmup=8000, delay=0, with_perceptual=False):
    if len(clean) <= warmup+delay+32:
        raise ValueError("Clip too short for the selected warmup and delay.")
    if delay:
        clean, primary, output = clean[:-delay], primary[:-delay], output[delay:]
    clean, primary, output = (np.asarray(x[warmup:], dtype=np.float64) for x in (clean, primary, output))
    if np.sum(clean**2) < 1e-8:
        return {"speech": False, "noise_only_reduction_db": float(10*np.log10(
            (np.sum((primary*gain)**2)+1e-12)/(np.sum(output**2)+1e-12)))}
    target = clean*gain
    return {"speech": True, "input_snr_db": snr(clean, primary), "output_snr_db": snr(target, output),
        "input_si_sdr_db": si_sdr(clean, primary), "output_si_sdr_db": si_sdr(target, output),
        **perceptual(target, output, with_perceptual)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", choices=["validation", "test"], default="test")
    parser.add_argument("--mode", choices=["primary", "dsp", "hybrid"], default="hybrid")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gain", type=float, default=0.05)
    parser.add_argument("--warmup-ms", type=float, default=500)
    parser.add_argument("--delay", type=int, default=0)
    parser.add_argument("--with-perceptual", action="store_true")
    args = parser.parse_args()
    if not 0 < args.gain <= 1 or args.warmup_ms < 0 or not 0 <= args.delay <= 64:
        parser.error("gain must be >0..1, warmup >=0 ms and delay 0..64 samples")
    rows = read_manifest(args.manifest)
    results = []
    for row in rows:
        if row["split"] != args.split:
            continue
        with np.load(args.manifest.parent/row["path"], allow_pickle=False) as pair:
            stereo = np.column_stack([pair["primary"], pair["reference"]])
            output = enhance(stereo, args.mode, args.gain, delay=args.delay)
            score = evaluate_pair(pair["clean"], pair["primary"], output, args.gain,
                round(args.warmup_ms*16), args.delay, args.with_perceptual)
        results.append({"path": row["path"], "noise_type": row["noise_type"], "nominal_mix_snr_db": row["snr_db"], **score})
    if not results:
        raise ValueError("Selected evaluation split is empty.")
    summary = {}
    for name in ("input_snr_db", "output_snr_db", "input_si_sdr_db", "output_si_sdr_db", "stoi", "pesq_wb", "noise_only_reduction_db"):
        values = [row[name] for row in results if row.get(name) is not None]
        summary[name] = {"mean": float(np.mean(values)), "median": float(np.median(values)), "count": len(values)} if values else None
    report = dict(mode=args.mode, model=library().mounam_model_provenance().decode(), gain=args.gain,
        model_id=library().mounam_model_id().decode(),
        neural_model_id=library().mounam_neural_id().decode(),
        neural_provenance=library().mounam_neural_provenance().decode(),
        split=args.split, warmup_ms=args.warmup_ms, primary_delay=args.delay,
        manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        provenance=sorted({r["provenance"] for r in rows}), summary=summary, pairs=results,
        notes="Offline software evaluation. No hardware latency, acoustic attenuation, power or real defence performance is inferred.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"report": str(args.output), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
