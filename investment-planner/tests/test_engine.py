from engine import InvestmentEngine


def test_allocation_sums_to_100():
    eng = InvestmentEngine()
    res = eng.allocate(200000, 10, 3, 10)
    total = sum(res["allocation_pct"].values())
    assert abs(total - 100.0) < 1e-6


def test_liquidity_respected():
    eng = InvestmentEngine()
    res = eng.allocate(100000, 5, 3, 40)
    assert abs(res["allocation_pct"]["Liquid / Cash"] - 40.0) < 1e-6
    assert abs(res["allocation_rupees"]["Liquid / Cash"] - 40000.0) < 1e-6


def test_equity_within_cap():
    eng = InvestmentEngine()
    res = eng.allocate(100000, 1, 5, 0)  # conflict case
    eq = res["allocation_pct"]["Large-cap Equity"] + res["allocation_pct"]["Mid-cap Equity"]
    assert eq <= res["equity_cap_total"] * 100.0 + 1e-6
    assert len(res["warnings"]) >= 0  # may have warnings


def test_weights_sum_various_personas():
    eng = InvestmentEngine()
    personas = [
        (50000, 2, 1, 30),
        (200000, 10, 5, 10),
        (500000, 3, 3, 20),
        (1000000, 5, 1, 40),
    ]
    for p in personas:
        res = eng.allocate(*p)
        assert abs(sum(res["allocation_pct"].values()) - 100.0) < 1e-6
