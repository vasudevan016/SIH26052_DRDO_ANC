import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from tools.flash import choose_port, flash_command
from tools.package_firmware import package, verify, IMAGE
from tools.console import key_command, format_stats


class FlashTests(unittest.TestCase):
    def test_multiple_ports_are_not_silently_guessed(self):
        ports = [SimpleNamespace(device=f"/dev/ttyUSB{i}", vid=0x10c4, description="USB UART") for i in range(2)]
        with self.assertRaisesRegex(ValueError, "select one"):
            choose_port(None, ports)
        self.assertEqual(choose_port(None, ports[:1]), "/dev/ttyUSB0")
        self.assertEqual(choose_port("/dev/ttyUSB1", ports), "/dev/ttyUSB1")

    def test_package_layout_checksum_and_stale_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/"components/mounam_dsp/include").mkdir(parents=True)
            weights = root/"components/mounam_dsp/include/model_weights.h"
            weights.write_text('constexpr auto kProvenance = "unit_test";')
            build = root/"firmware/build"
            build.mkdir(parents=True)
            header = bytearray(128); header[0] = 0xe9; header[12] = 9
            (build/"boot.bin").write_bytes(header)
            (build/"app.bin").write_bytes(header+b"app")
            (build/"part.bin").write_bytes(b"partitions")
            (build/"flasher_args.json").write_text(json.dumps({"extra_esptool_args":{"chip":"esp32s3"},
                "flash_settings":{"flash_mode":"dio","flash_freq":"80m","flash_size":"16MB"},
                "flash_files":{"0x0":"boot.bin","0x8000":"part.bin","0x10000":"app.bin"}}))
            output = root/"firmware/prebuilt"
            package(build, output, "a"*40, root)
            image, metadata = verify(output, root)
            raw = image.read_bytes()
            self.assertEqual(raw[:128], header)
            self.assertEqual(raw[128:0x8000], b"\xff"*(0x8000-128))
            self.assertEqual(raw[0x10000:], header+b"app")
            command = flash_command("/dev/test port", 460800, image, metadata)
            self.assertIn("/dev/test port", command)  # Remains one argument; never shell text.
            self.assertEqual(command[-2:], ["0x0", str(image)])
            weights.write_text('constexpr auto kProvenance = "changed";')
            with self.assertRaisesRegex(ValueError, "sources changed"):
                verify(output, root)
            image.write_bytes(raw[:-1]+b"x")
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify(output, root)

    def test_console_controls_and_real_metrics(self):
        self.assertEqual(key_command("d", {}), "demo")
        self.assertEqual(key_command("c", {}), "calibrate")
        self.assertEqual(key_command("1", {}), "mode primary")
        self.assertEqual(key_command("m", {"muted":False}), "mute on")
        self.assertEqual(key_command("+", {"gain":0.25}), "gain 0.250")
        text = format_stats({"mode":3,"muted":True,"max_dsp_us":317,"rx_overflows":2})
        self.assertIn("317 us", text)
        self.assertIn("overruns 2", text)
        self.assertNotIn("SNR", text)


if __name__ == "__main__":
    unittest.main()
