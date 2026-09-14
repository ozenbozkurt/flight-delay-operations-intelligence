import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from flight_delay.cli import main

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo_flights.csv"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "results"

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["--input", str(DEMO), "--output", str(self.output), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_export_creates_expected_tables_and_valid_json(self):
        code, stdout, stderr = self.run_cli()
        self.assertEqual(code, 0, stderr)
        self.assertIn("Analyzed 7 of 8", stdout)
        self.assertEqual(len(list(self.output.glob("*.csv"))), 5)
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertEqual(summary["analyzed_rows"], 7)
        self.assertEqual((self.output / "top_risky_routes.csv").read_text().count("\n"), 1)

    def test_existing_outputs_are_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "important.txt"
        sentinel.write_text("keep")
        code, _, stderr = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("new or empty directory", stderr)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_bad_input_creates_no_output(self):
        missing = Path(self.temp.name) / "missing.csv"
        code, _, _ = self.run_cli("--input", str(missing))
        self.assertEqual(code, 2)
        self.assertFalse(self.output.exists())

    def test_bad_arguments_create_no_output(self):
        code, _, stderr = self.run_cli("--min-flights", "0")
        self.assertEqual(code, 2)
        self.assertIn("positive integer", stderr)
        self.assertFalse(self.output.exists())

    def test_header_only_csv_creates_no_output(self):
        empty = Path(self.temp.name) / "empty.csv"
        empty.write_text(DEMO.read_text().splitlines()[0] + "\n")
        code, _, stderr = self.run_cli("--input", str(empty))
        self.assertEqual(code, 2)
        self.assertIn("No valid", stderr)

    def test_literal_na_carrier_code_is_preserved(self):
        fixture = Path(self.temp.name) / "carrier.csv"
        fixture.write_text("fl_date,dep_delay,origin,dest,op_unique_carrier\n2024-01-01,3,AAA,BBB,NA\n")
        code, _, stderr = self.run_cli("--input", str(fixture), "--min-flights", "1")
        self.assertEqual(code, 0, stderr)
        self.assertIn("NA,1,3.0", (self.output / "worst_carriers.csv").read_text())

    def test_module_cli_runs_outside_the_repository(self):
        run = subprocess.run([sys.executable, "-m", "flight_delay", "--input", str(DEMO),
                              "--output", str(self.output)], cwd=self.temp.name,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((self.output / "summary.json").exists())

    def test_optional_charts_are_real_png_files(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("charts extra not installed")
        code, _, stderr = self.run_cli("--charts")
        self.assertEqual(code, 0, stderr)
        images = list(self.output.glob("*.png"))
        self.assertEqual(len(images), 4)
        for image in images:
            self.assertEqual(image.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
