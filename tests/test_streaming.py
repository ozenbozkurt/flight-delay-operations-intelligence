from pathlib import Path
import tempfile
import unittest

import pandas as pd

from flight_delay import analyze
from flight_delay.streaming import analyze_csv


DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo_flights.csv"


class StreamingTests(unittest.TestCase):
    def test_streaming_matches_in_memory(self):
        data = pd.concat(
            [pd.read_csv(DEMO)] * 4,
            ignore_index=True,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flights.csv"
            data.to_csv(path, index=False)

            expected = analyze(
                data,
                min_flights=1,
                min_route_flights=1,
            )
            actual = analyze_csv(
                path,
                chunksize=3,
                min_flights=1,
                min_route_flights=1,
            )

        self.assertEqual(actual.summary, expected.summary)

        for name in expected.tables:
            pd.testing.assert_frame_equal(
                actual.tables[name],
                expected.tables[name],
                check_dtype=False,
                check_exact=False,
                rtol=1e-12,
                atol=1e-12,
            )

    def test_missing_reason_columns_remain_unknown(self):
        data = pd.read_csv(DEMO)
        data = data[
            [
                "fl_date",
                "dep_delay",
                "origin",
                "dest",
                "op_unique_carrier",
            ]
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flights.csv"
            data.to_csv(path, index=False)

            result = analyze_csv(
                path,
                chunksize=2,
                min_flights=1,
                min_route_flights=1,
            )

        reasons = result.tables["delay_reason_share"]
        self.assertTrue(reasons["minutes_total"].isna().all())
        self.assertTrue(reasons["share"].isna().all())
        self.assertTrue(reasons["observed_rows"].eq(0).all())

    def test_streaming_rejects_invalid_chunksize(self):
        with self.assertRaisesRegex(ValueError, "chunksize"):
            analyze_csv(DEMO, chunksize=0)

    def test_streaming_rejects_missing_required_column(self):
        data = pd.read_csv(DEMO).drop(columns="dest")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flights.csv"
            data.to_csv(path, index=False)

            with self.assertRaisesRegex(ValueError, "Missing required columns: dest"):
                analyze_csv(path, chunksize=2)


if __name__ == "__main__":
    unittest.main()
