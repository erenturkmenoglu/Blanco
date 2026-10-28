from datetime import date

import pandas as pd

from app.calc.engine import annualize_ytd, compute_derived, growth, maturity_shares, quarterly_from_cumulative, spread
from app.validation.checks import blocked, run_checks


def test_quarterly_from_cumulative_and_annualize():
    ytd = {date(2026, 3, 31): 10.0, date(2026, 6, 30): 25.0, date(2026, 12, 31): 60.0}
    q = quarterly_from_cumulative(ytd)
    assert q[date(2026, 3, 31)] == 10.0 and q[date(2026, 6, 30)] == 15.0
    assert q[date(2026, 12, 31)] is None          # Q3 yok → uydurulmaz
    v, method = annualize_ytd(25.0, date(2026, 6, 30))
    assert v == 50.0 and "YTD×4/2" in method


def test_growth_requires_base():
    s = {date(2025, 6, 30): 100.0, date(2026, 3, 31): 130.0, date(2026, 6, 30): 150.0}
    g, _ = growth(s, date(2026, 6, 30), 1)
    assert abs(g - (150 / 130 - 1)) < 1e-9
    g, _ = growth(s, date(2026, 6, 30), 4)
    assert abs(g - 0.5) < 1e-9
    assert growth(s, date(2026, 3, 31), 4)[0] is None


def test_spread_refuses_mismatched_definitions():
    pe = date(2023, 6, 30)
    loan = {"value": 12.07, "rate_definition": "stock_avg_applied_rate", "currency": "TRY", "period_end": pe, "reporting_scope": "solo"}
    dep = {**loan, "value": 21.40}
    s = spread(loan, dep)
    assert abs(s.value - (12.07 - 21.40)) < 1e-9 and "STOK" in s.limitations
    dep2 = {**dep, "rate_definition": "new_business_flow_rate"}
    assert spread(loan, dep2).value is None and "rate_definition" in spread(loan, dep2).limitations


def test_maturity_shares_keeps_3_12_bucket():
    d = maturity_shares({"demand": 100, "0_1m": 200, "1_3m": 150, "3_12m": 250, "1_5y": 300, "total": 1000}, total=1000)
    assert abs(d.inputs["shares"]["3_12m"] - 0.25) < 1e-9 and "3-12" in d.limitations
    assert "illustrative" in d.method


def test_validation_blocks_scale_unknown_and_balance_mismatch():
    pe = date(2026, 6, 30)
    base = dict(bank_code="akbank", bank_match="alias", period_end=pe, unit="TRY", currency="ALL", reporting_scope="solo", frequency="quarterly",
                source_code="TBB", cumulative_ytd=False)
    obs = [{**base, "metric_code": "total_assets", "value": 1000.0, "scale": None}]
    res = run_checks(obs)
    assert blocked(res) and any(r.code == "DQ04_unit_scale" for r in res)
    obs = [{**base, "metric_code": "total_assets", "value": 1000.0, "scale": 1e3},
           {**base, "metric_code": "total_liabilities", "value": 900.0, "scale": 1e3}]
    res = run_checks(obs)
    assert any(r.code == "DQ06_balance" and not r.passed for r in res)
    obs = [{**base, "metric_code": "loan_interest_tl", "value": 12.0, "unit": "pct", "scale": 1.0, "rate_definition": None}]
    assert any(r.code == "DQ11_rate_definition" for r in run_checks(obs))
    dup = {**base, "metric_code": "total_assets", "value": 1.0, "scale": 1.0}
    assert any(r.code == "DQ07_duplicate" for r in run_checks([dup, dup]))


def test_compute_derived_reports_methods_and_limits():
    rows = []
    def add(code, pe, v, cum=False):
        rows.append({"bank_code": "akbank", "metric_code": code, "period_end": pe, "value": v, "reporting_scope": "solo", "cumulative_ytd": cum})
    pe, pye, pq = date(2026, 6, 30), date(2025, 12, 31), date(2026, 3, 31)
    add("total_assets", pe, 1200.0); add("total_assets", pye, 1000.0); add("total_assets", pq, 1100.0)
    add("total_equity", pe, 120.0); add("total_equity", pye, 100.0)
    add("net_profit", pe, 30.0, True); add("net_interest_income", pe, 50.0, True); add("operating_expenses", pe, 20.0, True)
    add("net_fee_commission_income", pe, 10.0, True); add("loans_gross", pe, 800.0); add("total_deposits", pe, 700.0)
    add("npl_amount", pe, 16.0); add("loan_loss_provisions", pe, 12.0)
    df = pd.DataFrame(rows)
    out = {d.metric_code: d for d in compute_derived(df, "akbank", pe)}
    assert abs(out["roa"].value - (60.0 / 1100.0 * 100)) < 1e-9 and "YTD×4/2" in out["roa"].method
    assert abs(out["roe"].value - (60.0 / 110.0 * 100)) < 1e-9
    assert abs(out["npl_ratio"].value - 2.0) < 1e-9 and abs(out["npl_coverage_ratio"].value - 75.0) < 1e-9
    assert abs(out["loan_to_deposit_ratio"].value - (800 / 700 * 100)) < 1e-9
    assert abs(out["assets_growth_qoq"].value - (1200 / 1100 - 1) * 100) < 1e-9
    assert out["assets_growth_yoy"].value is None            # 2025-06 yok → None, uydurma yok
    assert out["nim"].limitations and "TOPLAM aktif" in out["nim"].limitations
    assert out["cost_to_income"].limitations                 # ticari/diğer gelir eksik → sınırlama notu
