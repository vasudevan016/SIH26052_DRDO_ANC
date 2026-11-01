# A clear 90-second hackathon demonstration

Use a quiet fan or recorded noise at ordinary playback level, the exact two-mic
node, a stereo headphone amplifier and consented spoken phrases. Place the
primary near the mouth and reference away from the voice, toward the noise.

| Time | Show |
| --- | --- |
| 0-15 s | Explain the offline mic -> ESP32-S3 -> DAC -> amplifier path. Show that no network is required. |
| 15-25 s | Press Calibrate / **c**, keep quiet for three seconds. Then Start audio / **d**. |
| 25-50 s | Say the same phrase in Original / **1** and Neural / **3** modes at unchanged gain and amplifier volume. |
| 50-65 s | Show actual device DSP timing, band gains and zero overflow/error counters. These are processing/continuity data, not speech-quality scores. |
| 65-80 s | Show the recorded public-speaker results, source archive hash and model IDs. State that noise and microphone paths are simulated in that benchmark. |
| 80-90 s | Demonstrate BOOT-button A/B switching, then hold BOOT for one second to mute. |

The browser dashboard is optional. From the repository root, close any terminal
serial console and run `python3 -m tools.dashboard`. The page connects directly
to the board over USB and keeps live device metrics separate from software scores.
Do not show prerecorded data as a live device result.

## Explain the contribution precisely

- Two synchronized digital microphones provide primary and independent reference
  signals; DMA and fixed buffers keep the audio task deterministic.
- The MCU combines bounded adaptive filtering with **learned eight-band gains**.
  Both trained models, int8 weight export and matching native inference are supplied.
- Calibration, voice guards and a reference-confirmed transient detector protect
  speech onsets; the model is evaluated against an unchanged-gain DSP baseline.
- Flashing is one command. The released image is checksum/source verified and
  checked against Espressif's own image merger.

Report the full [results table](RESULTS.md), including limits and failures. Global
means do not yet pass every stated metric target. The benchmark uses short English
commands and generated noises; it cannot establish continuous tactical-speech,
actual gunfire, end-to-end latency, power or certified hearing protection.

Before judging, capture the real node, collect additional consented speech in the
intended languages, evaluate actual independent noise sources and measure power
and latency with the [validation protocol](VALIDATION.md). Keep original audio,
model/firmware IDs, mic positions and volume settings with your evidence.
