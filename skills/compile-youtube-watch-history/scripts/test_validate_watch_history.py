from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_watch_history.py")
SPEC = importlib.util.spec_from_file_location("validate_watch_history", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ValidateWatchHistoryTests(unittest.TestCase):
    def test_rejects_video_id_with_wrong_length(self) -> None:
        errors: list[str] = []

        VALIDATOR.validate_url(
            "https://www.youtube.com/watch?v=x",
            Path("fixture.md"),
            1,
            errors,
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("valid v parameter", errors[0])

    def test_repository_neighbor_requires_cross_month_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "outputs"
            month_dir = output_root / "2026" / "07"
            repository_root = root / "repository"
            month_dir.mkdir(parents=True)
            (repository_root / "2026" / "06").mkdir(parents=True)
            (repository_root / "2026" / "06" / "20260630.md").write_text(
                "# Tuesday, June 30, 2026\n",
                encoding="utf-8",
            )
            daily_file = month_dir / "20260701.md"
            daily_file.write_text(
                "# Wednesday, July 1, 2026\n\n"
                "[Next →](20260702.md)\n\n"
                "## YouTube\n",
                encoding="utf-8",
            )
            (month_dir / "20260702.md").write_text(
                "# Thursday, July 2, 2026\n",
                encoding="utf-8",
            )
            errors: list[str] = []

            VALIDATOR.validate_daily_file(
                daily_file,
                date(2026, 7, 1),
                month_dir,
                output_root,
                repository_root,
                errors,
            )

            self.assertTrue(
                any("navigation links do not match adjacent files" in error for error in errors)
            )


if __name__ == "__main__":
    unittest.main()
