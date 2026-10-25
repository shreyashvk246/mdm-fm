"""
Download monthly historical market data for an Indian investment-analysis project.

Output:
  data/nifty50_monthly.csv
  data/goldbees_monthly.csv
  data/liquidbees_monthly.csv
  data/nifty_midcap50_monthly.csv
  data/giltbees_monthly.csv
  data/data_sources.txt

Source: Yahoo Finance via yfinance
Requested date range: 2015-01-01 through the current date.
Note: Actual coverage depends on each ticker's available history.
"""

from pathlib import Path
from datetime import date, timedelta
import sys

try:
    import yfinance as yf
except ImportError:
    print("Missing dependency. Install it with: pip install yfinance pandas")
    sys.exit(1)

import pandas as pd

OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2015-01-01"
# yfinance's end date is exclusive; tomorrow includes today's data if available.
END_DATE = (date.today() + timedelta(days=1)).isoformat()

ASSETS = {
    "nifty50_monthly.csv": ("^NSEI", "Nifty 50 index"),
    "goldbees_monthly.csv": ("GOLDBEES.NS", "Nippon India ETF Gold BeES"),
    "liquidbees_monthly.csv": ("LIQUIDBEES.NS", "Nippon India ETF Liquid BeES"),
    "nifty_midcap50_monthly.csv": ("^NSEMDCP50", "Nifty Midcap 50 index"),
    "giltbees_monthly.csv": ("GILTBEES.NS", "Nippon India ETF Nifty 8-13 yr G-Sec"),
}

source_lines = [
    "Data source: Yahoo Finance, accessed on " + date.today().isoformat(),
    f"Requested start date: {START_DATE}",
    f"Requested end date: {END_DATE} (coverage may stop at the latest available observation)",
    "Frequency: Monthly (yfinance interval='1mo')",
    "Prices: Yahoo Finance OHLCV fields; use Adj Close when present for return analysis.",
    "",
    "Per-file results:"
]

for filename, (ticker, description) in ASSETS.items():
    print(f"Downloading {description} ({ticker}) ...")
    try:
        df = yf.download(
            ticker,
            start=START_DATE,
            end=END_DATE,
            interval="1mo",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df.empty:
            source_lines.append(f"{filename}: FAILED - no data returned for {ticker}")
            print(f"  No data returned for {ticker}.")
            continue

        # yfinance may return a MultiIndex column layout, even for one ticker.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                col[0] if isinstance(col, tuple) else col
                for col in df.columns
            ]

        df = df.reset_index()
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df = df.rename(columns={date_col: "Date"})
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        df.insert(1, "Ticker", ticker)
        df.to_csv(OUT_DIR / filename, index=False)

        source_lines.append(
            f"{filename}: {ticker} | {description} | "
            f"{df['Date'].min()} to {df['Date'].max()} | "
            f"{len(df)} monthly rows"
        )
        print(f"  Saved {OUT_DIR / filename} ({len(df)} rows)")
    except Exception as exc:
        source_lines.append(f"{filename}: FAILED - {ticker} - {exc}")
        print(f"  Failed: {exc}")

(OUT_DIR / "data_sources.txt").write_text(
    "\n".join(source_lines) + "\n",
    encoding="utf-8"
)

print("\nFinished. Check data/data_sources.txt for source and actual date ranges.")
print("If any ticker failed or has short history, use a suitable alternative ticker or a documented Kaggle CSV.")
