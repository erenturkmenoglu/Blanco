import pandas as pd

from app.normalization.bank_names import BankRegistry, normalize_name
from app.normalization.mapping import map_label, map_table
from app.normalization.periods import parse_period
from app.normalization.special_tables import map_interest_table, map_maturity_table
from tests.fixtures import balance_sheet_rows, interest_table_rows, maturity_table_rows


def test_bank_name_normalization_and_matching():
    reg = BankRegistry()
    assert normalize_name("T.C. Ziraat Bankası A.Ş.") == "t c ziraat bankası"
    assert reg.match("T.C. Ziraat Bankası A.Ş.")[0] == "ziraat"
    assert reg.match("Türkiye İş Bankası A.Ş.")[0] == "isbank"
    assert reg.match("TÜRKİYE İŞ BANKASI A.Ş.")[0] == "isbank"      # İ/I Türkçe küçük harf
    assert reg.match("Yapı ve Kredi Bankası A.Ş.")[0] == "yapikredi"
    code, conf, how = reg.match("Tamamen Bilinmeyen Banka A.Ş.")
    assert code is None and how == "none"
    assert reg.is_aggregate("Sektör") and reg.is_aggregate("Kamusal Sermayeli Mevduat Bankaları")


def test_period_parsing():
    assert parse_period("Haziran 2026").label == "2026Q2"
    assert parse_period("30.06.2026").end.isoformat() == "2026-06-30"
    assert parse_period("2026-06").label == "2026Q2"
    assert parse_period("2025Q4").end.isoformat() == "2025-12-31"
    assert parse_period("Jun-26").end.month == 6
    assert parse_period("2024").frequency == "annual"
    assert parse_period("Ocak 2026").frequency == "monthly"


def test_label_mapping():
    assert map_label("Toplam Aktifler") == "total_assets"
    assert map_label("Krediler") == "loans_gross"
    assert map_label("Krediler (Net)") == "loans_net"
    assert map_label("Dönem Net Kârı") == "net_profit"
    assert map_label("Net Ücret ve Komisyon Gelirleri") == "net_fee_commission_income"
    assert map_label("Sermaye Yeterliliği Standart Oranı") == "capital_adequacy_ratio"
    assert map_label("Şüpheli Bir Kalem") is None


def test_map_table_banks_in_columns_with_scale():
    df = pd.DataFrame(balance_sheet_rows())
    res = map_table(df, BankRegistry())
    assert res.orientation == "banks_in_columns" and res.scale == 1e3
    zi = {o.metric_code: o.value_raw for o in res.observations if o.bank_code == "ziraat"}
    assert zi["total_assets"] == 1_000_000 and zi["loans_gross"] == 700_000 and zi["total_deposits"] == 650_000
    assert "Şüpheli Bir Kalem" in res.unmapped_labels
    assert all(o.bank_code for o in res.observations)


def test_interest_table_mapping_matches_verified_values():
    rows = map_interest_table(pd.DataFrame(interest_table_rows()), BankRegistry())
    z = {(r.key["currency"], r.key["instrument"]): r.value for r in rows if r.bank_code == "ziraat"}
    assert z[("TRY", "loan")] == 12.07 and z[("TRY", "deposit")] == 21.40
    assert z[("USD", "loan")] == 8.64 and z[("EUR", "deposit")] == 0.77
    assert all(r.key["rate_definition"] == "stock_avg_applied_rate" for r in rows)
    assert any(r.bank_match == "aggregate" for r in rows)       # sektör satırı banka değil


def test_maturity_table_mapping_keeps_source_buckets():
    rows = map_maturity_table(pd.DataFrame(maturity_table_rows()), BankRegistry())
    za = {r.key["bucket"]: r.value for r in rows if r.bank_code == "ziraat" and r.key["item"] == "total_assets"}
    zl = {r.key["bucket"]: r.value for r in rows if r.bank_code == "ziraat" and r.key["item"] == "total_liabilities"}
    assert za["3_12m"] == 250 and za["demand"] == 100 and za["total"] == 1150
    assert zl["demand"] == 300 and "3_6m" not in za and "6_12m" not in za      # 3-12 ay yapay bölünmedi
    assert all(r.key["basis"] == "remaining" for r in rows)


def test_single_bank_workbook_mapping_uses_bank_hint():
    from app.normalization.periods import quarter_period
    rows = [["Akbank T.A.Ş. — Bilanço (Bin TL)", None, None, None],
            ["Kalem", "TP", "YP", "Toplam"],
            ["Toplam Aktifler", "600.000", "400.000", "1.000.000"],
            ["Mevduat", "350.000", "300.000", "650.000"],
            ["Bilinmeyen Satır", "1", "2", "3"]]
    res = map_table(pd.DataFrame(rows), BankRegistry(), bank_hint="Akbank T.A.Ş.", period_hint=quarter_period(2026, 6))
    assert res.orientation == "single_bank" and res.scale == 1e3
    got = {(o.metric_code, o.currency): o.value_raw for o in res.observations}
    assert got[("total_assets", "TRY")] == 600_000 and got[("total_assets", "FX")] == 400_000 and got[("total_deposits", "ALL")] == 650_000
    assert all(o.bank_code == "akbank" for o in res.observations) and "Bilinmeyen Satır" in res.unmapped_labels
