import ctypes as ct
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
import numpy as np
from ml.native import extract, enhance, library, ROOT
from ml.train import predict, read_manifest
from tools.protocol import Parser, HEADER
from tools.evaluate import snr, si_sdr, evaluate_pair
from tools.audio import read_wav, write_wav


class WorkflowTests(unittest.TestCase):
    def test_capture_fragments_corruption_and_resync(self):
        payload = bytes(range(128))
        packet = HEADER.pack(b"MANC", 1, 2, 32, 17, 0, zlib.crc32(payload))+payload
        parser = Parser()
        records = []
        stream = b"boot log\n"+packet+b"junk"+packet
        for start in range(0, len(stream), 7):
            records.extend(parser.feed(stream[start:start+7]))
        self.assertEqual(records, [(17, 0, payload)]*2)
        corrupt = bytearray(packet); corrupt[-1] ^= 1
        self.assertEqual(parser.feed(corrupt+packet), [(17, 0, payload)])
        self.assertEqual(parser.crc_errors, 1)
        parser.feed(b"x"*65536)
        self.assertLessEqual(len(parser.buffer), 3)

    def test_native_features_and_padded_replay(self):
        rng = np.random.default_rng(1)
        audio = rng.normal(0, 0.02, (16101, 2)).astype(np.float32)
        features = extract(audio)
        self.assertEqual(features.shape, (504, 8))
        self.assertTrue(np.isfinite(features).all())
        self.assertTrue((features[:, 2] >= -1).all())
        self.assertTrue((features <= 1.00001).all())
        output = enhance(audio)
        self.assertEqual(output.shape, (16101,))
        self.assertTrue((np.abs(output) <= 0.25).all())
        with self.assertRaises(ValueError):
            enhance(np.zeros((32, 1)))

    def test_model_export_matches_embedded_prediction(self):
        path = ROOT/"models/demo_model.json"
        if not path.exists():
            self.skipTest("Run the demo model training before model parity test.")
        model = json.loads(path.read_text())
        lib = library()
        # A locally retrained non-demo model deliberately replaces the demo header.
        if lib.mounam_model_id().decode() != model["model_id"]:
            self.skipTest("A different locally trained model is compiled.")
        rng = np.random.default_rng(26052)
        x = rng.uniform(0, 1, (100, 8)).astype(np.float32)
        x[:, 2] = rng.uniform(-1, 1, 100)
        params = [np.asarray(p, dtype=np.float64) for p in model["parameters"]]
        _, expected = predict(x, params)
        actual = [lib.mounam_predict(np.ascontiguousarray(row)) for row in x]
        np.testing.assert_allclose(actual, expected, rtol=2e-5, atol=2e-6)

    def test_metrics_cannot_be_faked_by_turning_down_volume(self):
        rng = np.random.default_rng(9)
        clean = rng.normal(0, 0.02, 16000)
        noisy = clean+rng.normal(0, 0.02, 16000)
        a = evaluate_pair(clean, noisy, noisy*0.05, 0.05)
        b = evaluate_pair(clean, noisy, noisy*0.005, 0.05)
        self.assertAlmostEqual(a["input_snr_db"], a["output_snr_db"], places=5)
        self.assertLess(b["output_snr_db"], a["output_snr_db"]+1)
        self.assertAlmostEqual(si_sdr(clean, noisy), si_sdr(clean, noisy*0.1), places=5)
        self.assertGreater(snr(clean, clean), 60)

    def test_audio_roundtrip_and_no_ground_truth_from_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"pair.wav"
            audio = np.column_stack([np.zeros(320), np.full(320, 0.125)])
            write_wav(path, audio)
            restored = read_wav(path)
            np.testing.assert_allclose(restored, audio, atol=4e-5)
            self.assertEqual(read_wav(path, 1).shape, (320,))

    def test_source_leakage_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"manifest.jsonl"
            rows = [dict(path="x.npz", split=s, speaker_id="same-speaker", noise_id=s,
                         sha256="irrelevant") for s in ("train", "test")]
            path.write_text("\n".join(json.dumps(r) for r in rows))
            with self.assertRaisesRegex(ValueError, "leaks"):
                read_manifest(path)


if __name__ == "__main__":
    unittest.main()
