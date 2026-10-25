"""
Build asset assumptions (return, volatility, correlation) from historical data.
Generates assets.json used by the engine and app.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path("data")
ASSETS_JSON = Path("assets.json")

# Map files to asset classes
ASSET_MAP = [
    ("liquidbees_monthly.csv", "Liquid / Cash"),
    ("giltbees_monthly.csv", "Bonds / FDs"),
    ("nifty50_monthly.csv", "Large-cap Equity"),
    ("nifty_midcap50_monthly.csv", "Mid-cap Equity"),
    ("goldbees_monthly.csv", "Gold"),
]

INFLATION_ANNUAL = 0.06  # 6% - hard-coded as suggested


def annualize_return(monthly_returns):
    # Geometric mean annualized
    if monthly_returns.empty:
        return 0.0
    cum = (1 + monthly_returns).prod()
    years = len(monthly_returns) / 12.0
    if years <= 0:
        return 0.0
    return cum ** (1 / years) - 1


def annualize_vol(monthly_returns):
    if monthly_returns.empty:
        return 0.0
    return monthly_returns.std() * np.sqrt(12)


def main():
    prices = {}
    for fname, label in ASSET_MAP:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing {fpath}. Run download_market_data.py first.")
        df = pd.read_csv(fpath)
        # Try common price columns
        for col in ["Adj Close", "Adj_Close", "Close", "close"]:
            if col in df.columns:
                prices[label] = pd.Series(df[col].values, index=pd.to_datetime(df["Date"]))
                break
        else:
            raise ValueError(f"No price column found in {fpath}")

    # Align dates
    dfp = pd.DataFrame(prices)
    dfp = dfp.dropna()
    # Monthly returns
    rets = dfp.pct_change().dropna()

    assets = {}
    for label in ASSET_MAP:
        label_name = label[1]
        if label_name not in rets.columns:
            continue
        r = rets[label_name]
        assets[label_name] = {
            "expected_return": float(annualize_return(r)),
            "volatility": float(annualize_vol(r)),
            "liquidity": "high" if label_name in ["Liquid / Cash", "Large-cap Equity", "Mid-cap Equity", "Gold"] else "medium",
            "min_horizon_years": 0 if label_name == "Liquid / Cash" else (1 if label_name == "Bonds / FDs" else (3 if label_name == "Gold" else (5 if label_name == "Large-cap Equity" else 7))),
        }

    # Correlation matrix
    corr = rets[assets.keys()].corr()
    assets_corr = corr.to_dict()

    out = {
        "inflation_annual": INFLATION_ANNUAL,
        "assets": assets,
        "correlation": assets_corr,
        "source_note": "Computed from monthly historical data via yfinance (see data/data_sources.txt). If data was unavailable, use sensible defaults.",
    }

    with open(ASSETS_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {ASSETS_JSON} with {len(assets)} assets")


if __name__ == "__main__":
    main()
