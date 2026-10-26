import sys
import os
import io
import zipfile
import tarfile
import tempfile
import shutil
from pathlib import Path
import unittest

src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from utils.downloader import BinaryExtractor


class TestArchiveExtraction(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_extract_zip_archive(self):
        zip_path = os.path.join(self.test_dir, "test_sf.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            # write a dummy stockfish binary inside
            binary_name = "stockfish.exe" if os.name == "nt" else "stockfish"
            zf.writestr(f"stockfish-16/{binary_name}", b"#!/bin/sh\necho stockfish\n")

        extractor = BinaryExtractor(zip_path)
        extracted_path = extractor.extract_binary()
        self.assertIsNotNone(extracted_path)
        self.assertTrue(os.path.exists(extracted_path))
        extractor._cleanup()

    def test_extract_tar_archive(self):
        tar_path = os.path.join(self.test_dir, "test_sf.tar")
        binary_name = "stockfish.exe" if os.name == "nt" else "stockfish"
        content = b"#!/bin/sh\necho stockfish\n"

        with tarfile.open(tar_path, "w") as tf:
            ti = tarfile.TarInfo(name=f"subfolder/{binary_name}")
            ti.size = len(content)
            tf.addfile(ti, io.BytesIO(content))

        extractor = BinaryExtractor(tar_path)
        extracted_path = extractor.extract_binary()
        self.assertIsNotNone(extracted_path)
        self.assertTrue(os.path.exists(extracted_path))
        extractor._cleanup()

    def test_extract_corrupt_archive(self):
        bad_path = os.path.join(self.test_dir, "corrupt.zip")
        with open(bad_path, "wb") as f:
            f.write(b"NOT A REAL ZIP FILE CONTENT")

        extractor = BinaryExtractor(bad_path)
        extracted_path = extractor.extract_binary()
        self.assertIsNone(extracted_path)


if __name__ == "__main__":
    unittest.main()
