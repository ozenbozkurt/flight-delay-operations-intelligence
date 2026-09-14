import math
from pathlib import Path
import unittest

import pandas as pd

from flight_delay import analyze

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo_flights.csv"


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.read_csv(DEMO)

    def test_demo_metrics_and_exclusion_counts(self):
        result = analyze(self.data, min_flights=1, min_route_flights=1)
        self.assertEqual(result.summary["input_rows"], 8)
        self.assertEqual(result.summary["analyzed_rows"], 7)
        self.assertEqual(result.summary["cancelled_rows_excluded"], 1)
        self.assertEqual(result.summary["invalid_non_cancelled_rows_excluded"], 0)
        self.assertAlmostEqual(result.summary["late_rate"], 3 / 7)
        self.assertAlmostEqual(result.summary["avg_dep_delay"], 115 / 7)
        month = result.tables["by_month_metrics"]
        self.assertEqual(month.loc["2024-01", "n"], 4)
        self.assertEqual(month.loc["2024-01", "late_rate"], .25)
        self.assertAlmostEqual(month.loc["2024-02", "late_rate"], 2 / 3)
        self.assertEqual(result.tables["top_risky_routes"].index[0], "CCC-BBB")
        self.assertAlmostEqual(result.tables["delay_reason_share"]["share"].sum(), 1)

    def test_fifteen_minutes_is_not_late_in_historical_convention(self):
        one = self.data.iloc[[2]]
        self.assertEqual(analyze(one).summary["late_rate"], 0)
        self.assertEqual(analyze(one, late_threshold=14).summary["late_rate"], 1)

    def test_small_dataset_yields_header_only_rankings(self):
        result = analyze(self.data)
        for key in ("worst_origins", "worst_carriers", "top_risky_routes"):
            self.assertTrue(result.tables[key].empty)
        self.assertEqual(len(result.summary["warnings"]), 3)

    def test_invalid_dates_numbers_and_blank_identifiers_are_counted(self):
        data = self.data.astype(object)
        data.loc[0, "fl_date"] = "invalid"
        data.loc[1, "dep_delay"] = "bad"
        data.loc[2, "origin"] = "  "
        data.loc[3, "dep_delay"] = float("inf")
        result = analyze(data)
        self.assertEqual(result.summary["analyzed_rows"], 3)
        self.assertEqual(result.summary["invalid_non_cancelled_rows_excluded"], 4)

    def test_missing_reason_columns_are_unknown(self):
        result = analyze(self.data[list(("fl_date", "dep_delay", "origin", "dest", "op_unique_carrier"))])
        table = result.tables["delay_reason_share"]
        self.assertTrue(table["minutes_total"].isna().all())
        self.assertTrue(table["share"].isna().all())
        self.assertTrue(table["observed_rows"].eq(0).all())

    def test_zero_reason_minutes_have_undefined_share(self):
        result = analyze(self.data.iloc[[0, 1]])
        self.assertTrue(result.tables["delay_reason_share"]["share"].isna().all())
        self.assertTrue(result.tables["delay_reason_share"]["minutes_total"].eq(0).all())

    def test_invalid_reason_minutes_do_not_enter_totals(self):
        data = self.data.copy()
        data.loc[0, "carrier_delay"] = -10
        data.loc[1, "carrier_delay"] = float("inf")
        result = analyze(data)
        row = result.tables["delay_reason_share"].loc["carrier_delay"]
        self.assertEqual(row["minutes_total"], 30)
        self.assertEqual(row["missing_or_invalid_rows"], 2)

    def test_cancelled_record_with_delay_is_excluded(self):
        data = self.data.copy()
        data.loc[7, "dep_delay"] = 900
        self.assertAlmostEqual(analyze(data).summary["avg_dep_delay"], 115 / 7)

    def test_original_dataframe_is_not_mutated(self):
        before = self.data.copy(deep=True)
        analyze(self.data)
        pd.testing.assert_frame_equal(before, self.data)

    def test_missing_required_columns_produce_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Missing required columns: dest"):
            analyze(self.data.drop(columns="dest"))

    def test_duplicate_columns_produce_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analyze(pd.concat([self.data, self.data[["origin"]]], axis=1))

    def test_empty_or_all_cancelled_inputs_fail(self):
        for data in (self.data.iloc[:0], self.data.iloc[[7]]):
            with self.subTest(rows=len(data)), self.assertRaisesRegex(ValueError, "No valid"):
                analyze(data)

    def test_invalid_parameters_fail(self):
        for args in ({"min_flights": 0}, {"min_route_flights": -1}, {"min_flights": 1.5},
                     {"min_flights": True}, {"late_threshold": math.nan},
                     {"late_threshold": math.inf}, {"late_threshold": -1}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                analyze(self.data, **args)


if __name__ == "__main__":
    unittest.main()
