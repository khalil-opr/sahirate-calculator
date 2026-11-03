"""Unit tests for the SahiRate calculator. Run with:  python -m unittest -v"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculator import (  # noqa: E402
    CostSettings,
    billable_hours_per_month,
    breakdown_from_gross,
    gross_needed_for_net,
    rate_plan,
)


class TestBreakdown(unittest.TestCase):
    def test_no_costs_means_you_keep_everything(self):
        costs = CostSettings(0, 0, 0, 0, 0, 280)
        b = breakdown_from_gross(100, costs)
        self.assertAlmostEqual(b.net_pkr, 28_000)
        self.assertAlmostEqual(b.keep_pct, 100)

    def test_fiverr_twenty_percent_only(self):
        costs = CostSettings(20, 0, 0, 0, 0, 280)
        b = breakdown_from_gross(100, costs)
        self.assertAlmostEqual(b.platform_fee_usd, 20)
        self.assertAlmostEqual(b.net_pkr, 80 * 280)

    def test_full_chain_by_hand(self):
        # $1,000 on Upwork at 10%, one $0.99 withdrawal, 2% markup, 1% tax, Rs 277.7
        costs = CostSettings(10, 0.99, 1, 2, 1, 277.7)
        b = breakdown_from_gross(1000, costs)
        converted = 1000 * 0.9 - 0.99
        expected = converted * 277.7 * 0.98 * 0.99
        self.assertAlmostEqual(b.net_pkr, expected, places=6)

    def test_deductions_plus_net_equal_gross(self):
        costs = CostSettings(15, 2.5, 3, 2.2, 1, 277.7)
        b = breakdown_from_gross(843.21, costs)
        total = sum(v for _, v in b.cost_rows()) + b.net_pkr
        self.assertAlmostEqual(total, b.gross_pkr, places=6)

    def test_withdrawal_fees_never_exceed_balance(self):
        costs = CostSettings(0, 10, 5, 0, 0, 280)
        b = breakdown_from_gross(20, costs)
        self.assertAlmostEqual(b.withdrawal_fees_usd, 20)
        self.assertAlmostEqual(b.net_pkr, 0)

    def test_override_withdrawals_for_single_payment(self):
        costs = CostSettings(0, 1, 4, 0, 0, 280)
        self.assertAlmostEqual(breakdown_from_gross(100, costs, withdrawals=1).withdrawal_fees_usd, 1)


class TestInverse(unittest.TestCase):
    def test_round_trip(self):
        for costs in [
            CostSettings(),
            CostSettings(20, 0, 2, 2, 1, 277.7),
            CostSettings(0, 0.99, 1, 0.6, 0.25, 300),
            CostSettings(15, 3, 4, 3, 1, 250),
        ]:
            for net in [0, 1, 50_000, 258_750, 1_234_567]:
                gross = gross_needed_for_net(net, costs)
                self.assertAlmostEqual(breakdown_from_gross(gross, costs).net_pkr, net, places=4)


class TestRatePlan(unittest.TestCase):
    def test_billable_hours(self):
        self.assertAlmostEqual(billable_hours_per_month(40, 60, 4), 96)
        self.assertEqual(billable_hours_per_month(40, 60, 60), 0)

    def test_default_plan(self):
        # Rs 200k take-home + Rs 25k expenses, 15% buffer, 40 h/wk, 60% billable, 4 wks off
        # Upwork 10%, Payoneer (no flat fee, 2% markup), PSEB 0.25%, Rs 277.7
        plan = rate_plan(200_000, 25_000, 15, 40, 60, 4, CostSettings(10, 0, 2, 2, 0.25, 277.7))
        net_needed = 225_000 * 1.15
        gross = net_needed / (277.7 * 0.98 * 0.9975) / 0.9
        self.assertAlmostEqual(plan.net_needed_pkr, net_needed)
        self.assertAlmostEqual(plan.gross_usd_per_month, gross, places=6)
        self.assertAlmostEqual(plan.hourly_usd, gross / 96, places=6)
        self.assertTrue(math.isclose(plan.hourly_usd, 11.03, abs_tol=0.01))

    def test_zero_billable_hours_rejected(self):
        with self.assertRaises(ValueError):
            rate_plan(100_000, 0, 0, 40, 60, 52, CostSettings())


class TestValidation(unittest.TestCase):
    def test_bad_settings(self):
        with self.assertRaises(ValueError):
            CostSettings(platform_fee_pct=100)
        with self.assertRaises(ValueError):
            CostSettings(fx_markup_pct=-1)
        with self.assertRaises(ValueError):
            CostSettings(usd_pkr=0)
        with self.assertRaises(ValueError):
            CostSettings(withdrawal_fee_usd=-0.5)


if __name__ == "__main__":
    unittest.main()
