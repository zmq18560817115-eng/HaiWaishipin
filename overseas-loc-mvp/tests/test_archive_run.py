import unittest
from pathlib import Path

from scripts.archive_run import archive_slug


class ArchiveRunTests(unittest.TestCase):
    def test_dry_run_night_pumping(self):
        result = archive_slug("night-pumping-v1", dry_run=True)
        self.assertEqual(result["slug"], "night-pumping-v1")
        self.assertTrue(any("en-localization-pack.md" in line for line in result["copied"]))

    def test_missing_slug_raises(self):
        with self.assertRaises(FileNotFoundError):
            archive_slug("does-not-exist-slug-xyz", dry_run=True)


if __name__ == "__main__":
    unittest.main()
