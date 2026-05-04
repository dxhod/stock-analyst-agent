import unittest

from tools.portfolio_builder import missing_required_preferences, normalize_preferences


class PortfolioBuilderPreferenceTests(unittest.TestCase):
    def test_missing_required_preferences(self):
        preferences = {
            "investment_amount": 10000,
            "holdings_count": 10,
            "risk": "Balanced",
        }

        missing = missing_required_preferences(preferences)

        self.assertIn("horizon", missing)
        self.assertIn("style", missing)
        self.assertIn("etf_preference", missing)
        self.assertIn("cash_pct", missing)

    def test_normalize_preferences_defaults_and_bounds(self):
        preferences = normalize_preferences(
            {
                "investment_amount": None,
                "holdings_count": 100,
                "risk": None,
                "horizon": None,
                "style": None,
                "etf_preference": None,
                "cash_pct": 35,
            }
        )

        self.assertEqual(preferences["investment_amount"], 10000)
        self.assertEqual(preferences["holdings_count"], 25)
        self.assertEqual(preferences["risk"], "Balanced")
        self.assertEqual(preferences["horizon"], "1-3yr")
        self.assertEqual(preferences["style"], "Balanced")
        self.assertEqual(preferences["etf_preference"], "Mixed")
        self.assertEqual(preferences["cash_pct"], 20)


if __name__ == "__main__":
    unittest.main()
