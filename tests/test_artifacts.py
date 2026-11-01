"""Published metadata should retain the exact bytes that were hashed."""
import hashlib
import json
from pathlib import Path
import unittest


class ArtifactTests(unittest.TestCase):
    def test_exported_artifact_hashes(self):
        root = Path(__file__).resolve().parents[1] / "results"
        hashes = json.loads((root / "SHA256SUMS.json").read_text())
        for name, expected in hashes.items():
            with self.subTest(artifact=name):
                data = (root / name).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected)
                json.loads(data)
