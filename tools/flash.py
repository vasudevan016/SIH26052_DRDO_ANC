"""Flash the bundled ESP32-S3 N16P8 image without installing the development SDK."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from tools.package_firmware import ROOT, verify


def choose_port(requested, ports):
    if requested:
        return requested
    candidates = [p.device for p in ports if p.vid is not None and
                  (Path(p.device).name.startswith(("ttyUSB", "ttyACM")) or p.device.startswith("COM"))]
    if len(candidates) != 1:
        listing = "\n".join(f"  {p.device}: {p.description}" for p in ports) or "  No USB serial device found."
        raise ValueError("Connect the board's UART USB socket. If several devices are connected, select one:\n"
                         +listing+"\nExample: bash flash.sh --port /dev/ttyUSB0")
    return candidates[0]


def flash_command(port, baud, image, metadata):
    settings = metadata["flash_settings"]
    return [sys.executable, "-m", "esptool", "--chip", "esp32s3", "--port", port, "--baud", str(baud),
            "--before", "default_reset", "--after", "hard_reset", "write_flash",
            "--flash_mode", settings["flash_mode"], "--flash_freq", settings["flash_freq"],
            "--flash_size", settings["flash_size"], "0x0", str(image)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Auto-detected when exactly one USB serial board is connected.")
    parser.add_argument("--baud", type=int, choices=[115200, 230400, 460800, 921600], default=460800)
    parser.add_argument("--no-monitor", action="store_true", help="Exit after flashing.")
    parser.add_argument("--monitor-only", action="store_true", help="Open controls without flashing again.")
    parser.add_argument("--verify-only", action="store_true", help="Check the bundled image and source fingerprints without touching hardware.")
    parser.add_argument("--dry-run", action="store_true", help="Show the flashing command without opening a serial port; supply --port.")
    args = parser.parse_args()
    try:
        image = metadata = None
        if not args.monitor_only or args.verify_only:
            image, metadata = verify(ROOT/"firmware/prebuilt")
            print(f"Verified N16P8 firmware: {metadata['bytes']:,} bytes; source {metadata['source_commit'][:12]}.")
        if args.verify_only:
            return
        if args.dry_run:
            if not args.port or args.monitor_only:
                parser.error("Dry run requires --port and a normal flash operation.")
            print(json.dumps(flash_command(args.port, args.baud, image, metadata)))
            return
        from serial.tools import list_ports
        port = choose_port(args.port, list_ports.comports())
        if not args.monitor_only:
            print(f"Flashing ESP32-S3 on {port}. Keep the USB cable connected.")
            result = subprocess.run(flash_command(port, args.baud, image, metadata))
            if result.returncode:
                raise RuntimeError("Flash failed. Close other serial programs. Hold BOOT, tap RESET, release BOOT, "
                                   "then retry. For permission errors: sudo usermod -aG dialout \"$USER\", then log out/in.")
            print("Firmware flashed and verified by esptool. Output starts muted.")
        if not args.no_monitor:
            from tools.console import run
            run(port)
    except (OSError, ValueError, RuntimeError, KeyError, ImportError) as exc:
        parser.exit(1, f"\n{exc}\n")


if __name__ == "__main__":
    main()
