"""
Core engine for Interactive Investment Planning System
- Risk/horizon caps, liquidity reservation, allocation, projections, validation
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

ASSETS_JSON = Path("assets.json")

ASSET_ORDER = [
    "Liquid / Cash",
    "Bonds / FDs",
    "Large-cap Equity",
    "Mid-cap Equity",
    "Gold",
]


class InvestmentEngine:
    def __init__(self, config_path: Path = ASSETS_JSON):
        self.config_path = config_path
        self.config = self._load_config()
        self.assets = self.config.get("assets", {})
        self.inflation = float(self.config.get("inflation_annual", 0.06))
        self.corr = self.config.get("correlation", {})

    def _load_config(self):
        if not self.config_path.exists():
            return {
                "inflation_annual": 0.06,
                "assets": {
                    "Liquid / Cash": {"expected_return": 0.035, "volatility": 0.005, "liquidity": "high", "min_horizon_years": 0},
                    "Bonds / FDs": {"expected_return": 0.065, "volatility": 0.08, "liquidity": "medium", "min_horizon_years": 1},
                    "Large-cap Equity": {"expected_return": 0.11, "volatility": 0.18, "liquidity": "high", "min_horizon_years": 5},
                    "Mid-cap Equity": {"expected_return": 0.13, "volatility": 0.22, "liquidity": "high", "min_horizon_years": 7},
                    "Gold": {"expected_return": 0.08, "volatility": 0.16, "liquidity": "high", "min_horizon_years": 3},
                },
                "correlation": {},
                "source_note": "Default assumptions used (assets.json not found).",
            }
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_equity_caps(self, risk: int, horizon_years: float) -> Dict[str, float]:
        risk = max(1, min(5, int(risk)))
        if risk <= 2:
            risk_cap = 0.25
        elif risk == 3:
            risk_cap = 0.45
        elif risk == 4:
            risk_cap = 0.70
        else:
            risk_cap = 0.80

        if horizon_years < 2:
            horizon_cap = 0.15
        elif horizon_years < 3:
            horizon_cap = 0.25
        elif horizon_years < 5:
            horizon_cap = 0.40
        elif horizon_years < 7:
            horizon_cap = 0.55
        else:
            horizon_cap = 0.80

        equity_cap_total = min(risk_cap, horizon_cap)
        return {"risk_cap": risk_cap, "horizon_cap": horizon_cap, "equity_cap_total": equity_cap_total}

    def validate_inputs(self, amount: float, horizon_years: float, risk: int, liquidity_pct: float) -> List[str]:
        warnings = []
        if amount <= 0:
            warnings.append("Investment amount must be greater than 0.")
        if horizon_years <= 0:
            warnings.append("Duration must be greater than 0 years.")
        if not (1 <= risk <= 5):
            warnings.append("Risk tolerance should be between 1 (Low) and 5 (High).")
        if not (0 <= liquidity_pct <= 100):
            warnings.append("Liquidity need should be between 0% and 100%.")
        caps = self.get_equity_caps(risk, horizon_years)
        if risk >= 4 and horizon_years < 2:
            warnings.append("Conflict: High risk with very short horizon. Equity is capped for capital preservation.")
        if liquidity_pct > 80 and horizon_years >= 5:
            warnings.append("Note: High liquidity need limits long-term growth potential.")
        return warnings

    def allocate(self, amount: float, horizon_years: float, risk: int, liquidity_pct: float) -> Dict[str, Any]:
        warnings = self.validate_inputs(amount, horizon_years, risk, liquidity_pct)
        liquidity_pct = max(0, min(100, float(liquidity_pct)))
        caps = self.get_equity_caps(risk, horizon_years)
        eq_cap = caps["equity_cap_total"]

        alloc = {k: 0.0 for k in ASSET_ORDER}

        if amount <= 0:
            return {"amount": amount, "allocation_pct": alloc, "allocation_rupees": alloc, "warnings": warnings, "explanation": "Invalid amount."}

        alloc["Liquid / Cash"] = liquidity_pct
        rem_pct = 100.0 - liquidity_pct
        if rem_pct <= 0:
            alloc_r = {k: amount * (v / 100.0) for k, v in alloc.items()}
            return {
                "amount": amount,
                "horizon_years": horizon_years,
                "risk": risk,
                "liquidity_pct": liquidity_pct,
                "equity_cap_total": eq_cap,
                "allocation_pct": alloc,
                "allocation_rupees": alloc_r,
                "warnings": warnings,
                "explanation": "All funds reserved in liquid/cash due to high liquidity need.",
            }

        bonds_target = min(40.0, max(10.0, 30.0 - risk * 5.0))
        gold_target = min(15.0, max(5.0, 10.0))
        equity_total_pct = rem_pct - bonds_target - gold_target
        if equity_total_pct < 0:
            equity_total_pct = 0.0
        if equity_total_pct > eq_cap * 100.0:
            equity_total_pct = eq_cap * 100.0
        s = bonds_target + gold_target + equity_total_pct
        if s > rem_pct:
            scale = rem_pct / s
            bonds_target *= scale
            gold_target *= scale
            equity_total_pct *= scale
        elif s < rem_pct:
            bonds_target += (rem_pct - s)

        if equity_total_pct > 0:
            large_eq = equity_total_pct * 0.7
            mid_eq = equity_total_pct * 0.3
        else:
            large_eq = mid_eq = 0.0

        alloc["Bonds / FDs"] = bonds_target
        alloc["Large-cap Equity"] = large_eq
        alloc["Mid-cap Equity"] = mid_eq
        alloc["Gold"] = gold_target

        total = sum(alloc.values())
        if total > 0:
            for k in alloc:
                alloc[k] = alloc[k] * 100.0 / total

        alloc_r = {k: amount * (v / 100.0) for k, v in alloc.items()}

        explanation = (
            f"Liquidity of {liquidity_pct:.0f}% reserved first in Liquid/Cash. "
            f"Equity capped at {eq_cap*100:.0f}% of total (lower of risk cap {caps['risk_cap']*100:.0f}% and horizon cap {caps['horizon_cap']*100:.0f}%). "
            f"Remainder split across bonds, equity (large/mid) and gold with stability bias."
        )

        return {
            "amount": amount,
            "horizon_years": horizon_years,
            "risk": risk,
            "liquidity_pct": liquidity_pct,
            "equity_cap_total": eq_cap,
            "caps": caps,
            "allocation_pct": alloc,
            "allocation_rupees": alloc_r,
            "warnings": warnings,
            "explanation": explanation,
        }

    def project(self, allocation_pct: Dict[str, float], horizon_years: float, n_sims: int = 1000) -> Dict[str, Any]:
        horizon_years = max(0.0, float(horizon_years))
        if horizon_years == 0:
            horizon_years = 1e-9

        w = []
        rets = []
        vols = []
        for k in ASSET_ORDER:
            if k not in self.assets:
                continue
            w.append(float(allocation_pct.get(k, 0.0)) / 100.0)
            rets.append(float(self.assets[k]["expected_return"]))
            vols.append(float(self.assets[k]["volatility"]))
        w = np.array(w, dtype=float)
        rets = np.array(rets, dtype=float)
        vols = np.array(vols, dtype=float)
        if w.sum() == 0:
            port_ret = 0.0
            port_vol = 0.0
        else:
            w = w / w.sum()
            port_ret = float(np.asarray(np.dot(w, rets)).reshape(-1)[0])
            var = float(np.asarray(np.dot(w * w, vols * vols)).reshape(-1)[0])
            port_vol = float(np.sqrt(max(var, 0.0)))

        scenarios = {}
        for name, dr in [("pessimistic", port_ret - port_vol), ("base", port_ret), ("optimistic", port_ret + port_vol)]:
            fv = ((1 + dr) ** horizon_years)
            scenarios[name] = {"fv_multiple": fv, "fv_per_unit": fv}

        rng = np.random.default_rng(12345)
        sims = []
        for _ in range(n_sims):
            path_ret = rng.normal(port_ret, port_vol, size=int(max(1, round(horizon_years))))
            cum = np.prod(1 + path_ret)
            if horizon_years % 1 != 0:
                cum *= (1 + rng.normal(port_ret, port_vol))
            sims.append(cum)
        sims = np.array(sims)
        p10, p50, p90 = np.percentile(sims, [10, 50, 90])

        return {
            "portfolio_expected_return": port_ret,
            "portfolio_volatility": port_vol,
            "inflation_annual": self.inflation,
            "scenarios": scenarios,
            "monte_carlo": {"n": n_sims, "p10": float(p10), "p50": float(p50), "p90": float(p90)},
            "inflation_adjusted_p50_multiple": float(p50 / ((1 + self.inflation) ** horizon_years)),
        }
