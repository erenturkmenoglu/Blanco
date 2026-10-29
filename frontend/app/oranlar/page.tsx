"use client";
import { Chart } from "@/components/Chart";
import { Table } from "@/components/Table";
import { D, PERIODS, ratio, series, stockPeriods } from "@/lib/data";

export default function Oranlar() {
  const r = (code: string) => (p: string) => ratio(code).values[p] ?? null;
  const S = (codes: [string, string][], ps = stockPeriods) => series(codes.map(([c]) => ({ key: c, get: r(c) })), ps);
  const N = (codes: [string, string][]) => codes.map(([c, n]) => ({ key: c, name: n }));
  return (
    <>
      <h1>Oranlar</h1>
      <div className="note" style={{ marginBottom: 10 }}>Blanco yöntemi: akım = YTD×4/q, ortalama bakiye = (dönem sonu + önceki yıl sonu)/2. TTM yöntemi: son 4 çeyrek akım / son 5 çeyrek sonu ortalaması. Oranlar para biriminden bağımsızdır (TL).</div>
      <div className="grid2">
        <Chart title="ROE" pct data={S([["roe", ""], ["roe_ttm", ""]])} series={N([["roe", "Blanco (YTD×4/q, 2 nokta ort.)"], ["roe_ttm", "TTM / 5Ç ort."]])} />
        <Chart title="ROA" pct digits={1} data={S([["roa", ""], ["roa_ttm", ""]])} series={N([["roa", "Blanco"], ["roa_ttm", "TTM / 5Ç ort."]])} />
        <Chart title="Net faiz marjı" pct digits={1} data={S([["nim_iea_ttm", ""], ["nim", ""], ["nim_q_ann", ""]])} series={N([["nim_iea_ttm", "Faiz getirili aktif, TTM"], ["nim", "Toplam aktif, Blanco"], ["nim_q_ann", "Çeyrek×4 / dönem sonu aktif"]])} />
        <Chart title="Gider / Gelir" pct data={S([["cost_to_income", ""], ["cost_to_income_q", ""]], PERIODS)} series={N([["cost_to_income", "YTD"], ["cost_to_income_q", "Çeyrek"]])} />
        <Chart title="Efektif getiri / maliyet (TTM / 5Ç ort. bakiye)" pct data={S([["int_yield_loans_ttm", ""], ["int_cost_deposits_ttm", ""], ["int_cost_funds_borrowed_ttm", ""]])} series={N([["int_yield_loans_ttm", "Kredi faiz getirisi"], ["int_cost_deposits_ttm", "Mevduat faiz maliyeti"], ["int_cost_funds_borrowed_ttm", "Alınan kredi faiz maliyeti"]])} note="Muhasebesel (faiz geliri/ortalama bakiye); dipnottaki stok ortalama uygulanan oranlarla karşılaştırılabilir ama aynı tanım değildir." />
        <Chart title="Gelir karması payları (YTD)" pct data={S([["nii_share", ""], ["fee_share", ""], ["trading_share", ""]], PERIODS)} series={N([["nii_share", "NII"], ["fee_share", "Net ücret"], ["trading_share", "Ticari K/Z"]])} />
        <Chart title="Kredi/Mevduat" pct data={S([["loan_to_deposit_ratio", ""]])} series={N([["loan_to_deposit_ratio", "Kredi/Mevduat"]])} />
        <Chart title="Kredi risk maliyeti ve efektif vergi" pct digits={2} data={S([["cost_of_risk", ""], ["effective_tax_rate", ""]], PERIODS)} series={N([["cost_of_risk", "CoR (Blanco)"], ["effective_tax_rate", "Efektif vergi oranı (YTD)"]])} />
        <Chart title="Çeyreklik büyüme (stok)" pct data={S([["assets_growth_qoq", ""], ["loans_growth_qoq", ""], ["deposits_growth_qoq", ""]])} series={N([["assets_growth_qoq", "Aktif"], ["loans_growth_qoq", "Kredi"], ["deposits_growth_qoq", "Mevduat"]])} />
        <Chart title="Net kâr büyümesi (YTD/YTD ve çeyrek)" pct data={S([["profit_growth_yoy", ""], ["profit_growth_q_yoy", ""]], PERIODS)} series={N([["profit_growth_yoy", "YTD aynı pencere"], ["profit_growth_q_yoy", "Çeyrek YoY"]])} />
      </div>
      <section>
        <h2>Tüm oranlar</h2>
        <Table periods={PERIODS} rows={D.ratios.map(x => ({ label: `${x.name} [${x.method}]`, tip: `${x.code}: ${x.formula}`, pct: x.unit === "pct", digits: x.unit === "pct" ? 1 : x.unit === "x" ? 2 : 0, values: PERIODS.map(p => x.values[p] ?? null) }))} />
      </section>
    </>
  );
}
