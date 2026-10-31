"use client";
import { Chart } from "@/components/Chart";
import { Table } from "@/components/Table";
import { useCcy } from "@/components/Ccy";
import { D, ccyUnit, conv, item, ratio, series, stockPeriods } from "@/lib/data";

export default function Bilanco() {
  const { ccy } = useCcy(); const u = ccyUnit(ccy);
  const st = (code: string) => (p: string) => conv(item(code).values[p], p, ccy);
  const r = (code: string) => (p: string) => ratio(code).values[p] ?? null;
  const S = (codes: [string, string][]) => series(codes.map(([c]) => ({ key: c, get: st(c) })), stockPeriods);
  const N = (codes: [string, string][]) => codes.map(([c, n]) => ({ key: c, name: n }));
  const assets: [string, string][] = [["cash_and_central_bank", "Nakit ve TCMB"], ["due_from_banks", "Bankalar"], ["money_market_receivables", "Para piyasası"], ["securities_portfolio", "Menkul kıymetler"], ["loans_gross", "Krediler (brüt)"], ["derivative_assets", "Türev varlıklar"], ["other_assets", "Diğer aktifler"]];
  const liabs: [string, string][] = [["total_deposits", "Mevduat"], ["funds_borrowed", "Alınan krediler"], ["money_market_funds", "Para piyasası"], ["derivative_liabilities", "Türev yükümlülükler"], ["provisions", "Karşılıklar"], ["tax_liabilities", "Vergi borcu"], ["other_liabilities", "Diğer yükümlülükler"], ["total_equity", "Özkaynaklar"]];
  const eq: [string, string][] = [["paid_in_capital", "Ödenmiş sermaye"], ["capital_reserves", "Sermaye yedekleri"], ["oci_accumulated", "Birikmiş OCI"], ["profit_reserves", "Kâr yedekleri"], ["net_profit_bs", "Dönem net kârı"]];
  const bsItems = D.items.filter(i => i.section.startsWith("balance_sheet") && i.status !== "UNAVAILABLE");
  const periods = stockPeriods;
  return (
    <>
      <h1>Bilanço</h1>
      <div className="grid2">
        <Chart title="Aktif kompozisyonu" unit={u} kind="bar" stacked data={S(assets)} series={N(assets)} />
        <Chart title="Pasif kompozisyonu" unit={u} kind="bar" stacked data={S(liabs)} series={N(liabs)} />
        <Chart title="Brüt krediler – TP / YP" unit={u} kind="bar" stacked data={S([["loans_tl", "TP"], ["loans_fx", "YP"]])} series={N([["loans_tl", "TP krediler"], ["loans_fx", "YP krediler"]])} />
        <Chart title="Mevduat – TP / YP" unit={u} kind="bar" stacked data={S([["deposits_tl", "TP"], ["deposits_fx", "YP"]])} series={N([["deposits_tl", "TP mevduat"], ["deposits_fx", "YP mevduat"]])} />
        <Chart title="Alınan krediler – TP / YP" unit={u} kind="bar" stacked data={S([["funds_borrowed_tl", "TP"], ["funds_borrowed_fx", "YP"]])} series={N([["funds_borrowed_tl", "TP"], ["funds_borrowed_fx", "YP"]])} />
        <Chart title="Likit aktifler" unit={u} data={S([["cash_cb_tl", ""], ["cash_cb_fx", ""], ["due_from_banks", ""], ["securities_portfolio", ""]])} series={N([["cash_cb_tl", "Nakit+TCMB TP"], ["cash_cb_fx", "Nakit+TCMB YP"], ["due_from_banks", "Bankalar"], ["securities_portfolio", "Menkul kıymetler"]])} />
        <Chart title="Özkaynak kompozisyonu" unit={u} kind="bar" stacked data={S(eq)} series={N(eq)} />
        <Chart title="YP payları" pct data={series([{ key: "a", get: r("fx_assets_share") }, { key: "l", get: r("fx_liabilities_share") }, { key: "k", get: r("fx_loans_share") }, { key: "m", get: r("fx_deposits_share") }], periods)} series={[{ key: "a", name: "YP aktif" }, { key: "l", name: "YP pasif" }, { key: "k", name: "YP kredi" }, { key: "m", name: "YP mevduat" }]} />
        <Chart title="Bilanço yapısı" pct data={series([{ key: "k", get: r("loans_to_assets") }, { key: "m", get: r("deposits_to_assets") }, { key: "f", get: r("funds_borrowed_to_assets") }, { key: "c", get: r("cash_to_assets") }, { key: "e", get: r("equity_to_assets") }], periods)} series={[{ key: "k", name: "Kredi/Aktif" }, { key: "m", name: "Mevduat/Aktif" }, { key: "f", name: "Alınan krediler/Aktif" }, { key: "c", name: "Nakit/Aktif" }, { key: "e", name: "Özkaynak/Aktif" }]} />
        <Chart title="Yıllık büyüme (stok, TL)" pct data={series([{ key: "a", get: r("assets_growth_yoy") }, { key: "k", get: r("loans_growth_yoy") }, { key: "m", get: r("deposits_growth_yoy") }, { key: "e", get: r("equity_growth_yoy") }], periods)} series={[{ key: "a", name: "Aktif" }, { key: "k", name: "Kredi" }, { key: "m", name: "Mevduat" }, { key: "e", name: "Özkaynak" }]} note="Nominal TL büyümesi; USD/EUR bazlı büyüme için tabloyu kullanın." />
      </div>
      <section>
        <h2>Bilanço kalemleri (Blanco sözlüğü) · {u} · dönem sonu stok</h2>
        <Table unit={u} periods={periods} rows={bsItems.map(i => ({ label: i.name, level: i.status === "DERIVED" ? 2 : 1, status: i.status, tip: `${i.code} · ${i.source}${i.note ? " · " + i.note : ""}`, values: periods.map(p => conv(i.values[p], p, ccy)) }))} />
        <div className="note">DERIVED satırlar bileşenlerden hesaplanır (ör. net krediler = brüt + BZK). Tam bilanço (TP/YP ayrımıyla) için Tablolar sekmesi.</div>
      </section>
    </>
  );
}
