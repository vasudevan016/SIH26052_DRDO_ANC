"""Read real board metrics, send controls, or capture primary/reference WAV over USB-UART."""
import argparse
import json
from pathlib import Path
import time
import wave
from tools.protocol import Parser


def open_port(port, baud):
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt to enable serial commands.") from exc
    connection = serial.Serial(port=None, baudrate=baud, timeout=0.1, write_timeout=1)
    connection.dtr = False
    connection.rts = False
    connection.port = port
    connection.open()
    return connection


def capture(connection, args):
    target_frames = round(args.seconds*16000)
    if not 0 < args.seconds <= 3600:
        raise ValueError("Capture duration must be >0 and <=3600 seconds.")
    if args.output.exists() or args.output.with_suffix(".json").exists():
        raise ValueError("Capture output or metadata already exists; choose a new filename.")
    # Capturing microphones needs no headphone output.
    connection.write(b"mute on\n")
    time.sleep(0.1)
    connection.reset_input_buffer()
    parser = Parser()
    previous, first_drop, last_drop = None, None, 0
    parts, frames, lost = [], 0, 0
    deadline = time.monotonic()+args.seconds+10
    connection.write(b"capture on\n")
    try:
        while frames < target_frames:
            if time.monotonic() > deadline:
                raise TimeoutError("Capture stalled. Check baud, UART port and stats; no WAV was written.")
            for sequence, drops, payload in parser.feed(connection.read(4096)):
                if previous is not None and sequence != (previous+1) & 0xffffffff:
                    missing = (sequence-previous-1) & 0xffffffff
                    if missing > 16000*3600//32:
                        raise RuntimeError("Board restarted or packet sequence is invalid.")
                    lost += missing
                    raise RuntimeError(f"Lost {missing} audio blocks; capture rejected. Reduce serial load/check adapter.")
                if first_drop is None:
                    first_drop = drops
                if drops != first_drop or parser.crc_errors:
                    raise RuntimeError("Corrupt or dropped packets; capture rejected, no WAV was written.")
                previous, last_drop = sequence, drops
                parts.append(payload)
                frames += 32
    finally:
        connection.write(b"capture off\n")
        connection.flush()
    raw = b"".join(parts)[:target_frames*4]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.output), "wb") as file:
        file.setnchannels(2); file.setsampwidth(2); file.setframerate(16000); file.writeframes(raw)
    metadata = dict(sample_rate=16000, channels=["primary", "reference"], frames=len(raw)//4,
        source="ESP32-S3 INMP441 pair", capture="PCM16 truncation of 24-bit microphone samples",
        sequence_gaps=lost, crc_errors=parser.crc_errors, first_device_drops=first_drop,
        final_device_drops=last_drop, clean_ground_truth=False)
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2)+"\n")
    print(json.dumps({"wav": str(args.output), **metadata}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="USB-UART connector, usually /dev/ttyUSB0.")
    parser.add_argument("--baud", type=int, default=921600)
    sub = parser.add_subparsers(dest="action", required=True)
    monitor = sub.add_parser("monitor")
    monitor.add_argument("--seconds", type=float, default=15)
    command = sub.add_parser("command")
    command.add_argument("text", help="Quote a complete firmware command, e.g. 'mute off'.")
    record = sub.add_parser("capture")
    record.add_argument("--seconds", type=float, default=10)
    record.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with open_port(args.port, args.baud) as connection:
        # Recover the text protocol after an interrupted prior capture.
        connection.write(b"capture off\n")
        time.sleep(0.1)
        connection.reset_input_buffer()
        if args.action == "capture":
            capture(connection, args)
        else:
            text = args.text if args.action == "command" else "stats"
            if "\n" in text or "\r" in text or len(text) > 90 or text == "capture on":
                parser.error("Use a single text command; use the capture subcommand for binary capture.")
            connection.write(text.encode("ascii")+b"\n")
            end = time.monotonic()+(args.seconds if args.action == "monitor" else 1.5)
            while time.monotonic() < end:
                line = connection.readline()
                if line:
                    print(line.decode("utf-8", errors="replace").rstrip())


if __name__ == "__main__":
    main()
