# Reproduce and retrain the real AI models

Inference runs entirely on the ESP32-S3. Training runs on a local computer or
GitHub Actions. No raw microphone recordings or cloud connection are needed for
normal device operation.

## Models included in the release

| Stage | Architecture | Job |
| --- | --- | --- |
| Speech controller | 8-8-1 tanh/sigmoid, float32 | Estimate speech presence and protect adaptive learning |
| Suppression model | 26-24-8 tanh/sigmoid, per-row int8 weights | Predict eight frequency-band gains on the NLMS residual |

The second model uses 816 int8 weights, 32 float32 biases and 32 float32 scales:
1,072 bytes of numeric parameters. Activations and DSP are float32; this is
**weight quantization**, not an integer-only inference engine. The model does
not use TensorFlow, ONNX, TensorRT or an external runtime on the MCU.

Its features are eight smoothed residual powers, eight reference powers, eight
log power ratios, speech probability and coherence. Features and oracle training
targets are extracted through the exact C++ processing engine used on the board.
The bounded least-squares band-gain targets use the known clean training signal;
that signal is never available or required during inference.

## Reproduce the public-speech release

In a separate host-tools terminal, from the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-metrics.txt
make
python -m ml.prepare_public --output data/public-v2 --examples 600 --speakers 120
OPENBLAS_NUM_THREADS=1 python -m ml.train --manifest data/public-v2/manifest.jsonl --model models/speech_model.json --header components/mounam_dsp/include/model_weights.h --epochs 70
make
OPENBLAS_NUM_THREADS=1 python -m ml.train_neural --manifest data/public-v2/manifest.jsonl --model models/neural_model.json --header components/mounam_dsp/include/neural_weights.h --epochs 60
make test
python -m tools.evaluate --manifest data/public-v2/manifest.jsonl --mode hybrid --with-perceptual --output build/your-test-report.json
```

A fresh empty corpus directory is required. The official TensorFlow mini Speech
Commands archive is checked against the released SHA-256 pin. Training uses the
training split only; validation loss selects checkpoints. Test-speaker metrics
are computed after training. The checked-in training workflow reproduces these
steps, records validation as well as test results, and exports both headers and
provenance JSONs.

The released corpus has 58 training speakers, 24 validation speakers and 38 test
speakers. There are 360/120/120 paired clips respectively. Every clip contains
two seconds of audio; each split contains both speech and noise-only examples.
The generator simulates distinct causal mic paths, reference speech leakage,
unshared sensor noise, changing levels and nominal mixing SNRs from -10 to 15 dB.

The speech is genuinely human-recorded, but consists of short English commands.
The noises are generated surrogates, not real gunfire, aircraft or field recordings.
Nominal clean targets are the original recordings, which are not studio-isolated
speech. These limits matter when interpreting the results.

Small numerical differences across BLAS/compiler/library versions can change
retrained weights. Use the committed JSON/header pair for exact release inference.
Model IDs, header/JSON inference parity, data checksums, quantization error and
per-example results are retained. No failed metric is replaced with a made-up
number; reports retain valid counts and failure reasons.

## Your own speech and noise

Record quiet speech from several consented speakers and independent noises.
For paired data creation, organize clean speech as `corpus/speech/<speaker>/*.wav`
and noise as `corpus/noise/*.wav`. At least three speakers and three noise sources
are required; use far more for meaningful validation. Include the languages and
speakers expected in the final communication task.

```bash
python -m ml.make_dataset --speech-dir corpus/speech --noise-dir corpus/noise --output data/your-corpus --examples 600 --seconds 2
OPENBLAS_NUM_THREADS=1 python -m ml.train --manifest data/your-corpus/manifest.jsonl --model models/speech_model.json --header components/mounam_dsp/include/model_weights.h --epochs 100
make
OPENBLAS_NUM_THREADS=1 python -m ml.train_neural --manifest data/your-corpus/manifest.jsonl --model models/neural_model.json --header components/mounam_dsp/include/neural_weights.h --epochs 80
make test
```

Speakers and noise files are separated before mixing. Manifest hashes and source
IDs are checked; related edits of the same recording still need manual grouping.
Never use the same underlying speech/noise recording across training and test
under different filenames.

Capture your microphone pair with:

```bash
python -m tools.device --port /dev/ttyUSB0 capture --seconds 15 --output captures/take01.wav
```

This is primary/reference **input**, not noisy/clean ground truth or a recording
of the DAC output. Quiet speech takes can supply source speech; speech-free noise
takes can supply noise sources. Extract the intended channel with `tools.audio`.
Sequence gaps and CRC failures reject the capture. Raw capture is PCM16 at 16 kHz.

## Deployment after training

Export both models, run inference-parity tests and evaluate a speaker-disjoint
holdout. Rebuild/package/flash using [BUILD.md](BUILD.md). The flashing helper
rejects an image when its source fingerprint no longer matches the source files.
The package also checks that the compiled binary contains the current model IDs.
Keep each model, header, source manifest and report together. New model training
alone does not establish physical latency, acoustic safety or defence readiness.
