# Validation and measurement plan

## Recorded development results

| Check | Result recorded during creation |
| --- | --- |
| Portable C++ build | GCC C++17, `-Wall -Wextra -Werror -pedantic` |
| DSP tests | I2S signed/24-bit packing, CRC, DC removal, band reconstruction, correlated-noise convergence, mute, bounded/finite output, settings limits |
| Python tests | Nine integration checks including model parity, capture integrity, split leakage, metric correctness, firmware fingerprints, image layout and serial selection |
| Sanitizers | Address/undefined behavior checks pass; local leak scanning disabled because the host prevents `/proc` thread inspection |
| Dataset/training | Seeded 90-example synthetic corpus; 60 epochs; validation selects the model |
| Software evaluation | Separate 18-example synthetic test split; real-speech metrics not computed |
| ESP32-S3 firmware compilation | ESP-IDF v5.4.3 build with explicit N16P8 configuration checks; see current PR checks |
| Physical hardware | Not connected in this session; bring-up and measurements pending |

CI explicitly verifies required N16P8 sdkconfig settings before compiling;
`esp_psram` is an explicit component dependency so its Kconfig options are loaded.
On the physical board, live `psram_bytes` telemetry confirms detected RAM.

## Version 1.1 improvements

The project is now the repository root. Legacy simulated dashboards, Wi-Fi/MQTT
code and classic-ESP32 configuration have been removed. The simple flash path
uses a CI-built merged image; SHA-256 and a firmware source fingerprint reject
corrupt or stale images before opening a serial port. CI compares this merged
image byte-for-byte against Espressif's own `merge_bin` output.

Telemetry snapshots now cross cores at 10 Hz instead of 500 Hz (98% fewer queue
copies), while audio remains 16 kHz with 2-ms processing blocks. The filter
kernel remains the validated baseline after host profiling. A host benchmark is
available through `make benchmark`; no MCU speedup or latency is inferred from it.
The on-board BOOT button starts/compares the demo and supports a one-second hold
to mute. Physical button/audio validation still needs your board.

The local sanitizer command was `ASAN_OPTIONS=detect_leaks=0 make sanitize`.
Ordinary GitHub runners can run `make sanitize` with their default leak scanner.
No memory leak verification is inferred from the local restricted-host run.

Both host and firmware jobs are tracked in
[the project PR checks](https://github.com/vasudevan016/SIH26052_DRDO_ANC/pull/1/checks).
Successful firmware runs also provide built ESP32-S3 binary artifacts. No board was flashed or
connected during these checks. The source model's original training environment
is recorded in [demo_environment.json](../models/demo_environment.json).

## Acceptance measurements

| Requirement | Method | Honest completion criterion |
| --- | --- | --- |
| Synchronized inputs | Scope WS/BCLK and capture two distinct quiet signals | WS 16 kHz, BCLK 1.024 MHz; correct L/R assignment |
| Real-time processing | Core 1 GPIO10 timing pulses and `max_dsp_us` | Worst processing time below the **2-ms block period**, zero late blocks over >=30 minutes |
| DMA continuity | `rx_overflows`, `io_errors`, drop counters | Zero during the normal standalone audio test |
| Physical latency | Electrical stimulus and dual-channel oscilloscope/audio interface | Measure input-to-analog-output delay; report median, p95 and maximum |
| Speech quality | Source-disjoint real clean/noisy pairs and real acoustic test | Report SNR, SI-SDR, STOI, PESQ by noise type and input SNR |
| Target scores | Same held-out paired corpus and stated protocol | Evaluate SNR >15 dB, STOI >0.85 and PESQ >2.5; do not assume they hold |
| Output behavior | Dummy load/headphone amplifier and scope before listening | Correct channel output, mute/ramp, no clipped/unstable output |
| Power | Inline current/power meter at the chosen supply | Idle/audio/peak W or mW, including DAC and amplifier |
| Cost | Actual part and assembly quotations | Separate present prototype cost from estimated production cost |

The 2-ms block, three DMA buffers, converter filters, buffering and any primary
delay all contribute to physical latency. `max_dsp_us` measures the call to the
DSP engine; it does **not** include microphone conversion, RX accumulation,
DMA queueing, DAC conversion or headphone amplifier delay. A sub-5-ms DSP claim
does not establish a sub-5-ms acoustic path. Use both measurements separately.

To measure electrical latency without an expensive calibrated acoustic setup,
use a controlled shared trigger/reference recording and record DAC line output
through an appropriate line-input interface. Establish clock alignment and
conversion delay in the measurement apparatus. A single unsynchronized USB
recording is insufficient to prove a millisecond budget. Acoustic latency and
hearing-protection performance require additional calibrated equipment.

## A practical demonstration sequence

1. Verify input RMS, silence on startup, correct L/R channels, DAC mute wiring,
   and quiet output into a powered line input or headphone amplifier.
2. Record quiet speech, separate quiet noise, and a dual-mic noisy bench take.
   Keep the primary near the speaker and reference near the background source.
3. Compare primary, DSP and hybrid modes at the same digital and analog gain.
   Record failures as well as improvements; listen for removed consonants,
   pumping, metallic sound and speech cancellation.
4. Repeat with stationary, modulated and recorded transient noise at low playback
   levels, then with a different source position and held-out speaker.
5. Run the paired software evaluation and a separately identified hardware
   output recording. Preserve raw inputs, processing mode, model ID, gains,
   source layout, firmware commit and measurement setup.

Do not perform human tests using real gunfire, explosions or hazardous playback
levels. This device's electronic attenuation is not certified ear protection.
Software cannot reconstruct information lost when a microphone clips.

## Serial protocol details

The default application UART is UART0 at 921600, 8-N-1. Text mode emits real JSON
stats once per second and accepts newline-terminated commands. `capture on`
temporarily replaces text telemetry with binary packets; `capture off` restores
text mode. Captured microphone audio is sensitive user data; files stay local.

| Offset | Type | Meaning |
| --- | --- | --- |
| 0 | 4 bytes | ASCII `MANC` |
| 4 | uint8 | Version = 1 |
| 5 | uint8 | Channels = 2 |
| 6 | uint16 LE | Frames = 32 |
| 8 | uint32 LE | Audio block sequence, wraps modulo 2^32 |
| 12 | uint32 LE | Cumulative capture queue drops |
| 16 | uint32 LE | Standard CRC-32 of the following 128 PCM bytes |
| 20 | 64 x int16 LE | Interleaved primary/reference samples |

Total 148 bytes, up to 500 packets/second = 74,000 bytes/second, below the
92,160-byte/second raw payload capacity of 921600-baud 8-N-1 UART. Adapter/host
overheads can still cause drops. The audio task enqueues without waiting; slow
capture cannot block DSP. Capture covers microphone inputs, not the processed DAC
output. Ground-truth quality and end-to-end latency need the separate methods
above.

Any I2S read/write failure or RX queue overflow latches an audio fault and asserts
DAC MUTE. Press board RESET after resolving the fault. `reset` is a filter reset
and mute command during a healthy stream; it is not an I2S fault recovery command.
