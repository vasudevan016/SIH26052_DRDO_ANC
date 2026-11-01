# Flash, calibrate and compare

1. With USB power disconnected, wire the parts using [WIRING.md](WIRING.md).
2. Connect the board's **UART USB socket** with a data cable.
3. Open an Ubuntu terminal and run:

```bash
sudo apt install -y git python3-venv
git clone https://github.com/vasudevan016/SIH26052_DRDO_ANC.git mounam-final
cd mounam-final
bash flash.sh
```

The script verifies and flashes the included trained-model firmware, then opens
its console. ESP-IDF, Arduino IDE, NumPy and model training are not needed here.

4. Keep the headphone amplifier at minimum volume. Press **c** and keep quiet
   for three seconds while the background noise continues. Output stays muted.
5. Press **d** to start. Press **1 / 3** for original / neural audio at equal gain.
6. Press **m** to mute; **q** mutes and exits.

For a visual console, exit with **q**, then run:

```bash
python3 -m tools.dashboard
```

Use Chrome/Edge at the printed localhost URL. Click Connect USB device and select
the same board. Close other serial programs first. The dashboard shows actual
hardware telemetry and separate recorded software results.

Without a computer, tap **BOOT** to start or compare original/neural audio. Hold
BOOT for one second to mute. Reset starts muted and clears acoustic calibration.
No wireless network is needed for operation.

| Problem | Fix |
| --- | --- |
| Existing clone | Save local edits, then `git pull --ff-only` from that clone |
| Missing `venv` / `ensurepip` | `sudo apt install python3-venv`, retry |
| Several serial boards | `bash flash.sh --port /dev/ttyUSB0` using your board's port |
| Permission denied | `sudo usermod -aG dialout "$USER"`, log out/in, retry |
| Cannot enter flashing mode | Close serial programs; hold BOOT, tap RESET, release BOOT, retry |
| Flash connection unreliable | Try `bash flash.sh --baud 115200` and a data-capable USB cable |
| Reopen console | `bash flash.sh --monitor-only` |
| No mic level | Check 3.3-V power, SD wiring and opposite L/R straps |
| No output | Check mute, headphone amplifier, DAC MUTE/format and analog wiring |
| Source fingerprint mismatch | Use an unchanged clone or rebuild after source edits using [BUILD.md](BUILD.md) |

This image targets **ESP32-S3-WROOM-1 N16P8**. The UDA1334A requires a headphone
amplifier for proper wired-earphone output. Test at ordinary sound levels;
physical latency and acoustic safety need separate bench measurements.
