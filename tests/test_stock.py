"""
tests/test_stock.py
-------------------
Unit tests for utils/stock.py — Stock price, news, and metrics extractor.
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from utils.stock import get_stock_price


class TestStockPrice(unittest.TestCase):
    """Tests for the stock fetcher utility using mocked yfinance."""

    @patch("utils.stock.yf.Ticker")
    def test_get_stock_price_success(self, mock_ticker):
        # Setup mock Ticker instance
        mock_instance = MagicMock()
        mock_ticker.return_value = mock_instance
        
        # Setup mock history DataFrame
        dates = pd.date_range(start="2026-05-01", periods=30, freq="D")
        mock_df = pd.DataFrame({
            "Close": [100.0 + i for i in range(30)]
        }, index=dates)
        mock_instance.history.return_value = mock_df
        
        # Setup mock info
        mock_instance.info = {
            "fiftyTwoWeekHigh": 150.0,
            "fiftyTwoWeekLow": 90.0,
            "marketCap": 10000000,
            "trailingPE": 25.0
        }
        
        # Setup mock news
        mock_instance.news = [
            {"title": "News 1", "publisher": "Pub 1", "link": "http://link1"},
            {"title": "News 2", "publisher": "Pub 2", "link": "http://link2"}
        ]
        
        result = get_stock_price("AAPL")
        
        self.assertNotIn("error", result)
        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["price"], 129.0)  # Last close price (100.0 + 29)
        self.assertEqual(len(result["news"]), 2)
        self.assertEqual(result["news"][0]["title"], "News 1")
        self.assertEqual(result["metrics"]["high_52w"], 150.0)

    @patch("utils.stock.yf.Ticker")
    def test_get_stock_price_empty_history(self, mock_ticker):
        # Setup mock Ticker instance returning empty history
        mock_instance = MagicMock()
        mock_ticker.return_value = mock_instance
        mock_instance.history.return_value = pd.DataFrame()
        
        result = get_stock_price("INVALID")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Invalid stock symbol or no data found")


if __name__ == "__main__":
    unittest.main()
