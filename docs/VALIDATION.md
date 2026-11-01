# Release verification and physical acceptance tests

## Automated checks

The project runs native C++ DSP invariants, Python integration checks, address /
undefined-behavior sanitizers, ESP-IDF target compilation and browser checks.

| Area | What is checked |
| --- | --- |
| Audio core | Signed I2S packing, CRC, DC removal, complementary band reconstruction, NLMS convergence, finite/bounded output and mute |
| Speech/transients | A primary-only onset does not trigger the noise attenuator; a simultaneous reference shock does |
| Calibration | Explicit noise-only settings force output mute |
| Models | Active header/JSON identity, speech-model prediction parity, int8 gain-model prediction parity, bounded causal features/targets |
| Data/metrics | Source leakage rejection, paired metrics, output-volume changes cannot masquerade as SNR |
| Capture | Fragmented packets, CRC corruption, resynchronization and sequence continuity |
| Image | N16P8 config, region layout, checksum, source fingerprint and compiled model IDs |
| Flash helper | Multiple USB ports are not guessed; chip/offset command arguments are explicit |
| Dashboard | Local server exposes only approved routes; desktop/mobile layout, disconnected empty readings and USB control contract |
| MCU build | ESP32-S3, ESP-IDF v5.4.3, 16-MB flash, octal PSRAM, 240-MHz CPU and UART settings |

Image packaging is compared byte-for-byte with Espressif's `merge_bin`. The
flashing helper rejects a mismatched image or changed firmware source. GitHub
Actions exports the firmware/model/browser artifacts used for verification.
A browser serial double is used only in tests; production UI never generates
fake live readings. Layout screenshots show the disconnected UI and real included
software reports, not invented connected-device metrics.

On restricted development hosts, leak scanning can be unavailable because `/proc`
thread inspection is blocked; use `ASAN_OPTIONS=detect_leaks=0 make sanitize` there.
GitHub's regular Linux runner also runs sanitizer checks with its default scanner.
No physical board has been connected or flashed by this development session.

## Software evaluation

[RESULTS.md](RESULTS.md) contains the measured means and per-noise results from
120 speaker-disjoint test examples, of which 90 contain speech. `models/` retains
full validation/test reports, metric counts, source archive hash and model IDs.
Human speech is real; the noises and mic paths are simulated. Checkpoints use
validation loss, and the test set is evaluated after training. These scores do
not establish field readiness or that every problem-statement target is passed.

## Physical measurements still required

| Requirement | Method / acceptance evidence |
| --- | --- |
| Input synchronization | Scope WS 16 kHz and BCLK 1.024 MHz, check distinct L/R mic signals |
| DSP deadline | GPIO10 pulse and device timings; worst DSP processing below the **2-ms block period**, zero late blocks over >=30 minutes |
| Continuity | Zero RX overflows and I/O faults during normal standalone operation |
| End-to-end latency | Synchronized stimulus / input-to-analog-output recording; report median/p95/max and instrument delays |
| Speech quality | Independent real clean/noisy pairs and separately identified actual-microphone tests |
| Problem targets | SNR >15 dB, STOI >0.85, PESQ >2.5 under a stated representative protocol; do not substitute a favorable single sample |
| Output | Test DAC plus amplifier into an appropriate load before wearing earphones; verify mute, ramp and clipping behavior |
| Power | Inline meter at the actual supply, including MCU, mics, DAC, amplifier and regulator |
| Cost | Actual prototype receipts; separate production PCB/assembly estimates |
| Standalone controls | BOOT tap/start/compare and one-second hold/mute on the actual DevKit |

The timing percentiles in telemetry are **16-us histogram-bin upper bounds for
DSP processing only**. They exclude microphone conversion, RX accumulation,
DMA queueing, DAC conversion and amplifier delay. A small DSP duration does not
prove a sub-5-ms microphone-to-earphone path. Three descriptors, 2-ms blocks and
any user-selected primary delay all contribute to that path.

Do not expose people to real gunfire, explosions or hazardous playback to test
this prototype. A clipped microphone loses information software cannot recover.
Ordinary earphones plus microphone enhancement do not establish acoustic ANC at
the eardrum or certified hearing protection.

## Serial capture protocol

UART0 uses 921600 baud, 8-N-1. Text mode emits actual JSON stats once per second.
`capture on` switches to binary packets; `capture off` restores text mode. The
capture queue never blocks the audio task.

| Offset | Type | Value |
| --- | --- | --- |
| 0 | 4 bytes | ASCII MANC |
| 4 | uint8 | Version 1 |
| 5 | uint8 | Two channels |
| 6 | uint16 LE | 32 frames |
| 8 | uint32 LE | Audio block sequence, wraps modulo 2^32 |
| 12 | uint32 LE | Capture queue drops |
| 16 | uint32 LE | CRC-32 of the 128-byte PCM payload |
| 20 | 64 x int16 LE | Primary/reference interleaved PCM |

Packets are 148 bytes at 500/second: 74,000 bytes/second versus the raw
92,160-byte/second payload limit of 921600-baud 8-N-1 UART. Adapter overhead can
still cause drops. Corrupt/discontinuous recordings are rejected. Capture is
microphone input, not a clean target or a recording of the processed DAC output.
