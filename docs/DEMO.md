# A strong 90-second demonstration

Use the exact hardware, a low-volume fan/recorded noise source, a headphone
amplifier and consented spoken phrases. Keep original and enhanced modes at the
same digital gain and physical volume.

| Time | Show |
| --- | --- |
| 0-15 s | Point to both mics, ESP32-S3 and DAC. Explain that audio works offline; power it without any network. |
| 15-35 s | Press **d**, then **1**. Say a short phrase while the quiet noise source runs. This is the original microphone signal. |
| 35-55 s | Press **3**, repeat the same phrase, then alternate **1 / 3**. Use BOOT for the same comparison without a computer. |
| 55-75 s | Show actual input levels, maximum DSP duration, and zero overrun/error counters. Label these as processing/continuity data. |
| 75-90 s | Show a held-out real-speech report, actual power/BOM measurements and the model ID used. If these are not measured yet, say so. |

Press **m** or hold BOOT for one second to mute. The first short BOOT press after
startup enables the low-gain hybrid demo; subsequent taps alternate original /
hybrid. This uses the board's existing button, not another purchased part.

## Evidence to collect before judging

- Record quiet clean speech from several speakers and independent noises; train
  and evaluate using [TRAINING.md](TRAINING.md).
- Evaluate stationary, modulated and recorded transient noise separately at
  several input SNRs. Include failures and the DSP-only baseline.
- Preserve raw recordings, firmware/model IDs, unchanged gain, source positions
  and the full report. Never rename microphone reference audio as clean speech.
- Measure end-to-end latency and power using the [validation plan](VALIDATION.md).
  DSP processing duration is only one part of latency.
- Show the actual hardware cost, including the headphone amplifier and power
  supply. Keep prototype cost separate from a production estimate.

The strongest claim this implementation supports now is a working offline
dual-mic speech-enhancement prototype with reproducible code and honest metrics.
The demo model uses synthetic signals; real recordings and measurements are the
next step toward the problem statement's score targets. Ordinary earphones and
this DSP do not establish certified impulse-noise hearing protection.
