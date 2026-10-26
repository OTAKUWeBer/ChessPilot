import sys
from pathlib import Path
import unittest

src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from utils.cpu_features import detect_os, detect_cpu_info, format_bytes
from utils.downloader import choose_best_asset


class TestCpuFeaturesAndDownloader(unittest.TestCase):
    def test_detect_os(self):
        system = detect_os()
        self.assertIn(system, ["windows", "linux", "macos", "unknown"])

    def test_detect_cpu_info(self):
        arch, vendor, flags = detect_cpu_info()
        self.assertIsInstance(arch, str)
        self.assertIsInstance(vendor, str)
        self.assertIsInstance(flags, set)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500.0 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1048576), "1.0 MB")
        self.assertEqual(format_bytes(1073741824), "1.0 GB")

    def test_choose_best_asset_windows_x86_64(self):
        mock_assets = [
            {"name": "stockfish-windows-x86-64-avx2.zip", "browser_download_url": "http://example.com/avx2.zip"},
            {"name": "stockfish-windows-x86-64-sse41-popcnt.zip", "browser_download_url": "http://example.com/sse41.zip"},
            {"name": "stockfish-windows-x86-64.zip", "browser_download_url": "http://example.com/base.zip"},
            {"name": "stockfish-ubuntu-x86-64-avx2.tar", "browser_download_url": "http://example.com/linux_avx2.tar"},
        ]
        
        # Test machine with avx2
        flags_avx2 = {"avx2", "bmi2", "sse4_1", "popcnt"}
        best = choose_best_asset(mock_assets, "windows", "x86_64", "intel", flags_avx2)
        self.assertIsNotNone(best)
        self.assertEqual(best["name"], "stockfish-windows-x86-64-avx2.zip")

        # Test machine with only sse4_1
        flags_sse41 = {"sse4_1", "popcnt"}
        best_sse41 = choose_best_asset(mock_assets, "windows", "x86_64", "intel", flags_sse41)
        self.assertIsNotNone(best_sse41)
        self.assertEqual(best_sse41["name"], "stockfish-windows-x86-64-sse41-popcnt.zip")


if __name__ == "__main__":
    unittest.main()
