"""Small local console showing actual ESP metrics; only pyserial is required."""
import json
import math
import select
import sys
import time
from tools.device import open_port

MODES = ("Original", "Reference", "DSP", "Hybrid ML")


def dbfs(value):
    return 20*math.log10(max(float(value), 1e-9))


def format_stats(s):
    mode = MODES[int(s.get("mode", 3)) % 4]
    return (f"{mode} | {'MUTED' if s.get('muted', True) else 'PLAYING'} | gain {s.get('gain', 0):.3f} | "
            f"mic P {dbfs(s.get('primary_rms', 0)):.0f} / R {dbfs(s.get('reference_rms', 0)):.0f} dBFS | "
            f"DSP peak {s.get('max_dsp_us', 0)} us | overruns {s.get('rx_overflows', 0)} | "
            f"I/O {s.get('io_errors', 0)} | {s.get('status', 'waiting')}")


def key_command(key, state):
    if key in "123" and len(key) == 1:
        return {"1": "mode primary", "2": "mode dsp", "3": "mode hybrid"}[key]
    if key == "d":
        return "demo"
    if key == "m":
        return "mute off" if state.get("muted", True) else "mute on"
    if key in ("+", "-"):
        gain = min(0.25, max(0, float(state.get("gain", 0.05))+(0.025 if key == "+" else -0.025)))
        return f"gain {gain:.3f}"
    if key == "r":
        return "reset"
    return None


def run(port):
    print("\nMOUNAM - live hardware console")
    print("d Start | 1 Original | 2 DSP | 3 Hybrid | m Mute | +/- Volume | r Reset | q Quit and mute")
    print("Model: synthetic demo. This display does not invent SNR/STOI/PESQ scores.")
    print("Use a headphone amplifier or powered line input, initially at minimum volume.\n")
    state = {}
    terminal = None
    if sys.stdin.isatty():
        import termios
        import tty
        terminal = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    try:
        with open_port(port, 921600) as connection:
            connection.write(b"capture off\nstats\n")
            pending = bytearray()
            last_stats = time.monotonic()
            try:
                while True:
                    pending.extend(connection.read(connection.in_waiting or 1))
                    while b"\n" in pending:
                        raw, _, remaining = pending.partition(b"\n"); pending = bytearray(remaining)
                        try:
                            message = json.loads(raw.decode("utf-8"))
                        except (ValueError, UnicodeError):
                            continue
                        if message.get("type") == "stats":
                            state = message
                            last_stats = time.monotonic()
                            print("\r\033[2K"+format_stats(state), end="", flush=True)
                        elif message.get("error"):
                            print("\nBoard:", message["error"])
                    if len(pending) > 4096:
                        pending.clear()
                    if time.monotonic()-last_stats > 5:
                        print("\nNo device stats yet. Press RESET once; confirm the UART USB socket and port.")
                        last_stats = time.monotonic()
                    if select.select([sys.stdin], [], [], 0)[0]:
                        key = sys.stdin.read(1).lower()
                        if key in ("q", "\x03", ""):
                            break
                        command = key_command(key, state)
                        if command:
                            connection.write((command+"\n").encode())
            finally:
                connection.write(b"mute on\n"); connection.flush()
    except KeyboardInterrupt:
        pass
    finally:
        if terminal is not None:
            import termios
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, terminal)
        print("\nConsole closed. Reopen with: bash flash.sh --monitor-only")
