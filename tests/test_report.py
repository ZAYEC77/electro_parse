import tempfile
import unittest
from pathlib import Path

from generate_report import generate_report


ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"


class ReportTests(unittest.TestCase):
    def test_generates_markdown_with_github_relative_image_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            report_dir = Path(tmp_dir) / "report"
            report_path = generate_report(image_dir=IMAGES, report_dir=report_dir)

            self.assertEqual(report_path, report_dir / "report.md")
            self.assertTrue(report_path.exists())

            content = report_path.read_text(encoding="utf-8")
            self.assertIn("# Electro Parse Report", content)
            self.assertIn("![photo_2026-02-12.jpeg](assets/photo_2026-02-12.debug.jpeg)", content)
            self.assertIn("![photo_2026-03-19.jpeg](assets/photo_2026-03-19.debug.jpeg)", content)

            asset_path = report_dir / "assets" / "photo_2026-02-12.debug.jpeg"
            self.assertTrue(asset_path.exists())
            self.assertTrue(asset_path.stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
