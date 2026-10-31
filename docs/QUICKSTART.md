# Flash and run: the short guide

1. Wire the audio parts with USB power disconnected using [WIRING.md](WIRING.md).
2. Connect the ESP32-S3 board's **UART USB socket** using a data cable.
3. On Ubuntu, open Terminal and paste:

```bash
git clone https://github.com/vasudevan016/SIH26052_DRDO_ANC.git mounam-anc
cd mounam-anc
bash flash.sh
```

The script checks and flashes the included firmware, then opens the live console.
You do **not** need ESP-IDF, Arduino IDE, NumPy or model training for this step.

4. Keep the headphone amplifier volume at minimum. Output starts muted.
5. Press **d** to start; press **1 / 3** to compare original / enhanced audio.
   Press **m** to mute; **q** mutes and exits.

Without the computer: tap **BOOT** to start or compare; hold BOOT for one second
to mute. Press RESET to reboot with output muted. The node needs only USB power
while operating; a network connection is unnecessary.

## If something stops you

| Problem | Do this |
| --- | --- |
| `venv` / `ensurepip` unavailable | `sudo apt install python3-venv`, then `bash flash.sh` |
| Repository folder already exists | Open your existing clone, save any local changes, then `git pull --ff-only` |
| Several serial devices | `bash flash.sh --port /dev/ttyUSB0` using your board's listed port |
| Port permission denied | `sudo usermod -aG dialout "$USER"`, log out/in, retry |
| Cannot connect while flashing | Close other serial programs. Hold BOOT, tap RESET, release BOOT, retry. Try `bash flash.sh --baud 115200` |
| No microphone levels | Check mic power, shared SD, and opposite L/R straps |
| No headphone audio | Check mute, amplifier, DAC MUTE/format and analog wiring |
| Need controls again | `bash flash.sh --monitor-only` |
| Firmware/source fingerprint mismatch | Use an unchanged clone, or follow [BUILD.md](BUILD.md) after editing code |

Only an **ESP32-S3 N16P8** is supported by this image. A stereo headphone amplifier
is needed between the UDA1334A line output and wired earphones. Test at ordinary
sound levels. Actual speech quality and physical latency need bench measurement.
