# Mounam - offline speech enhancement on ESP32-S3

**SIH26052 · Idea 180588 · Team Mounam**

Two INMP441 microphones capture speech and background noise. An ESP32-S3 N16P8
processes audio locally using adaptive filtering and a tiny ML controller. A
UDA1334A sends enhanced audio to a headphone amplifier. No Wi-Fi or cloud is used.

## Flash your ESP in three commands

Connect the board's **UART USB socket** with a data cable, then run on Ubuntu:

```bash
git clone https://github.com/vasudevan016/SIH26052_DRDO_ANC.git mounam-anc
cd mounam-anc
bash flash.sh
```

The script installs only the small flashing tools, finds a single connected USB
serial board, checks the bundled firmware, flashes it and opens the live console.
**No Arduino IDE or ESP-IDF installation is required.** If Python reports that
venv is unavailable, run `sudo apt install python3-venv` and retry.

Output starts **muted**. Complete the [wiring](docs/WIRING.md) and keep the
headphone amplifier at minimum volume before pressing **d** in the console.

| Console key | Action |
| --- | --- |
| **d** | Start the hybrid audio demo at low gain |
| **1 / 2 / 3** | Original / adaptive DSP / hybrid ML, at the same gain |
| **m** | Mute or unmute |
| **+ / -** | Adjust output gain |
| **q** | Mute and exit |

After flashing, **tap the board's BOOT button** to start or switch original /
hybrid audio. **Hold BOOT for one second** to mute. This also works with USB power
and no computer attached. Press RESET to restart with output muted.

Reopen the console with `bash flash.sh --monitor-only`. If several serial devices
are connected, use `bash flash.sh --port /dev/ttyUSB0` with your board's port.

## Your hardware connections

Power off before wiring. Both microphones share the clock and data wires.

| ESP32-S3 GPIO | Connect to |
| --- | --- |
| **4** | Both mic SCK and DAC BCLK |
| **5** | Both mic WS and DAC WSEL |
| **6** | Both mic SD pins; add 100-kohm pull-down to GND |
| **7** | DAC DIN |
| **8** | DAC MUTE; add 10-kohm pull-up to 3.3 V |
| **3V3 / GND** | Mic power / common ground; use the DAC board's documented supply |

Primary mic **L/R -> GND**; reference mic **L/R -> 3V3**.
**DAC L/R -> stereo headphone amplifier -> wired earphones.** The DAC output is
line level; an amplifier is needed for proper 32-ohm earphone output. See the
[complete pin-by-pin guide](docs/WIRING.md) for DAC format and supply details.

## What is ready, and what to measure

The source includes actual I2S/DMA audio, Core 1 DSP, a learned speech-presence
controller, safe startup/mute, live hardware metrics, training, capture and
paired evaluation. Firmware is built and checked in CI; bundled images include
their SHA-256 and source fingerprint. Source changes invalidate an old image.

The shipped ML model is a **synthetic integration demo**. Real speech scores,
physical latency, power and BOM must be measured for your final submission.
This prototype enhances microphone audio; acoustic hearing protection requires
separate hardware and validation.

| Need more? | Guide |
| --- | --- |
| First flash or a flashing problem | [Simple quick start](docs/QUICKSTART.md) |
| Demonstration for judges | [90-second demo and evidence](docs/DEMO.md) |
| Train with real speech/noise | [Training](docs/TRAINING.md) |
| Compile or modify firmware | [Developer build](docs/BUILD.md) |
| Architecture and measurements | [Architecture](docs/ARCHITECTURE.md), [validation](docs/VALIDATION.md) |
