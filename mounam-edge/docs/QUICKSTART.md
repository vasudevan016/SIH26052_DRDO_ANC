# Ubuntu terminal setup and first audio

All commands assume Ubuntu/Linux and a board labelled **ESP32-S3 N16P8**.
The project uses **ESP-IDF v5.4.3**, not the old root PlatformIO/Arduino project.
Internet access is needed to install/build dependencies initially; the flashed
audio node works without a computer or network when powered independently.

## 1. Get the new project

```bash
git clone --branch codex/mounam-edge-from-scratch --single-branch https://github.com/vasudevan016/SIH26052_DRDO_ANC.git
cd SIH26052_DRDO_ANC/mounam-edge
```

If you already cloned this repository, first save any local work. Fetch the
remote branch and switch to it, then enter `mounam-edge`. Do not discard changes
or build the root `src/main.cpp` by mistake.

## 2. Install the ESP-IDF toolchain once

```bash
sudo apt update
sudo apt install -y git wget flex bison gperf python3 python3-pip python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0 build-essential
mkdir -p "$HOME/esp"
git clone --branch v5.4.3 --recursive https://github.com/espressif/esp-idf.git "$HOME/esp/esp-idf-v5.4.3"
cd "$HOME/esp/esp-idf-v5.4.3"
./install.sh esp32s3
```

In every terminal used to build/flash, activate it:

```bash
. "$HOME/esp/esp-idf-v5.4.3/export.sh"
idf.py --version
```

Use a fresh directory name if that installation path already contains a different
SDK. Follow Espressif's [official setup guide](https://docs.espressif.com/projects/esp-idf/en/v5.4.3/esp32s3/get-started/linux-macos-setup.html)
for distribution-specific prerequisites.

## 3. Build and flash

Return to your clone's `mounam-edge/firmware` directory:

```bash
cd /path/to/SIH26052_DRDO_ANC/mounam-edge/firmware
idf.py set-target esp32s3
python ../tools/check_sdkconfig.py sdkconfig
idf.py build
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Choose the port that appeared when connecting the board's **USB-UART** socket.
For example:

```bash
idf.py -p /dev/ttyUSB0 -b 460800 flash
idf.py -p /dev/ttyUSB0 monitor
```

The flash baud is independent of the application's **921600-baud** serial
interface. IDF monitor reads its baud from sdkconfig. Exit monitor with **Ctrl+]**.
Only one monitor/capture program can own the serial port at a time.

If the port reports permission denied:

```bash
sudo usermod -aG dialout "$USER"
```

Log out and back in before retrying. If automatic flashing fails, hold BOOT,
tap RESET, release BOOT, and retry the flash command. Do not erase flash as a
routine troubleshooting step.

`sdkconfig.defaults` selects 16-MB flash, octal 80-MHz PSRAM, 240-MHz CPU and a
1-kHz scheduler tick. Change pins through `idf.py menuconfig` under **Mounam board
wiring**. The checked-in defaults are for N16P8; changing the board requires a
configuration review.

## 4. Install the local host tools

Use a separate terminal and virtual environment for the host tools so they do
not modify ESP-IDF's own Python environment. From `mounam-edge`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
make test
```

If `make` or `g++` is missing, install `build-essential`. The native DSP build
supports Linux and WSL; it does not require a GPU, PyTorch or TensorFlow.

## 5. Verify microphones while output stays muted

Close IDF monitor before using these commands:

```bash
python -m tools.device --port /dev/ttyUSB0 monitor --seconds 10
python -m tools.device --port /dev/ttyUSB0 command 'stats'
```

Expect `status: streaming`, `muted: true`, `psram_bytes: 8388608`, and RMS values for both microphones.
Speak near each mic separately. The primary is the left I2S slot and reference
is the right. A channel stuck at zero suggests L/R, shared SD or power wiring
needs correction. A healthy run should keep `rx_overflows`, `io_errors` and
`late_blocks` at zero.

The shipped model reports `model: synthetic_demo`. It is a learned integration
demo, not a model validated on human speech or defence noises.

## 6. First output through a powered line input or headphone amplifier

Keep earphones off your ears for the first output test. With the output amplifier
at minimum, set a small gain and check primary audio before the filters:

```bash
python -m tools.device --port /dev/ttyUSB0 command 'gain 0.05'
python -m tools.device --port /dev/ttyUSB0 command 'mode primary'
python -m tools.device --port /dev/ttyUSB0 command 'mute off'
```

After verifying clean, quiet output, introduce quiet background noise and compare
at the **same gain**:

```bash
python -m tools.device --port /dev/ttyUSB0 command 'mode dsp'
python -m tools.device --port /dev/ttyUSB0 command 'mode hybrid'
python -m tools.device --port /dev/ttyUSB0 command 'mute on'
```

`hold on` freezes NLMS learning for speech-leakage diagnosis. `reset` resets the
filters and mutes output. `delay N` changes primary alignment in samples; start
at zero. Commands are applied on a block boundary. `accepted` means queued;
inspect the next stats line for the actual setting.

## 7. Capture real dual-microphone input

```bash
python -m tools.device --port /dev/ttyUSB0 capture --seconds 10 --output captures/bench-01.wav
python -m tools.replay captures/bench-01.wav captures/bench-01-hybrid.wav --mode hybrid
```

Capture mutes playback, writes a stereo 16-kHz WAV plus metadata, and rejects
corrupt or discontinuous input. Channels are primary/reference, **not** noisy/
clean ground truth. Replay uses the same C++ DSP as the firmware. Audio is not
automatically played. Close other serial programs if packets drop.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No new Wi-Fi SSID | Expected: this implementation does not start Wi-Fi |
| No audio | Startup mute, physical amplifier volume, DAC MUTE pin/format, both mic RMS values |
| One input silent | L/R straps must be opposite; both SD pins go to GPIO6 |
| Buzz/distortion | DAC feeding a headphone load directly, ground/clock wiring, clipping counters |
| Speech disappears | Reference hears too much speech; relocate it, compare `hold on` and primary mode |
| `fault_reboot_required` | Output is muted; fix clocks/power/CPU load, then press RESET |
| PSRAM boot failure | Confirm the actual module is N16P8 and the SDK target/configuration is ESP32-S3 |
| Serial text is garbled | Use UART socket and 921600 baud; reset-ROM messages can briefly use another baud |
| Capture rejects blocks | Close other serial users; use a data cable and a USB-UART adapter supporting 921600 |

No physical board is connected to this development session. Firmware compilation
and host tests do not substitute for the above bring-up and timing measurements.
