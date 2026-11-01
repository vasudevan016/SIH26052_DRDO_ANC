# Mounam 2.0 - AI-assisted dual-microphone speech enhancement

**SIH26052 · Idea 180588 · Team Mounam · ESP32-S3 N16P8**

A complete offline firmware and training project for your two INMP441 microphones
and UDA1334A DAC. The ESP32-S3 runs normalized LMS, a human-speech-trained voice
controller and an **eight-band neural suppression model with int8 weights**.
Trained weights, evaluation reports, a live USB dashboard and ready-to-flash
firmware are included. Audio inference runs entirely on the MCU.

## Flash - no Arduino IDE or ESP-IDF needed

Connect the ESP32-S3 board's **UART USB socket** with a data cable. On Ubuntu:

```bash
sudo apt install -y git python3-venv
git clone https://github.com/vasudevan016/SIH26052_DRDO_ANC.git mounam-final
cd mounam-final
bash flash.sh
```

The script creates a small local flashing environment, verifies the image/source
fingerprints, finds a single USB serial board, flashes it and opens the console.
For an existing clone, save local edits, then run `git pull --ff-only` from that
clone before flashing. Details: [short guide](docs/QUICKSTART.md).

Output starts **muted**. With a headphone amplifier connected at minimum volume:

| Key | What to do |
| --- | --- |
| **c** | Keep quiet for three seconds while the background path is calibrated |
| **d** | Start enhanced audio; learned calibration is preserved |
| **1 / 2 / 3** | Compare original / classical DSP / neural hybrid at the same gain |
| **m** | Mute or unmute |
| **+ / -** | Adjust digital output gain |
| **q** | Mute and exit |

The **BOOT button** starts audio or toggles original/neural modes. Hold BOOT for
one second to mute. This works on USB power without a computer or network.
Resetting/power cycling starts muted and clears the acoustic calibration.

## Exact wiring

Disconnect power before wiring. Use **GPIO labels**, not header position numbers.

| ESP32-S3 | Primary INMP441 | Reference INMP441 | UDA1334A |
| --- | --- | --- | --- |
| GPIO4 | SCK | SCK | BCLK |
| GPIO5 | WS | WS | WSEL / WS |
| GPIO6 | SD | SD | - |
| GPIO7 | - | - | DIN |
| GPIO8 | - | - | MUTE, active high |
| 3V3 | VDD and exposed CHIPEN | VDD and exposed CHIPEN | Supply according to the breakout's label |
| GND | GND and **L/R** | GND | GND |
| 3V3 | - | **L/R** | - |

Tie the two SD pins together; add **100 kohms from shared SD to GND**. Add
**10 kohms from DAC MUTE to 3V3**. Both microphones use 3.3 V, never 5 V. A bare
DAC supply is 3.3 V; a regulated breakout's VIN must follow its board specification.
Use normal Philips I2S / PLL audio mode with de-emphasis off; no external MCLK.

**DAC LOUT/ROUT -> stereo headphone amplifier -> wired earphones.**
The UDA1334A is a line-output DAC; a proper amplifier is required for 32-ohm
headphones. A powered speaker/line input is an alternative for a bench demo.
See [full wiring and placement](docs/WIRING.md) for supply, decoupling and grounding.

## Optional visual dashboard

Close the terminal console with **q**, then run:

```bash
python3 -m tools.dashboard
```

Open the printed localhost URL in Chrome/Edge and click **Connect USB device**.
The page reads actual device levels, eight neural gains, DSP timing percentiles,
overrun/clip counters and model IDs. Recorded software scores are shown separately.
No account, cloud server, Wi-Fi or Bluetooth is needed.

## Real training and evidence

Two model stages are included: an 8-8-1 speech-presence controller and a 26-24-8
band-gain MLP. The latter uses 816 signed int8 weights with float32 activations,
scales and biases. Its model storage is about **1.1 kB**, plus the speech model.
Native host evaluation calls the **same C++ implementation** used on the ESP32.

The public training run uses 600 pairs from 120 human speakers, split by speaker
identity, with generated stationary, modulated, siren, wind and impulse noises.
Full attribution, archive hash, model IDs, per-example results and validation/test
reports are included. See [measured results](docs/RESULTS.md) and
[training/reproduction](docs/TRAINING.md).

This is a microphone-signal speech-enhancement prototype for the DRDO problem
statement. Continuous speech, actual defence recordings, physical end-to-end
latency, power and hearing protection need separate validation. The results are
not DRDO approval or a guarantee that every target is met.

| Further detail | Guide |
| --- | --- |
| First flash / connection problems | [Quick start](docs/QUICKSTART.md) |
| Demonstration for judges | [Demo](docs/DEMO.md) |
| Models, architecture and MCU budget | [Architecture](docs/ARCHITECTURE.md) |
| Measured scores and limitations | [Results](docs/RESULTS.md), [validation](docs/VALIDATION.md) |
| Retrain with your recordings | [Training](docs/TRAINING.md) |
| Recompile firmware | [Developer build](docs/BUILD.md) |
| Match to submitted idea | [Idea alignment](docs/IDEA_ALIGNMENT.md) |
