"use client";
import { useState } from "react";
import { Chart } from "@/components/Chart";
import { Table } from "@/components/Table";
import { useCcy } from "@/components/Ccy";
import { D, PERIODS, ccyUnit, conv, convYtd, flow, ratio, series } from "@/lib/data";

export default function Gelir() {
  const { ccy } = useCcy(); const u = ccyUnit(ccy);
  const [mode, setMode] = useState<"q" | "ytd" | "ttm">("q");
  const q = (code: string) => (p: string) => conv(flow(code).q[p], p, ccy, "q");
  const S = (codes: [string, string][]) => series(codes.map(([c]) => ({ key: c, get: q(c) })));
  const N = (codes: [string, string][]) => codes.map(([c, n]) => ({ key: c, name: n }));
  const ii: [string, string][] = [["interest_on_loans", "Krediler"], ["interest_from_banks", "Bankalar"], ["interest_from_money_market", "Para piyasası"], ["interest_on_securities", "Menkul"], ["other_interest_income", "Diğer"]];
  const ie: [string, string][] = [["interest_on_deposits", "Mevduat"], ["interest_on_funds_borrowed", "Alınan krediler"], ["interest_on_money_market", "Para piyasası"], ["other_interest_expense", "Diğer"]];
  const rev: [string, string][] = [["net_interest_income", "NII"], ["net_fee_commission_income", "Net ücret"], ["trading_income", "Ticari K/Z"], ["other_operating_income", "Diğer"]];
  const tr: [string, string][] = [["trading_securities", "Sermaye piyasası"], ["trading_derivatives", "Türev"], ["trading_fx", "Kambiyo"]];
  const ox: [string, string][] = [["personnel_expenses", "Personel"], ["other_operating_expenses", "Diğer faaliyet"], ["provision_expenses", "Karşılıklar"]];
  const pl = D.items.filter(i => i.section === "income_statement");
  const periods = PERIODS;
  const val = (code: string, p: string) => mode === "q" ? conv(flow(code)?.q[p], p, ccy, "q") : mode === "ttm" ? ttm(code, p) : convYtd(code, p, ccy);
  function ttm(code: string, p: string) { const i = PERIODS.indexOf(p); if (i < 3) return null; let s = 0; for (let k = 0; k < 4; k++) { const v = conv(flow(code)?.q[PERIODS[i - k]], PERIODS[i - k], ccy, "q"); if (v === null) return null; s += v; } return s; }
  return (
    <>
      <h1>Gelir tablosu</h1>
      <div className="grid2">
        <Chart title="Çeyreklik faiz gelir / gider ve NII" unit={u} kind="bar" data={S([["interest_income", ""], ["interest_expense", ""], ["net_interest_income", ""]])} series={N([["interest_income", "Faiz gelirleri"], ["interest_expense", "Faiz giderleri"], ["net_interest_income", "Net faiz geliri"]])} />
        <Chart title="Faiz geliri kompozisyonu (çeyrek)" unit={u} kind="bar" stacked data={S(ii)} series={N(ii)} />
        <Chart title="Faiz gideri kompozisyonu (çeyrek, negatif)" unit={u} kind="bar" stacked data={S(ie)} series={N(ie)} />
        <Chart title="Gelir karması (çeyrek)" unit={u} kind="bar" stacked data={S(rev)} series={N(rev)} />
        <Chart title="Ticari K/Z kırılımı (çeyrek)" unit={u} kind="bar" stacked data={S(tr)} series={N(tr)} />
        <Chart title="Faaliyet giderleri ve karşılıklar (çeyrek, negatif)" unit={u} kind="bar" stacked data={S(ox)} series={N(ox)} />
        <Chart title="Vergi öncesi kâr, vergi, net kâr (çeyrek)" unit={u} kind="bar" data={S([["profit_before_tax", ""], ["tax_provision", ""], ["net_profit", ""]])} series={N([["profit_before_tax", "Vergi öncesi kâr"], ["tax_provision", "Vergi"], ["net_profit", "Net kâr"]])} />
        <Chart title="Net kâr ve NII büyümesi (çeyrek, yıllık, TL)" pct kind="bar" data={series([{ key: "p", get: (p) => ratio("profit_growth_q_yoy").values[p] ?? null }, { key: "n", get: (p) => ratio("nii_growth_q_yoy").values[p] ?? null }])} series={[{ key: "p", name: "Net kâr çeyrek YoY" }, { key: "n", name: "NII çeyrek YoY" }]} />
      </div>
      <section>
        <h2>Gelir tablosu kalemleri · {u} ·
          <span className="ccy" style={{ marginLeft: 8 }}>{(["q", "ytd", "ttm"] as const).map(m => <button key={m} className={m === mode ? "on" : ""} onClick={() => setMode(m)}>{m === "q" ? "Çeyrek" : m === "ytd" ? "YTD" : "TTM"}</button>)}</span>
        </h2>
        <Table unit={u} periods={periods} rows={pl.map(i => ({ label: i.name, level: i.status === "DERIVED" ? 2 : 1, status: i.status, tip: `${i.code} · ${i.source}`, values: periods.map(p => val(i.code, p)) }))} />
        <div className="note">Çeyrek = YTD − önceki YTD (Ç1 = YTD; 2020Ç3 bildirilen 3 aylık). USD/EUR: çeyrek ortalama kur, YTD/TTM = çeyreklerin toplamı. Giderler KAP işaretiyle (negatif).</div>
      </section>
    </>
  );
}
