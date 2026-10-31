# Dataset, ML training and evaluation

The shipped learned model is a **speech-presence controller**, not a deep speech
reconstructor. Eight causal features feed eight tanh hidden units and one sigmoid
output. Its 81 float32 parameters occupy 324 bytes before alignment/metadata.
NLMS does the main correlated-noise subtraction; the model controls adaptation
and the residual postfilter. Everything executes on the ESP32-S3 at runtime.

## Reproduce the shipped demo

From the repository root, with the host virtual environment active:

```bash
make
python -m ml.make_dataset --demo --output data/demo --examples 90 --seed 26052
OPENBLAS_NUM_THREADS=1 python -m ml.train --manifest data/demo/manifest.jsonl --model models/demo_model.json --header components/mounam_dsp/include/model_weights.h --epochs 60 --seed 180588
make test
python -m tools.evaluate --manifest data/demo/manifest.jsonl --mode hybrid --output models/demo_evaluation_hybrid.json
python -m tools.evaluate --manifest data/demo/manifest.jsonl --mode dsp --output models/demo_evaluation_dsp.json
```

Use a new output directory if `data/demo` already contains a dataset. The dataset
generator refuses to overwrite an existing nonempty folder. Generated WAV/NPZ
data is excluded from git by default. Preserve a corpus privately if it cannot
be reproduced.

The demo uses harmonic voice-like signals with interruptions plus generated
stationary, modulated and impulsive noise. They exercise the complete data and
training path but do not establish human intelligibility or defence performance.
The `synthetic_demo` provenance is compiled into firmware telemetry.

Feature extraction calls the **same C++ implementation** as the board through a
small native shared library. There is no separate Python approximation of the
feature pipeline. NumPy trains the MLP with binary cross-entropy and Adam;
the best validation loss selects the exported weights. Test examples are not
used for training or model selection.

With the committed seeds and 90 examples, there are 54 train, 18 validation and
18 test examples. The shipped model's identifier is recorded in its JSON and
header. Small differences in math libraries can change the final trained
weights; C++/Python prediction parity is checked for the actual exported model.
The original training versions are recorded in
[models/demo_environment.json](../models/demo_environment.json).

## Use real recordings

Prepare **clean speech** recorded in quiet surroundings and separate noise WAV
files. Place each speaker's files inside their own directory, for example:

| Input path | Contents |
| --- | --- |
| `corpus/speech/speaker01/*.wav` | One speaker, quiet speech |
| `corpus/speech/speaker02/*.wav` | Another speaker |
| `corpus/speech/speaker03/*.wav` | Another speaker; at least three speaker folders required |
| `corpus/noise/*.wav` | At least three independent noise recordings |

Use more speakers, languages and noise sources for a useful evaluation. Include
Tamil/Hindi/English speech if those are intended use cases, varied voices,
stationary engines/fans, moving or modulated sources, wind, and recorded
transients. Acquire noises as files or at ordinary playback levels. Include
speech/noise mixtures at -10, -5, 0, 5, 10 and 15 dB nominal mixing SNR.

```bash
python -m ml.make_dataset --speech-dir corpus/speech --noise-dir corpus/noise --output data/recorded-v1 --examples 600 --seconds 2 --seed 26052
OPENBLAS_NUM_THREADS=1 python -m ml.train --manifest data/recorded-v1/manifest.jsonl --model models/recorded_model.json --header components/mounam_dsp/include/model_weights.h --epochs 100
make test
python -m tools.evaluate --manifest data/recorded-v1/manifest.jsonl --mode hybrid --output build/recorded-test.json
```

The loader selects channel 0 from source WAVs and resamples to 16 kHz. Speakers
and noise files are split **before** mixing; a source ID cannot span splits.
Byte-identical duplicate source files spanning splits are rejected. Different
edits of the same recording still need manual grouping; their content hash alone
cannot establish independence. Keep related recordings under the same speaker
identity and curate independent noise sources.

Mixtures include a causal primary noise path, small reference speech leakage,
sensor-like noise and a common scale chosen to avoid clipping. These are simulated
microphone paths. Reverberation, clipping augmentation and measured two-mic
transfer functions remain additions for a stronger corpus; they are not
implemented just because the problem statement mentions them.

The generator writes each pair (`primary`, `reference`, `clean`) to NPZ and records
its SHA-256 hash, split, source IDs, mixing SNR and provenance in a JSONL manifest.
Training/evaluation verify those hashes and reject cross-split source reuse.
Real defence noises, even when mixed with real speech, require a genuinely
independent live-acoustic evaluation too.

## Capture with your microphones

```bash
python -m tools.device --port /dev/ttyUSB0 capture --seconds 15 --output captures/quiet-speaker01-take01.wav
python -m tools.audio captures/quiet-speaker01-take01.wav corpus/speech/speaker01/take01.wav --channel 0
python -m tools.device --port /dev/ttyUSB0 capture --seconds 15 --output captures/fan-noise01.wav
python -m tools.audio captures/fan-noise01.wav corpus/noise/fan-noise01.wav --channel 1
```

Record the speech take in quiet conditions and the noise take with no speech.
Repeat for additional speakers/noise recordings. The first file's primary mic
can serve as quiet speech; the second file's reference can serve as a noise
source. A noisy two-mic recording itself does **not** supply a clean target.
Never relabel its reference channel as clean speech.

Raw board capture is two-channel PCM16 converted from the microphones' 24-bit
samples. It preserves the captured level and can lose precision for very quiet
signals. Serial capture uses sequence numbers and CRC-32; corrupt or missing
blocks reject the capture rather than silently shifting alignment.

## Evaluate the actual DSP

`tools.evaluate` calls the compiled firmware DSP on the held-out split. It
compares output against the clean target at the configured output gain, skips
500 ms of filter startup by default and compensates only the explicitly selected
primary delay. It reports input/output SNR and SI-SDR, with per-example results.
For noise-only clips it reports noise-only reduction instead of undefined speech
SNR. RMS attenuation of mixed speech is never presented as an SNR measurement.

For real speech metrics, optionally install:

```bash
python -m pip install -r requirements-metrics.txt
python -m tools.evaluate --manifest data/recorded-v1/manifest.jsonl --mode hybrid --with-perceptual --output build/recorded-perceptual-test.json
```

Review the PESQ implementation/licensing requirements for your intended use.
Missing optional libraries or an invalid perceptual test return null metrics
with an explicit reason. Never compute/report intelligibility on the synthetic
harmonic demo as evidence of human speech quality.

## Deploy a retrained model

The trainer writes ordinary C++ weights. No network download, dynamic model loader,
TFLite interpreter, ONNX runtime or TensorRT is used on the ESP32-S3.

After exporting a new header, run `make` again so host replay uses those weights.
Build and flash the firmware again from its ESP-IDF terminal:

```bash
cd firmware
idf.py build
idf.py -p /dev/ttyUSB0 -b 460800 flash
```

Check `model` and `model_id` in live stats against the exported JSON. Keep a copy
of each model JSON, its header, training manifest and held-out report. The shipped
demo parity test checks the demo model only; when a different model is compiled,
evaluate its predictions against its own exported parameters before release.
